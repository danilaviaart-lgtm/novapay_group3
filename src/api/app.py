from fastapi import FastAPI
from contextlib import asynccontextmanager
import joblib
from app.routers import predict # Importas tus rutas, añadir más a posterior
from pathlib import Path

# Configuración de rutas
BASE_DIR = Path(__file__).resolve().parent.parent.parent
RUTA_MODELO = BASE_DIR / "models" / "modelo_alto_recall_dani.pkl" # direccion del pickle del modelo entrenado
#RUTA_PARQUET = BASE_DIR / "data" / "processed" / "data_idname.parquet"

#lifespan para cargar modelo y cerrar recursos ( vive en RAM mientras la app esté corriendo, se carga al iniciar y se limpia al cerrar)
@asynccontextmanager
async def lifespan(app: FastAPI):
    #Startup buscamos y cargamos modelo
    if not RUTA_MODELO.exists():
        raise FileNotFoundError(f"No se encontró el modelo en: {RUTA_MODELO}")
        
    print("Cargando modelo en app.state...")
    # Guardamos el modelo en el estado de la aplicación
    app.state.model = joblib.load(RUTA_MODELO)
    
    yield # UP

    # Apagamos y limpiamos recursos
    print("Limpiando recursos...")
    # Eliminamos la referencia del estado
    app.state.model = None

app = FastAPI(lifespan=lifespan)

@app.get("/")
def read_root():
    return {"message": "API de NovaPay funcionando"}

#routers
#predict
app.include_router(predict.router, prefix="/predict", tags=["Predicciones"])
#ingesta
#eliminación