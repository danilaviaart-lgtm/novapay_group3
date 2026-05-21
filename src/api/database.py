import os
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

# 1. CADENAS DE CONEXIÓN REALES
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:pX9$mK2!vL7_qZ4w@192.168.0.20:7432/proyecto_novapay")
VALKEY_URL = os.getenv("VALKEY_URL", "redis://192.168.0.20:6379")

# 2. LOS ENGINES / CLIENTES (Objetos físicos de conexión)
engine = create_async_engine(DATABASE_URL, echo=True)

# Dejamos el cliente de Valkey listo como None; se instanciará en el lifespan de la app
valkey_client: aioredis.Redis | None = None


# 3. EL CREADOR DE SESIONES POSTGRES
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)


# 4. LAS DEPENDENCIAS PARA TUS ENDPOINTS (Lo que hereda predict.py)
async def get_db():
    """Entrega una conexión activa a Postgres y se asegura de cerrarla al terminar."""
    async with AsyncSessionLocal() as session:
        try:
            yield session  
        finally:
            await session.close()  

def get_valkey() -> aioredis.Redis:
    """Entrega la instancia activa y conectada de Valkey."""
    if valkey_client is None:
        raise RuntimeError("Valkey no ha sido inicializado en el lifespan de la aplicación.")
    return valkey_client


# 5. FUNCIONES DE CONTROL DE CICLO DE VIDA (Para tu archivo main.py)
async def init_databases():
    """Inicializa los pools de conexiones y verifica la conectividad al arrancar la app."""
    global valkey_client
    # Inicializamos el cliente de Valkey con decodificación automática a strings de Python
    valkey_client = aioredis.from_url(VALKEY_URL, decode_responses=True)
    # Hacemos un ping rápido para asegurar que Valkey está arriba
    await valkey_client.ping()

async def close_databases():
    """Cierra todos los pools de conexiones limpiamente al apagar el servidor."""
    global valkey_client
    if valkey_client:
        await valkey_client.close()
    # Libera los recursos del engine de Postgres
    await engine.dispose()