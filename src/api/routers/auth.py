from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
import uuid

from database import engine
from m_analista import UsuarioPlataformaBase, UsuarioPlataforma, RolUsuario
from security import verificar_password, crear_access_token, obtener_password_hash

router = APIRouter(tags=["Autenticación"])

# LOGIN
@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Endpoint de Login. 
    - username: Puede recibir el 'username' o el 'email' del analista.
    - password: La contraseña en texto plano que se comprobará contra el hash.
    """
    async with AsyncSession(engine) as session:
        # BUSQUEDA USUARIO O EMAIL
        statement = select(UsuarioPlataforma).where(
            (UsuarioPlataforma.username == form_data.username) | 
            (UsuarioPlataforma.email == form_data.username)
        )
        resultado = await session.exec(statement)
        usuario = resultado.first()
        
        # VALIDAMOS PASSWORD + HASH
        if not usuario or not verificar_password(form_data.password, usuario.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=(self_destruct_detail := "Credenciales de plataforma incorrectas"),
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        if not usuario.activo:
            raise HTTPException(status_code=403, detail="Este usuario está deshabilitado")
            
        # GENERAMOS TOKEN PARA AUTENTIFICACIÓN
        token_acceso = crear_access_token(
            data={
                "sub": str(usuario.id), 
                "username": usuario.username,
                "rol": usuario.rol
            }
        )
        
        return {
            "access_token": token_acceso,
            "token_type": "bearer"
        }

# TEMPORAL PARA CREAR ANALISTAS . ¡¡¡BORRAR ANTES DEL DEPLOY!!
@router.post("/auth/crear-analista-inicial")
async def crear_analista_inicial(
    username: str, 
    email: str, 
    nombre: str, 
    password_plano: str,
    rol: RolUsuario = RolUsuario.Admin  # <--- Esto genera el menú desplegable en Swagger
):
    """
    Usa este endpoint UNA SOLA VEZ en tu /docs para registrarte 
    e inyectar tu primer usuario con la contraseña bien hasheada en la BD.
    """
    async with AsyncSession(engine) as session:
        # Hasheamos la contraseña antes de guardarla
        hash_generado = obtener_password_hash(password_plano)
        
        nuevo_usuario = UsuarioPlataforma(
            username=username,
            email=email,
            nombre=nombre,
            password_hash=hash_generado,
            rol=rol  # Usa el rol seleccionado del desplegable
        )
        
        session.add(nuevo_usuario)
        await session.commit()
        return {"message": f"Usuario {username} creado con éxito con el rol {rol.value}. Ya puedes loguearte."}