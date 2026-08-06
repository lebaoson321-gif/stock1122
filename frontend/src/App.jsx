import React from "react";
import StockDashboard from "./StockDashboard";

// StockDashboard.jsx (copy từ bản artifact) hiện đang dùng dữ liệu mô phỏng
// (hàm genSeries) để bạn xem trước giao diện ngay không cần chạy backend.
//
// Để nối dữ liệu HOSE thật:
// 1. Chạy backend: cd backend && uvicorn app.main:app --reload
// 2. Trong StockDashboard.jsx, thay hàm genSeries() bằng gọi api.getHistory(symbol)
//    (đã có sẵn trong src/api.js), ví dụ:
//
//    import { api } from "./api";
//    const [data, setData] = useState([]);
//    useEffect(() => {
//      api.syncStock(symbol).then(() => api.getHistory(symbol)).then(setData);
//    }, [symbol]);
//
// 3. Map field JSON trả về (đã cùng tên: ma20, ma50, rsi, macd, macd_signal...)
//    vào đúng props chart đang dùng.

export default function App() {
  return <StockDashboard />;
}
