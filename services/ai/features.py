"""
Xây dựng feature matrix cho AI Module từ dữ liệu đã có trong Postgres
(bảng price_history, technical_indicators — do apps/api ghi).

PHASE 2 — chưa triển khai. Xem README.md mục "Việc cần làm" trước khi
implement: cần quyết định tập đặc trưng cụ thể và cách định nghĩa nhãn
(label) trước khi viết hàm này.
"""
import pandas as pd


def build_feature_matrix(symbol: str) -> pd.DataFrame:
    """
    Trả về DataFrame đặc trưng + nhãn cho 1 mã, sẵn sàng đưa vào
    train_test_split (theo thời gian, không shuffle).

    Gợi ý cột đặc trưng (chưa implement):
    - Giá: return 1/5/10 ngày gần nhất
    - Chỉ báo: ma20, ma50, rsi14, macd, macd_hist, khoảng cách tới
      bb_upper/bb_lower (từ bảng technical_indicators)
    - Khối lượng: volume so với trung bình N ngày

    Nhãn (label): 1 nếu close(t+1) > close(t), ngược lại 0.
    """
    raise NotImplementedError("Xem services/ai/README.md mục 'Việc cần làm'")
