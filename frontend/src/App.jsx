import React from "react";
import StockDashboard from "./StockDashboard";

// StockDashboard.jsx đã nối với backend FastAPI thật qua src/api.js
// (api.getHistory / api.getAnalysis, tự gọi api.syncStock khi mã chưa
// có dữ liệu). Cần chạy backend trước: cd backend && uvicorn app.main:app --reload

export default function App() {
  return <StockDashboard />;
}
