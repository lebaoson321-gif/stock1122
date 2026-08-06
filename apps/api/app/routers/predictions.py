from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.routers.common import get_stock_or_404
from app.schemas.stock import PredictionPlaceholder

router = APIRouter(prefix="/api/stocks", tags=["predictions"])


@router.get("/{symbol}/prediction", response_model=PredictionPlaceholder)
def get_prediction(symbol: str, db: Session = Depends(get_db)):
    """AI Module (XGBoost/Random Forest/LSTM dự đoán tăng/giảm) — PHASE 2,
    chưa triển khai. Xem services/ai/ cho scaffold huấn luyện model."""
    stock = get_stock_or_404(db, symbol)
    return PredictionPlaceholder(symbol=stock.symbol)
