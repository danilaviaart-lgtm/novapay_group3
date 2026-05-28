import os
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

ruta_env = Path(__file__).resolve().parent / ".env"

if ruta_env.exists():
    with open(ruta_env, "r") as f:
        for linea in f:
            linea = linea.strip()
            # Ignoramos líneas vacías o comentarios
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, valor = linea.split("=", 1)
            os.environ[clave.strip()] = valor.strip()
# =====================================================================

try:
    DATABASE_URL = os.environ["DATABASE_URL"]
except KeyError:
    raise RuntimeError(
        f"\n\n❌ ERROR CRÍTICO:\n"
        f"No se ha encontrado la variable 'DATABASE_URL' dentro de:\n"
        f"{ruta_env}\n"
        f"Asegúrate de que el archivo .env existe en esa carpeta y tiene la variable bien escrita.\n"
    )


engine = create_async_engine(DATABASE_URL, echo=False)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()