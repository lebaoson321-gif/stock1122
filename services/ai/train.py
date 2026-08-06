"""
CLI huấn luyện model — PHASE 2, chưa chạy được thật vì features.py và
models/*.py còn là stub (raise NotImplementedError). Khung CLI này đã
sẵn để cắm logic thật vào sau, không cần đổi cách gọi.

Dùng (sau khi implement xong): python train.py --symbol FPT --model random_forest
"""
import argparse

from evaluate import evaluate_predictions
from features import build_feature_matrix
from models.random_forest import RandomForestModel
from models.xgboost_model import XGBoostModel
from models.lstm import LSTMModel

MODEL_REGISTRY = {
    "random_forest": RandomForestModel,
    "xgboost": XGBoostModel,
    "lstm": LSTMModel,
}


def main():
    parser = argparse.ArgumentParser(description="Huấn luyện model dự đoán tăng/giảm giá")
    parser.add_argument("--symbol", required=True, help="Mã cổ phiếu, VD: FPT")
    parser.add_argument("--model", choices=MODEL_REGISTRY.keys(), default="random_forest")
    parser.add_argument("--test-size", type=float, default=0.2, help="Tỷ lệ tập test (chia theo thời gian)")
    args = parser.parse_args()

    df = build_feature_matrix(args.symbol)  # hiện raise NotImplementedError

    split_idx = int(len(df) * (1 - args.test_size))
    train_df, test_df = df.iloc[:split_idx], df.iloc[split_idx:]  # KHÔNG shuffle — time-series

    X_train, y_train = train_df.drop(columns=["label"]), train_df["label"]
    X_test, y_test = test_df.drop(columns=["label"]), test_df["label"]

    model = MODEL_REGISTRY[args.model]()
    model.fit(X_train, y_train)

    y_pred = (model.predict_proba_up(X_test) >= 0.5).astype(int)
    result = evaluate_predictions(y_test, y_pred)
    print(f"[{args.symbol}] {args.model}: {result}")


if __name__ == "__main__":
    main()
