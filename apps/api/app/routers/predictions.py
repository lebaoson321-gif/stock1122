from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.prediction import AIPrediction
from app.routers.common import get_stock_or_404
from app.schemas.stock import PredictionPlaceholder, PredictionResponse

router = APIRouter(prefix="/api/stocks", tags=["predictions"])


@router.get("/{symbol}/prediction", response_model=PredictionResponse | PredictionPlaceholder)
def get_prediction(symbol: str, db: Session = Depends(get_db)):
    """
    Dự đoán AI (XGBoost/Random Forest/LSTM) cho xác suất tăng giá phiên
    kế tiếp. Backend chỉ ĐỌC bảng ai_predictions — việc train/predict
    chạy độc lập ở services/ai/ (train.py rồi predict.py), không chạy
    trong tiến trình API. Trả placeholder (available=False) nếu mã tồn
    tại nhưng chưa từng chạy predict.py.
    """
    stock = get_stock_or_404(db, symbol)
    prediction = db.execute(
        select(AIPrediction)
        .where(AIPrediction.stock_id == stock.id)
        .order_by(AIPrediction.prediction_date.desc(), AIPrediction.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    if prediction is None:
        return PredictionPlaceholder(symbol=stock.symbol)

    return PredictionResponse(
        symbol=stock.symbol, date=prediction.prediction_date,
        model_name=prediction.model_name, model_version=prediction.model_version,
        prob_up=float(prediction.prob_up) if prediction.prob_up is not None else None,
        predicted_label=prediction.predicted_label,
    )
