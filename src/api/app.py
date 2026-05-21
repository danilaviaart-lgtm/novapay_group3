import joblib
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI

# Base de datos e Infraestructura
from database import init_databases, close_databases, engine
from sqlmodel import SQLModel

# Importación de rutas
from routers import predict 

# Configuración de rutas de archivos
BASE_DIR = Path(__file__).resolve().parent.parent.parent
RUTA_MODELO = BASE_DIR / "models" / "modelo_alto_recall_dani2.pkl" 

# --- LIFESPAN (Ciclo de vida de la aplicación) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Inicializamos las conexiones (PostgreSQL y Valkey)
    print("Inicializando pools de conexiones a las bases de datos...")
    await init_databases()

    # 2. Creamos las tablas en PostgreSQL si no existen (Lógica de SQLModel)
    print("Verificando y creando tablas en PostgreSQL...")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    # 3. Validamos y cargamos el modelo de Machine Learning en RAM
    if not RUTA_MODELO.exists():
        raise FileNotFoundError(f"No se encontró el modelo en: {RUTA_MODELO}")
        
    print("Cargando modelo de predicción en app.state...")
    app.state.model = joblib.load(RUTA_MODELO)
    
    yield  # --- LA API QUEDA OPERATIVA Y CORRIENDO ---

    # --- SHUTDOWN (Limpieza de recursos al apagar el servidor) ---
    print("Limpiando recursos y cerrando conexiones...")
    app.state.model = None
    await close_databases()  # Cierra pools de Valkey y del engine de Postgres de forma limpia
    print("Servidor apagado correctamente.")


# --- INICIALIZACIÓN DE FASTAPI ---
app = FastAPI(
    title="NovaPay Fraud Detection API",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/")
def read_root():
    return {"message": "API de NovaPay funcionando"}

# --- REGISTRO DE ROUTERS ---
# Incluimos las rutas de predicción bajo el prefijo /predict
app.include_router(predict.router, prefix="/predict", tags=["Predicciones"])