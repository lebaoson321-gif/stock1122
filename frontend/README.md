# Stock Intelligence — Frontend

Dashboard React, thiết kế lấy cảm hứng từ bảng điện giao dịch HOSE
(quy ước màu xanh/đỏ/vàng/tím/lam) kết hợp giao diện terminal hiện đại.

## Cài đặt & chạy

```bash
cd frontend
npm install
npm run dev
```

Mở http://localhost:5173

Backend cần chạy trước ở http://localhost:8000 (xem `/backend/README.md`),
nếu không dashboard sẽ hiện màn hình lỗi kèm nút "Thử lại".

## Trạng thái hiện tại

`StockDashboard.jsx` đã nối với backend FastAPI thật qua `src/api.js`:
- Giá, khối lượng, MA20/MA50/MA200, RSI, MACD: lấy từ `api.getHistory()` /
  `api.getAnalysis()`. Khi chọn một mã chưa từng sync, dashboard tự gọi
  `api.syncStock()` một lần rồi tải lại — có loading state trong lúc chờ
  (đồng bộ lần đầu có thể mất vài chục giây) và error state kèm nút thử
  lại nếu backend không phản hồi được.
- Điểm cơ bản (`FUNDAMENTALS`), tin tức/tâm lý thị trường (`NEWS`) và AI
  Prediction: vẫn là dữ liệu mô phỏng, vì backend chưa có các module này
  (xem `backend/README.md` — mục "Bước tiếp theo").

## Cấu trúc

| File | Vai trò |
|---|---|
| `src/StockDashboard.jsx` | Toàn bộ giao diện dashboard + gọi API |
| `src/api.js` | Service gọi backend FastAPI |
| `src/App.jsx` | Entry point |

## Bước tiếp theo

- Thêm ô tìm kiếm mã CP tự do (hiện đang là danh sách cố định 4 mã,
  có thể thay bằng `api.listStocks()`)
- Thêm trang riêng cho Chart (candlestick thật) và Analysis chi tiết
- Responsive cho mobile (hiện tối ưu cho desktop/tablet)
- Thay `FUNDAMENTALS`/`NEWS`/AI Prediction bằng dữ liệu thật khi backend
  có các module tương ứng
