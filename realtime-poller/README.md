# Realtime Poller

Script độc lập poll bảng giá khớp lệnh (price board) mỗi 60 giây cho tất
cả mã cổ phiếu đã có trong CSDL SQLite của backend (bảng `stocks`), và
in ra console. Không ghi vào DB, không gọi API backend.

## Yêu cầu

Backend đã sync ít nhất một mã trước đó (để bảng `stocks` có dữ liệu):

```bash
cd ../backend
uvicorn app.main:app --reload --port 8000
# ở terminal khác:
curl -X POST "http://localhost:8000/api/stocks/FPT/sync"
```

## Cài đặt & chạy

```bash
cd realtime-poller
pip install -r requirements.txt
python poller.py
```

`Ctrl+C` để dừng.

## Cấu hình

- Danh sách mã: tự động đọc từ `backend/app/stock_data.db`, đọc lại mỗi
  vòng lặp nên mã mới sync vào backend sẽ tự được poll ở lần kế tiếp.
- Chu kỳ poll: sửa hằng số `POLL_INTERVAL_SECONDS` trong `poller.py`
  (mặc định 60 giây).

## Lưu ý

`Trading.price_board()` của `vnstock` đôi khi đổi tên cột giữa các phiên
bản (đã gặp trường hợp này với `fetch_company_info` ở backend). Poller
dò nhiều tên cột khả dĩ cho giá/khối lượng khớp lệnh (`format_quote()`
trong `poller.py`); nếu vnstock đổi schema và không còn khớp tên nào,
sửa lại danh sách candidates trong hàm đó.
