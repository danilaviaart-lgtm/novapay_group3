from fastapi import APIRouter, Request
from app.routers.schemas import PredictionInput

router = APIRouter()

@router.post("/predict")
async def get_prediction(data: PredictionInput, request: Request):
    # Accedes al modelo a través de request.app.state
    model = request.app.state.model
    prediction = model.predict([list(data.dict().values())])
    return {"result": prediction.tolist()}