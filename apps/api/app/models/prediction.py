from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AIPrediction(Base):
    """
    Kết quả dự đoán từ AI Module (XGBoost/Random Forest/LSTM).

    PHASE 2 — bảng tồn tại để schema sẵn sàng, nhưng chưa có model nào
    ghi dữ liệu vào đây. Xem services/ai/ cho scaffold huấn luyện model.
    """

    __tablename__ = "ai_predictions"
    __table_args__ = (
        UniqueConstraint(
            "stock_id", "prediction_date", "model_name", name="uq_ai_predictions_stock_date_model"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False, index=True)
    prediction_date: Mapped[date] = mapped_column(Date, nullable=False)
    model_name: Mapped[str] = mapped_column(String(64), nullable=False)  # xgboost | random_forest | lstm
    model_version: Mapped[str] = mapped_column(String(32), default="v0")

    prob_up: Mapped[float | None] = mapped_column(Numeric(5, 4))  # xác suất tăng giá phiên tới
    predicted_label: Mapped[str | None] = mapped_column(String(8))  # up | down
    actual_label: Mapped[str | None] = mapped_column(String(8))  # điền sau khi biết kết quả thật, để đánh giá

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
