"""Level 1 model (theo roadmap gốc) — Random Forest, dễ debug, chạy tốt
với ít dữ liệu, không cần GPU."""
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from models.base import PredictionModel

_DEFAULTS = {"n_estimators": 200, "max_depth": 6, "min_samples_leaf": 10, "random_state": 42}


class RandomForestModel(PredictionModel):
    name = "random_forest"

    def __init__(self, **kwargs):
        params = {**_DEFAULTS, **kwargs}
        self._model = RandomForestClassifier(**params)

    def fit(self, X_train: pd.DataFrame, y_train: pd.Series) -> None:
        self._model.fit(X_train, y_train)

    def predict_proba_up(self, X: pd.DataFrame) -> pd.Series:
        proba = self._model.predict_proba(X)
        classes = list(self._model.classes_)
        up_idx = classes.index(1)
        return pd.Series(proba[:, up_idx], index=X.index)

    def save(self, path: str) -> None:
        import joblib

        joblib.dump(self._model, path)

    def load(self, path: str) -> None:
        import joblib

        self._model = joblib.load(path)
