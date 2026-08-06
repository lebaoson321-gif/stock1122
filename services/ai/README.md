# AI Module — Stock Intelligence Platform

**PHASE 2 — scaffold, chưa có model thật.** Đây là bộ khung (interface +
CLI) để bắt đầu huấn luyện model dự đoán xác suất tăng/giảm giá phiên
tiếp theo — không phải model đã train sẵn. `apps/api` hiện trả về
placeholder tĩnh ở `GET /api/stocks/{symbol}/prediction`, chưa gọi gì ở
đây cả.

## Kiến trúc dự kiến

```
technical_indicators (Postgres, do apps/api ghi)
        │
        ▼
  features.py           build_feature_matrix(symbol) -> DataFrame đặc trưng
        │
        ▼
  models/{random_forest,xgboost_model,lstm}.py   implement Model interface (models/base.py)
        │
        ▼
  train.py               huấn luyện, lưu model (vd. joblib/torch state_dict)
        │
        ▼
  evaluate.py             Accuracy / Precision / Recall / F1 trên tập test
        │
        ▼
  predict.py (chưa viết)  load model đã train, ghi kết quả vào bảng
                           ai_predictions (Postgres) — sau đó
                           apps/api/app/routers/predictions.py mới nên
                           đọc bảng này thay vì trả placeholder tĩnh
```

## Cài đặt

```bash
cd services/ai
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

Cần biến môi trường `DATABASE_URL` trỏ tới cùng Postgres/Supabase mà
`apps/api` dùng (xem `apps/api/.env.example`) — service này đọc
`technical_indicators`/`price_history` trực tiếp, không qua API.

## Việc cần làm để đi từ scaffold -> model thật

1. `features.py::build_feature_matrix()` — hiện raise `NotImplementedError`.
   Cần quyết định tập đặc trưng (lag returns, chỉ báo kỹ thuật hiện có,
   có thêm dữ liệu khối lượng/thanh khoản hay không) và nhãn (label =
   giá đóng cửa phiên sau tăng hay giảm so với phiên hiện tại).
2. Bắt đầu với `random_forest.py` hoặc `xgboost_model.py` (Level 1 theo
   đúng roadmap gốc) trước khi làm `lstm.py` — mô hình cây quyết định dễ
   debug, ít dữ liệu vẫn chạy được, phù hợp để có baseline nhanh.
3. `train.py` — nạp feature matrix, chia train/test theo thời gian
   (KHÔNG shuffle ngẫu nhiên — dữ liệu time-series, shuffle sẽ rò rỉ
   thông tin tương lai vào tập train), fit model, lưu ra file.
4. `evaluate.py` — đã có sẵn hàm tính Accuracy/Precision/Recall/F1 bằng
   `sklearn.metrics`, chỉ cần nối với model đã train.
5. Viết `predict.py` mới: load model, tính feature cho ngày gần nhất,
   predict, upsert vào bảng `ai_predictions` (model + migration đã có
   sẵn ở `apps/api/app/models/prediction.py`).
6. Sửa `apps/api/app/routers/predictions.py` để đọc từ `ai_predictions`
   thay vì trả `PredictionPlaceholder` tĩnh.
7. Cân nhắc: chạy training định kỳ (không phải mỗi request) — có thể
   thêm 1 scheduler job riêng trong `apps/api/app/scheduler.py` (job
   mới, KHÔNG chạy trong service `api`/`worker` hiện tại vì training
   tốn CPU/RAM khác hẳn profile của các job đồng bộ dữ liệu) hoặc một
   cron job độc lập gọi `train.py` rồi `predict.py`.
