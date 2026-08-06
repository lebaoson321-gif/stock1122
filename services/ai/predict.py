"""
CLI dự đoán: load model đã train (từ train.py), tính đặc trưng của
phiên gần nhất, dự đoán xác suất tăng giá phiên kế tiếp, upsert kết quả
vào bảng ai_predictions (Postgres) — apps/api/app/routers/predictions.py
đọc bảng này để trả về cho frontend.

Dùng: python predict.py --symbol FPT --model random_forest --model-path artifacts/FPT_random_forest.joblib
"""
import argparse
from datetime import date

import pandas as pd
from sqlalchemy import text

from db import get_engine
from features import FEATURE_COLUMNS, get_latest_features
from models.lstm import LSTMModel
from models.random_forest import RandomForestModel
from models.xgboost_model import XGBoostModel

MODEL_REGISTRY = {
    "random_forest": RandomForestModel,
    "xgboost": XGBoostModel,
    "lstm": LSTMModel,
}

MODEL_VERSION = "v1"

_UPSERT = text(
    """
    INSERT INTO ai_predictions (stock_id, prediction_date, model_name, model_version, prob_up, predicted_label)
    SELECT s.id, :prediction_date, :model_name, :model_version, :prob_up, :predicted_label
    FROM stocks s WHERE s.symbol = :symbol
    ON CONFLICT (stock_id, prediction_date, model_name) DO UPDATE SET
        model_version = EXCLUDED.model_version,
        prob_up = EXCLUDED.prob_up,
        predicted_label = EXCLUDED.predicted_label
    """
)


def main():
    parser = argparse.ArgumentParser(description="Dự đoán xác suất tăng giá phiên kế tiếp")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--model", choices=MODEL_REGISTRY.keys(), default="random_forest")
    parser.add_argument("--model-path", required=True, help="File model đã lưu (từ train.py --out)")
    args = parser.parse_args()

    latest = get_latest_features(args.symbol)
    if latest is None:
        raise SystemExit(f"Không đủ dữ liệu để tính đặc trưng cho {args.symbol}.")

    model = MODEL_REGISTRY[args.model]()
    model.load(args.model_path)

    X = pd.DataFrame([latest[FEATURE_COLUMNS]])
    prob_up = float(model.predict_proba_up(X).iloc[0])
    predicted_label = "up" if prob_up >= 0.5 else "down"

    # Dự đoán cho phiên KẾ TIẾP sau ngày dữ liệu gần nhất (đặc trưng
    # tính từ phiên latest["trade_date"], dự đoán chiều của phiên sau đó).
    prediction_date = latest["trade_date"]
    if isinstance(prediction_date, str):
        prediction_date = date.fromisoformat(prediction_date)

    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            _UPSERT,
            {
                "symbol": args.symbol.upper(), "prediction_date": prediction_date,
                "model_name": args.model, "model_version": MODEL_VERSION,
                "prob_up": round(prob_up, 4), "predicted_label": predicted_label,
            },
        )

    print(f"[{args.symbol}] {args.model}: prob_up={prob_up:.4f} ({predicted_label}) — đã ghi vào ai_predictions")


if __name__ == "__main__":
    main()
