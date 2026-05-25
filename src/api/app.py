import joblib
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# BASE DE DATOS
from database import init_databases, close_databases, engine
from sqlmodel import SQLModel

# IMPORTAR LA LÓGICA DE SHAP NUEVA
from utils.shap_explainer import get_explainer

# RUTAS ENDPOINTS
from routers import predictvit, clientes, trans, auth

# UTILIDADES
import utils.utils as clean_utils

# CLEAN UTILS PARA DEPLOYMENT PKL
sys.modules["utils.utils"] = clean_utils

# CONFIGURACIÓN DE RUTAS Y MODELO
BASE_DIR = Path(__file__).resolve().parent.parent.parent
RUTA_MODELO = BASE_DIR / "models" / "modelo_fraude_v1.pkl" 

# LIFESPAN: INICIALIZACIÓN Y SHUTDOWN DE LA APP
@asynccontextmanager
async def lifespan(app: FastAPI):

    # 1. POSTGRESQL + VALKEY
    print("Inicializando pools de conexiones a las bases de datos...")
    await init_databases()

    # 2. LOGICA POSTGRES Y CREACIÓN DE TABLAS SI NO EXISTEN
    print("Verificando y creando tablas en PostgreSQL...")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    # 3. CARGA DEL MODELO DE PREDICCIÓN EN MEMORIA
    if not RUTA_MODELO.exists():
        raise FileNotFoundError(f"No se encontró el modelo en: {RUTA_MODELO}")
        
    print("Cargando modelo de predicción en app.state...")
    pipeline_cargado = joblib.load(RUTA_MODELO)
    app.state.model = pipeline_cargado
    
    # 4. CARGA DEL EXPLICADOR SHAP BASADO EN TU PIPELINE
    print("Inicializando SHAP Explainer global a través de utils...")
    app.state.shap_explainer = get_explainer(pipeline_cargado)
    
    yield  # API OPERATIVA

    # SHUTDOWN: LIMPIEZA DE RECURSOS
    print("Limpiando recursos y cerrando conexiones...")
    app.state.model = None
    app.state.shap_explainer = None
    await close_databases()  
    print("Servidor apagado correctamente.")


# INICIALIZACIÓN DE LA APP CON CONFIGURACIÓN DE LIFESPAN
app = FastAPI(
    title="NovaPay Fraud Detection API",
    version="1.0.0",
    lifespan=lifespan
)

<<<<<<< HEAD
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # <--- El asterisco abre las puertas a cualquier origen
    allow_credentials=True,    # Nota: A veces con "*" algunos navegadores se quejan si esto está en True. Si te da error, cámbialo a False.
    allow_methods=["*"],       # Permite GET, POST, OPTIONS, etc.
    allow_headers=["*"],       # Permite cualquier header
)

=======
>>>>>>> c70af591b624600266f2a9549b6bccb72c2f5d5a
# RUTA PRINCIPAL PARA VERIFICAR QUE LA API ESTÁ FUNCIONANDO
@app.get("/")
def read_root():
    return {"message": "API de NovaPay funcionando"}

# ROUTAS ENDPOINTS
app.include_router(auth.router)
app.include_router(predictvit.router, prefix="/predict", tags=["Predicciones"])
app.include_router(clientes.router, prefix="/clientes", tags=["Clientes"])
app.include_router(trans.router, prefix="/trans", tags=["Transacciones"])