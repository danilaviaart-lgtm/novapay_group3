from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.security import OAuth2PasswordBearer 
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
import uuid
from datetime import datetime

from database import engine 
from m_usuarios import Usuario, UsuarioResponse, UsuarioUpdate
from security import verificar_access_token 

router = APIRouter()

# CONFIGURACIÓN DE SEGURIDAD RELATIVA PARA SWAGGER
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

async def obtener_analista_actual(token: str = Depends(oauth2_scheme)) -> dict:
    return verificar_access_token(token)

#ENDPOINT

@router.get("/lista", response_model=List[UsuarioResponse], status_code=status.HTTP_200_OK)
async def listar_clientes(
    q: Optional[str] = Query(None, description="Buscar por nombre, email o DNI"),
    bloqueado: Optional[bool] = Query(None, description="Filtrar por estado de bloqueo"),
    limite: int = Query(100, ge=1, le=500, description="Límite de registros"),
):
    async with AsyncSession(engine) as session:
        statement = select(Usuario)

        if q:
            statement = statement.where(
                (Usuario.nombre.ilike(f"%{q}%")) |
                (Usuario.apellido.ilike(f"%{q}%")) |
                (Usuario.email.ilike(f"%{q}%")) |
                (Usuario.dni.ilike(f"%{q}%"))
            )
        if bloqueado is not None:
            statement = statement.where(Usuario.bloqueado == bloqueado)

        statement = statement.limit(limite)
        resultado = await session.exec(statement)
        return resultado.all()


@router.get("/{Clienteid}", response_model=UsuarioResponse, status_code=status.HTTP_200_OK)
async def obtener_usuario_por_id(
    Clienteid: uuid.UUID,
    #analista_actual: dict = Depends(obtener_analista_actual) # <--- CANDADO ACTIVADO
):
    async with AsyncSession(engine) as session:
        statement = select(Usuario).where(Usuario.Clienteid == Clienteid)
        
        resultado = await session.exec(statement)
        usuario_encontrado = resultado.first()
        
        if not usuario_encontrado:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario con ID {Clienteid} no encontrado"
            )
            
        # DEVUELVE USUARIO
        return usuario_encontrado


@router.patch("/update/{Clienteid}", response_model=UsuarioResponse, status_code=status.HTTP_200_OK)
async def editar_usuario(
    Clienteid: uuid.UUID, 
    datos_actualizados: UsuarioUpdate,
    #analista_actual: dict = Depends(obtener_analista_actual) # <--- CANDADO ACTIVADO
):
    """
    Modifica los campos permitidos de un cliente existente buscando por su UUID.
    Requiere que un usuario de la plataforma esté autenticado.
    """
    async with AsyncSession(engine) as session:
        # BUSCA USUARIOS
        statement = select(Usuario).where(Usuario.Clienteid == Clienteid)
        resultado = await session.exec(statement)
        usuario_db = resultado.first()
        
        if not usuario_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario con ID {Clienteid} no encontrado"
            )
        
        data_dict = datos_actualizados.model_dump(exclude_unset=True)
        
        for key, value in data_dict.items():
            setattr(usuario_db, key, value) # Actualiza el atributo dinámicamente en el objeto
            
        # DATOS DE TIEMPO
        usuario_db.ultima_actualizacion = datetime.now()
        
        # ENVIO A BD
        session.add(usuario_db)
        await session.commit()
        await session.refresh(usuario_db)
        
        # DEVUELVO USUADIO PARA UPDATE
        return usuario_db