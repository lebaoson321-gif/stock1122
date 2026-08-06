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

## Trạng thái hiện tại

`StockDashboard.jsx` đang chạy với **dữ liệu mô phỏng** (hàm `genSeries`)
để bạn xem giao diện đầy đủ ngay lập tức, không cần chờ backend/API thật.
Cấu trúc dữ liệu được đặt tên khớp với response của backend
(`ma20`, `ma50`, `rsi`, `macd`, `macd_signal`...) để việc nối API thật
sau này chỉ là thay nguồn dữ liệu, không phải viết lại giao diện.

## Nối với backend thật

1. Chạy backend (xem `/backend/README.md`):
   ```bash
   cd ../backend && uvicorn app.main:app --reload
   ```
2. Trong `StockDashboard.jsx`, thay lời gọi `genSeries(...)` bằng:
   ```jsx
   import { api } from "./api";
   const [data, setData] = useState([]);
   useEffect(() => {
     api.syncStock(symbol).then(() => api.getHistory(symbol)).then(setData);
   }, [symbol]);
   ```
3. Danh sách mã cổ phiếu (`WATCHLIST`) có thể thay bằng `api.listStocks()`.

## Cấu trúc

| File | Vai trò |
|---|---|
| `src/StockDashboard.jsx` | Toàn bộ giao diện dashboard |
| `src/api.js` | Service gọi backend FastAPI |
| `src/App.jsx` | Entry point |

## Bước tiếp theo

- Thêm ô tìm kiếm mã CP tự do (hiện đang là danh sách cố định 4 mã)
- Thêm trang riêng cho Chart (candlestick thật) và Analysis chi tiết
- Responsive cho mobile (hiện tối ưu cho desktop/tablet)
- Loading/error state khi gọi API thật (hiện dữ liệu mô phỏng luôn có sẵn)
