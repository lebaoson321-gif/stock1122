# AI Module — Stock Intelligence Platform

Dự đoán xác suất tăng/giảm giá phiên tiếp theo. `Random Forest` (Level 1
theo roadmap gốc) đã cài đặt thật và chạy được end-to-end; `XGBoost` và
`LSTM` vẫn là scaffold (`models/{xgboost_model,lstm}.py`) — xem mục
"Việc tiếp theo" bên dưới.

## Kiến trúc

```
technical_indicators/price_history (Postgres, do apps/api ghi)
        │
        ▼
  features.py            build_training_data(symbol) / get_latest_features(symbol)
        │
        ▼
  models/random_forest.py   implement Model interface (models/base.py)
        │
        ▼
  train.py                 train/test split theo thời gian, lưu model (joblib)
        │
        ▼
  evaluate.py               Accuracy / Precision / Recall / F1
        │
        ▼
  predict.py                load model, dự đoán phiên gần nhất, upsert vào
                             bảng ai_predictions (Postgres)
        │
        ▼
  apps/api/app/routers/predictions.py   CHỈ ĐỌC ai_predictions, không
                                         train/predict trong tiến trình API
```

## Cài đặt

```bash
cd services/ai
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # điền DATABASE_URL — cùng Postgres/Supabase với apps/api
```

## Chạy

```bash
# 1. Huấn luyện — cần mã đã sync đủ dữ liệu lịch sử (khuyến nghị vài
#    trăm phiên trở lên; tối thiểu ~30 phiên để chạy được, nhưng số
#    liệu đánh giá sẽ không đáng tin với ít dữ liệu như vậy)
python train.py --symbol FPT --model random_forest
# In ra Accuracy/Precision/Recall/F1, lưu model vào artifacts/FPT_random_forest.joblib

# 2. Dự đoán phiên tới, ghi vào Postgres
python predict.py --symbol FPT --model random_forest --model-path artifacts/FPT_random_forest.joblib
```

Sau bước 2, `GET /api/stocks/FPT/prediction` ở backend sẽ trả kết quả
thật thay vì placeholder.

## Đặc trưng (features.py::FEATURE_COLUMNS)

`return_1d/5d/10d` (biến động giá gần đây), `volume_ratio` (khối lượng
hôm nay so với TB 20 phiên), `rsi14`, `macd`, `macd_hist`, `dist_ma20`,
`dist_ma50` (khoảng cách giá tới MA, chuẩn hoá theo %), `bb_position`
(vị trí giá trong dải Bollinger, 0=chạm dải dưới, 1=chạm dải trên).
Nhãn: `1` nếu `close(t+1) > close(t)`, ngược lại `0`.

Train/test split theo **thời gian** (không shuffle) — dữ liệu
time-series, shuffle sẽ rò rỉ thông tin tương lai vào tập train.

## Đã kiểm chứng

Chạy end-to-end trên Postgres local với dữ liệu giả lập (chu kỳ xác
định, không phải dữ liệu thị trường thật): `train.py` chạy không lỗi,
`evaluate.py` tính đúng 4 chỉ số, `predict.py` ghi đúng 1 dòng vào
`ai_predictions` (upsert idempotent — chạy lại không tạo dòng trùng),
và endpoint `/prediction` trả đúng dữ liệu thật khi có, trả placeholder
khi mã chưa được predict, trả 404 khi mã không tồn tại. **Chưa kiểm
chứng được độ chính xác trên dữ liệu thị trường thật** — cần bạn tự
train trên dữ liệu đã sync qua HOSE thật và tự đánh giá.

## Việc tiếp theo

1. **XGBoost** (`models/xgboost_model.py`) — cùng interface với Random
   Forest, thường cho kết quả tốt hơn trên dữ liệu tabular; implement
   tương tự `random_forest.py`.
2. **LSTM** (`models/lstm.py`) — chỉ nên bắt đầu SAU KHI có baseline ổn
   định từ Random Forest/XGBoost (cần nhiều dữ liệu hơn, khó debug hơn,
   dễ overfit với ít mã/ít năm dữ liệu).
3. **Tự động hoá training/predict định kỳ** — hiện phải chạy tay 2
   lệnh trên. Có thể thêm 1 scheduler job riêng trong
   `apps/api/app/scheduler.py` (KHÔNG chạy trong service `api`/`worker`
   hiện tại — training tốn CPU/RAM khác hẳn profile job đồng bộ dữ
   liệu, nên tách service riêng) hoặc 1 cron job độc lập/Render One-Off
   Job gọi `train.py` rồi `predict.py` sau mỗi lần sync dữ liệu mới.
4. **Đánh giá lại theo thời gian**: cột `ai_predictions.actual_label`
   đã có sẵn trong schema nhưng chưa có job nào điền — cần 1 job điền
   `actual_label` sau khi biết kết quả thật (phiên kế tiếp đã đóng cửa),
   để có thể tính accuracy thực tế theo thời gian, không chỉ trên tập
   test lúc train.
