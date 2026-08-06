"""
Đánh giá model bằng Accuracy, Precision, Recall, F1 Score.

`evaluate_predictions()` không phụ thuộc train.py/features.py (còn là
stub) nên đã cài đặt đầy đủ — dùng được ngay khi có y_true/y_pred thật.
"""
from dataclasses import dataclass

import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score


@dataclass
class EvaluationResult:
    accuracy: float
    precision: float
    recall: float
    f1: float

    def __str__(self) -> str:
        return (
            f"Accuracy={self.accuracy:.4f}  Precision={self.precision:.4f}  "
            f"Recall={self.recall:.4f}  F1={self.f1:.4f}"
        )


def evaluate_predictions(y_true: pd.Series, y_pred: pd.Series) -> EvaluationResult:
    """y_true/y_pred: nhãn nhị phân (1 = tăng giá, 0 = giảm giá)."""
    return EvaluationResult(
        accuracy=accuracy_score(y_true, y_pred),
        precision=precision_score(y_true, y_pred, zero_division=0),
        recall=recall_score(y_true, y_pred, zero_division=0),
        f1=f1_score(y_true, y_pred, zero_division=0),
    )


if __name__ == "__main__":
    # Demo nhanh để xác nhận hàm chạy đúng — không phải kết quả model thật.
    demo_true = pd.Series([1, 0, 1, 1, 0, 1, 0, 0])
    demo_pred = pd.Series([1, 0, 0, 1, 0, 1, 1, 0])
    print("Demo (dữ liệu giả lập, KHÔNG phải model thật):")
    print(evaluate_predictions(demo_true, demo_pred))
