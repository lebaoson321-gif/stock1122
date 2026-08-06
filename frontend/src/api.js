// Kết nối tới backend FastAPI (xem thư mục /backend).
// Đổi biến này khi deploy — dev local mặc định chạy uvicorn ở port 8000.
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE_URL}${path}`, options);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `API lỗi: ${res.status}`);
  }
  return res.json();
}

export const api = {
  listStocks: () => request("/api/stocks"),

  syncStock: (symbol, years = 5) =>
    request(`/api/stocks/${symbol}/sync?years=${years}`, { method: "POST" }),

  getHistory: (symbol) => request(`/api/stocks/${symbol}/history`),

  getAnalysis: (symbol) => request(`/api/stocks/${symbol}/analysis`),
};
