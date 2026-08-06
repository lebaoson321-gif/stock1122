"""PHASE 2 — chưa triển khai. Level 1 theo roadmap gốc (cùng với Random Forest)."""
import pandas as pd

from models.base import PredictionModel


class XGBoostModel(PredictionModel):
    name = "xgboost"

    def __init__(self, **kwargs):
        # Gợi ý: import xgboost as xgb; xgb.XGBClassifier(...)
        raise NotImplementedError("Xem services/ai/README.md mục 'Việc cần làm'")

    def fit(self, X_train: pd.DataFrame, y_train: pd.Series) -> None:
        raise NotImplementedError

    def predict_proba_up(self, X: pd.DataFrame) -> pd.Series:
        raise NotImplementedError

    def save(self, path: str) -> None:
        raise NotImplementedError

    def load(self, path: str) -> None:
        raise NotImplementedError
