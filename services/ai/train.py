"""
CLI huấn luyện model dự đoán tăng/giảm giá phiên tiếp theo.

Dùng: python train.py --symbol FPT --model random_forest --out artifacts/FPT_random_forest.joblib

Cần biến môi trường DATABASE_URL trỏ tới Postgres/Supabase đang có dữ
liệu (đã sync qua apps/api) — xem README.md.
"""
import argparse
from pathlib import Path

from evaluate import evaluate_predictions
from features import FEATURE_COLUMNS, build_training_data
from models.lstm import LSTMModel
from models.random_forest import RandomForestModel
from models.xgboost_model import XGBoostModel

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
    parser.add_argument("--out", default=None, help="Đường dẫn lưu model (mặc định artifacts/<symbol>_<model>.joblib)")
    args = parser.parse_args()

    df = build_training_data(args.symbol)
    if len(df) < 30:
        raise SystemExit(
            f"Chỉ có {len(df)} dòng dữ liệu train cho {args.symbol} — cần tối thiểu ~30 phiên "
            "(khuyến nghị vài trăm phiên trở lên). Sync thêm dữ liệu lịch sử trước."
        )

    # Chia theo THỜI GIAN, không shuffle — dữ liệu time-series, shuffle sẽ
    # rò rỉ thông tin tương lai vào tập train.
    split_idx = int(len(df) * (1 - args.test_size))
    train_df, test_df = df.iloc[:split_idx], df.iloc[split_idx:]

    X_train, y_train = train_df[FEATURE_COLUMNS], train_df["label"]
    X_test, y_test = test_df[FEATURE_COLUMNS], test_df["label"]

    model = MODEL_REGISTRY[args.model]()
    model.fit(X_train, y_train)

    y_pred = (model.predict_proba_up(X_test) >= 0.5).astype(int)
    result = evaluate_predictions(y_test, y_pred)
    print(f"[{args.symbol}] {args.model} — train={len(train_df)} test={len(test_df)}")
    print(result)

    out_path = args.out or f"artifacts/{args.symbol.upper()}_{args.model}.joblib"
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    model.save(out_path)
    print(f"Đã lưu model: {out_path}")


if __name__ == "__main__":
    main()
