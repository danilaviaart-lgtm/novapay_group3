from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.security import OAuth2PasswordBearer 
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List, Optional
<<<<<<< HEAD
from sqlalchemy import or_
=======
>>>>>>> c70af591b624600266f2a9549b6bccb72c2f5d5a
import uuid

from database import engine 
from m_transacciones import Transaccion, TransaccionResponse, TransaccionUpdate
from security import verificar_access_token 
<<<<<<< HEAD
from sqlalchemy.ext.asyncio import AsyncSession
=======
>>>>>>> c70af591b624600266f2a9549b6bccb72c2f5d5a

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

async def obtener_analista_actual(token: str = Depends(oauth2_scheme)) -> dict:
    return verificar_access_token(token)


@router.get("/", response_model=List[TransaccionResponse], status_code=status.HTTP_200_OK)
async def obtener_todas_las_transacciones(
    es_fraude: Optional[bool] = Query(None, description="Filtrar por si es fraude (true/false)"),
<<<<<<< HEAD
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
=======
    tipo_transaccion: Optional[str] = Query(None, description="Filtrar por tipo (ej: TRANSFER, PAYMENT)"),
    revisado: Optional[str] = Query(None, description="Filtrar por estado de revisión"),
    analista: Optional[str] = Query(None, description="Filtrar por el nombre del analista"),
    limite: int = Query(100, ge=1, le=500, description="Límite de registros"),
    analista_actual: dict = Depends(obtener_analista_actual)
):
    """
    Devuelve el listado global de transacciones con filtros opcionales.
    """
    async with AsyncSession(engine) as session:
        statement = select(Transaccion)
>>>>>>> c70af591b624600266f2a9549b6bccb72c2f5d5a
        
        if es_fraude is not None:
            statement = statement.where(Transaccion.es_fraude == es_fraude)
            
<<<<<<< HEAD
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
=======
        if tipo_transaccion is not None:
            statement = statement.where(Transaccion.tipo_transaccion == tipo_transaccion)

        if revisado is not None:
            statement = statement.where(Transaccion.revisado.like(f"%{revisado}%"))

        if analista is not None:
            statement = statement.where(Transaccion.analista == analista)
            
        statement = statement.limit(limite)
        resultado = await session.exec(statement)
        return resultado.all()
>>>>>>> c70af591b624600266f2a9549b6bccb72c2f5d5a


@router.get("/{id_transaccion}", response_model=TransaccionResponse, status_code=status.HTTP_200_OK)
async def obtener_transaccion_por_id(
    id_transaccion: uuid.UUID,
<<<<<<< HEAD
    #analista_actual: dict = Depends(obtener_analista_actual)
):
    async with AsyncSession(engine) as session:
        statement = select(Transaccion).where(Transaccion.id_transaccion == id_transaccion)
        
        # 1. Usamos session.execute en lugar de session.exec
        resultado = await session.execute(statement)
        
        # 2. Extraemos el objeto único o None
        transaccion_encontrada = resultado.scalar_one_or_none()
=======
    analista_actual: dict = Depends(obtener_analista_actual)
):
    async with AsyncSession(engine) as session:
        statement = select(Transaccion).where(Transaccion.id_transaccion == id_transaccion)
        resultado = await session.exec(statement)
        transaccion_encontrada = resultado.first()
>>>>>>> c70af591b624600266f2a9549b6bccb72c2f5d5a
        
        if not transaccion_encontrada:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transacción con ID {id_transaccion} no encontrada"
            )
        return transaccion_encontrada

<<<<<<< HEAD
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
=======

@router.get("/usuarios/{id_usuario}/trans", response_model=List[TransaccionResponse], status_code=status.HTTP_200_OK)
async def obtener_transacciones_de_usuario(
    id_usuario: uuid.UUID,
    analista_actual: dict = Depends(obtener_analista_actual)
):
    async with AsyncSession(engine) as session:
        statement = select(Transaccion).where(Transaccion.id_usuario == id_usuario)
        resultado = await session.exec(statement)
        return resultado.all()
>>>>>>> c70af591b624600266f2a9549b6bccb72c2f5d5a
    

@router.patch("/update/{id_transaccion}", response_model=TransaccionResponse, status_code=status.HTTP_200_OK)
async def editar_transaccion(
    id_transaccion: uuid.UUID, 
    datos_actualizados: TransaccionUpdate,
<<<<<<< HEAD
    analista_actual: dict = Depends(obtener_analista_actual) # 💡 Descomentado y con la coma arriba
):
    async with AsyncSession(engine) as session:
        # BUSCA LA TRANSACCIÓN
        statement = select(Transaccion).where(Transaccion.id_transaccion == id_transaccion)
        resultado = await session.execute(statement)  
        transaccion_db = resultado.scalars().first()   
=======
    analista_actual: dict = Depends(obtener_analista_actual)
):
    if analista_actual.get("rol") != "administrador":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu rol de analista no tiene permisos para modificar transacciones financieras."
        )

    async with AsyncSession(engine) as session:
        statement = select(Transaccion).where(Transaccion.id_transaccion == id_transaccion)
        resultado = await session.exec(statement)
        transaccion_db = resultado.first()
>>>>>>> c70af591b624600266f2a9549b6bccb72c2f5d5a
        
        if not transaccion_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transacción con ID {id_transaccion} no encontrada"
            )
        
<<<<<<< HEAD
        # SOLO ACTUALIZAMOS BODY
=======
>>>>>>> c70af591b624600266f2a9549b6bccb72c2f5d5a
        data_dict = datos_actualizados.model_dump(exclude_unset=True)
        for key, value in data_dict.items():
            setattr(transaccion_db, key, value)
            
<<<<<<< HEAD
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
        
=======
        # EXTRAE EL ID AUTOMÁTICAMENTE: Convertimos el 'sub' del JWT en un UUID válido
        id_analista_jwt = analista_actual.get("sub")
        transaccion_db.analista = uuid.UUID(id_analista_jwt)
        
        session.add(transaccion_db)
        await session.commit()
        await session.refresh(transaccion_db)
>>>>>>> c70af591b624600266f2a9549b6bccb72c2f5d5a
        return transaccion_db