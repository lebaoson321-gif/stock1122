"""
PHASE 2 — chưa triển khai. Model khởi điểm được khuyến nghị (Level 1
theo roadmap gốc) vì dễ debug, chạy tốt với ít dữ liệu, không cần GPU.
"""
import pandas as pd

from models.base import PredictionModel


class RandomForestModel(PredictionModel):
    name = "random_forest"

    def __init__(self, **kwargs):
        # Gợi ý: from sklearn.ensemble import RandomForestClassifier
        raise NotImplementedError("Xem services/ai/README.md mục 'Việc cần làm'")

    def fit(self, X_train: pd.DataFrame, y_train: pd.Series) -> None:
        raise NotImplementedError

    def predict_proba_up(self, X: pd.DataFrame) -> pd.Series:
        raise NotImplementedError

    def save(self, path: str) -> None:
        raise NotImplementedError

    def load(self, path: str) -> None:
        raise NotImplementedError
