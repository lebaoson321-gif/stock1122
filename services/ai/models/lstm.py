"""
PHASE 2 — chưa triển khai. Level 2 theo roadmap gốc — chỉ nên bắt đầu
SAU KHI Random Forest/XGBoost đã chạy ổn định và có baseline để so
sánh (LSTM cần nhiều dữ liệu hơn, khó debug hơn, dễ overfit với ít mã/
ít năm dữ liệu).
"""
import pandas as pd

from models.base import PredictionModel


class LSTMModel(PredictionModel):
    name = "lstm"

    def __init__(self, **kwargs):
        # Gợi ý: import torch.nn as nn; định nghĩa 1 nn.LSTM nhỏ + linear head
        raise NotImplementedError("Xem services/ai/README.md mục 'Việc cần làm'")

    def fit(self, X_train: pd.DataFrame, y_train: pd.Series) -> None:
        raise NotImplementedError

    def predict_proba_up(self, X: pd.DataFrame) -> pd.Series:
        raise NotImplementedError

    def save(self, path: str) -> None:
        raise NotImplementedError

    def load(self, path: str) -> None:
        raise NotImplementedError
