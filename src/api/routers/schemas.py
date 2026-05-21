from pydantic import BaseModel

class PredictionInput(BaseModel):
    # importa los campos del modelo
    feature1: float
    feature2: float