import os
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

<<<<<<< HEAD

=======
>>>>>>> c70af591b624600266f2a9549b6bccb72c2f5d5a
# CONEXIONES Y CONFIGURACIONES DE BASE DE DATOS
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:pX9$mK2!vL7_qZ4w@192.168.0.20:7432/postgres")
VALKEY_URL = os.getenv("VALKEY_URL", "redis://192.168.0.20:6379")

# ENGINE POSTGRESQL ASÍNCRONO
engine = create_async_engine(DATABASE_URL, echo=True)

# CLIENTE VALKEY
valkey_client: aioredis.Redis | None = None


# SESIÓN BD POSTGRES
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# CONEXIÓN Y CIERRE POSTGRES
async def get_db():
    """Entrega una conexión activa a Postgres y se asegura de cerrarla al terminar."""
    async with AsyncSessionLocal() as session:
        try:
            yield session  
        finally:
            await session.close()  

#CONEXIÓN VALKEY
def get_valkey() -> aioredis.Redis:
    """Entrega la instancia activa y conectada de Valkey."""
    if valkey_client is None:
        raise RuntimeError("Valkey no ha sido inicializado en el lifespan de la aplicación.")
    return valkey_client


#CONTROL VALKEY INICIO
async def init_databases():
    """Inicializa los pools de conexiones y verifica la conectividad al arrancar la app."""
    global valkey_client
    # Inicializamos el cliente de Valkey con decodificación automática a strings de Python
    valkey_client = aioredis.from_url(VALKEY_URL, decode_responses=True)
    # Hacemos un ping rápido para asegurar que Valkey está arriba
    await valkey_client.ping()
    
#CONTROL VALKEY CIERRE
async def close_databases():
    """Cierra todos los pools de conexiones limpiamente al apagar el servidor."""
    global valkey_client
    if valkey_client:
        await valkey_client.close()
    # Libera los recursos del engine de Postgres
    await engine.dispose()