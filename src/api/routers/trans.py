from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.security import OAuth2PasswordBearer 
from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List, Optional
from sqlalchemy import or_
import uuid

from database import engine
from m_transacciones import Transaccion, TransaccionResponse, TransaccionUpdate
from security import verificar_access_token 
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

async def obtener_analista_actual(token: str = Depends(oauth2_scheme)) -> dict:
    return verificar_access_token(token)


@router.get("/stats/dashboard", status_code=status.HTTP_200_OK)
async def obtener_stats_dashboard():
    async with AsyncSession(engine) as session:
        total = (await session.execute(select(func.count(Transaccion.id_transaccion)))).scalar() or 0
        fraud = (await session.execute(select(func.count(Transaccion.id_transaccion)).where(Transaccion.es_fraude == True))).scalar() or 0
        pending = (await session.execute(
            select(func.count(Transaccion.id_transaccion)).where(
                Transaccion.es_fraude == False,
                Transaccion.f_score.isnot(None),
                Transaccion.f_score > 0.3,
            )
        )).scalar() or 0
        clean = total - fraud - pending
        return {"total": total, "fraud": fraud, "pending": pending, "clean": clean}


@router.get("/", response_model=List[TransaccionResponse], status_code=status.HTTP_200_OK)
async def obtener_todas_las_transacciones(
    es_fraude: Optional[bool] = Query(None, description="Filtrar por si es fraude (true/false)"),
    revisado: Optional[str] = Query(None, description="Filtrar por estado de revisión"),
    analista: Optional[str] = Query(None, description="Filtrar por el nombre del analista"),
    limite: Optional[int] = Query(None, ge=1, le=50000, description="Número de registros (opcional)"),
    offset: int = Query(0, ge=0, description="Desplazamiento"),
    #analista_actual: dict = Depends(obtener_analista_actual)
):
    """
    Devuelve el listado global de transacciones con filtros opcionales y paginación.
    """
    async with AsyncSession(engine) as session:
        statement = select(Transaccion).order_by(Transaccion.fecha.desc())
        
        if es_fraude is not None:
            statement = statement.where(Transaccion.es_fraude == es_fraude)
            
        if revisado is not None:
            if revisado.lower() == "pendiente":
                statement = statement.where(
                    or_(
                        Transaccion.revisado.like(f"%{revisado}%"),
                        Transaccion.revisado.is_(None),
                    )
                )
            else:
                statement = statement.where(Transaccion.revisado.like(f"%{revisado}%"))

        if analista is not None:
            statement = statement.where(Transaccion.analista == analista)
        statement = statement.offset(offset)
        if limite is not None:
            statement = statement.limit(limite)
        resultado = await session.execute(statement)
        return resultado.scalars().all()


@router.get("/{id_transaccion}", response_model=TransaccionResponse, status_code=status.HTTP_200_OK)
async def obtener_transaccion_por_id(
    id_transaccion: uuid.UUID,
    #analista_actual: dict = Depends(obtener_analista_actual)
):
    async with AsyncSession(engine) as session:
        statement = select(Transaccion).where(Transaccion.id_transaccion == id_transaccion)
        
        # 1. Usamos session.execute en lugar de session.exec
        resultado = await session.execute(statement)
        
        # 2. Extraemos el objeto único o None
        transaccion_encontrada = resultado.scalar_one_or_none()
        
        if not transaccion_encontrada:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transacción con ID {id_transaccion} no encontrada"
            )
        return transaccion_encontrada

@router.get("/cliente/{id_usuario}", response_model=List[TransaccionResponse], status_code=status.HTTP_200_OK)
async def obtener_transacciones_de_usuario(
    id_usuario: uuid.UUID,
    #analista_actual: dict = Depends(obtener_analista_actual)
):
    async with AsyncSession(engine) as session:
        # Tu statement actual (probablemente un select(Transaccion).where(...))
        statement = select(Transaccion).where(Transaccion.id_usuario == id_usuario) 
        
        # 1. Cambia session.exec por session.execute
        resultado = await session.execute(statement)
        
        # 2. Extrae todas las filas como una lista de objetos de SQLModel/SQLAlchemy
        transacciones = resultado.scalars().all()
        
        return transacciones
    

@router.patch("/update/{id_transaccion}", response_model=TransaccionResponse, status_code=status.HTTP_200_OK)
async def editar_transaccion(
    id_transaccion: uuid.UUID, 
    datos_actualizados: TransaccionUpdate,
    analista_actual: dict = Depends(obtener_analista_actual) # 💡 Descomentado y con la coma arriba
):
    async with AsyncSession(engine) as session:
        # BUSCA LA TRANSACCIÓN
        statement = select(Transaccion).where(Transaccion.id_transaccion == id_transaccion)
        resultado = await session.execute(statement)  
        transaccion_db = resultado.scalars().first()   
        
        if not transaccion_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transacción con ID {id_transaccion} no encontrada"
            )
        
        # SOLO ACTUALIZAMOS BODY
        data_dict = datos_actualizados.model_dump(exclude_unset=True)
        for key, value in data_dict.items():
            setattr(transaccion_db, key, value)
            
        # FORZAMOS UPDATE DE ANALISTA CON EL ID DEL ANALISTA QUE HIZO LA MODIFICACIÓN (EXTRAIDO DEL JWT)
        id_analista_jwt = analista_actual.get("sub") #  Ahora sí existirá la variable
        if id_analista_jwt:
            try:
                transaccion_db.analista = uuid.UUID(id_analista_jwt)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El ID de analista en el token JWT no es un UUID válido."
                )
        
        # GUARDAMOS EN BD POST
        session.add(transaccion_db)
        await session.commit()
        await session.refresh(transaccion_db)
        
        return transaccion_db