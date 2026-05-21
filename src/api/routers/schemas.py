from pydantic import BaseModel

class PredictionInput(BaseModel):
    # importa los campos del modelo
    id: int 
    feature2: float