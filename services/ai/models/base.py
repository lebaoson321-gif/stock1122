"""Interface chung cho mọi model dự đoán — implement để train.py/evaluate.py
dùng được với bất kỳ model nào (XGBoost/Random Forest/LSTM) mà không phải
sửa code gọi."""
from abc import ABC, abstractmethod

import pandas as pd


class PredictionModel(ABC):
    name: str = "base"

    @abstractmethod
    def fit(self, X_train: pd.DataFrame, y_train: pd.Series) -> None:
        """Huấn luyện model trên tập train (đã chia theo thời gian)."""
        ...

    @abstractmethod
    def predict_proba_up(self, X: pd.DataFrame) -> pd.Series:
        """Trả về xác suất tăng giá (0.0–1.0) cho từng dòng trong X."""
        ...

    @abstractmethod
    def save(self, path: str) -> None: ...

    @abstractmethod
    def load(self, path: str) -> None: ...
