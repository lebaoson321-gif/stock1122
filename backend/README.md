# Stock Intelligence — Backend API

FastAPI backend, tái sử dụng logic đã kiểm chứng từ bản MVP
(database SQLite, tính chỉ báo kỹ thuật, fetch dữ liệu HOSE qua vnstock).

## Cài đặt & chạy

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Swagger docs tự động tại: http://localhost:8000/docs

## Luồng sử dụng

1. **Đồng bộ dữ liệu cho một mã** (chạy lần đầu hoặc khi muốn cập nhật):
   ```
   POST /api/stocks/FPT/sync?years=5
   ```
2. **Lấy lịch sử giá + chỉ báo** (dùng để vẽ chart ở frontend):
   ```
   GET /api/stocks/FPT/history
   ```
3. **Lấy phân tích tổng quan mới nhất** (dùng cho card tổng quan):
   ```
   GET /api/stocks/FPT/analysis
   ```
4. **Danh sách mã đã có trong hệ thống**:
   ```
   GET /api/stocks
   ```

## Kết nối với Frontend

Frontend cần set biến `API_BASE_URL = "http://localhost:8000"` và gọi
đúng 4 endpoint trên. CORS đã bật `allow_origins=["*"]` để dev dễ dàng —
**nhớ giới hạn lại domain cụ thể trước khi deploy production**.

## Bước tiếp theo (khi mở rộng ngoài MVP)

- Thêm bảng `financial_report` + endpoint `/api/stocks/{symbol}/fundamentals`
- Thêm authentication (API key hoặc JWT) trước khi public
- Chuyển SQLite -> PostgreSQL khi cần nhiều người dùng đồng thời
- Thêm background job (Celery/APScheduler) để tự sync dữ liệu mỗi ngày
  thay vì gọi `/sync` thủ công
- Thêm endpoint `/api/stocks/{symbol}/predict` khi làm đến Module AI
