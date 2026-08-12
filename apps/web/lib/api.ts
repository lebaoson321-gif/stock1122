// Kết nối tới backend FastAPI (xem apps/api). Cùng pattern với
// legacy/frontend/src/api.js — chỉ thêm kiểu TypeScript và header auth
// cho các endpoint watchlist cần đăng nhập.
import type {
  AnalysisResponse,
  FundamentalsResult,
  OrderResult,
  PortfolioOut,
  PortfolioResult,
  PredictionResult,
  PricePoint,
  ScoreResult,
  StockSummary,
  SyncResult,
  TransactionOut,
  WatchlistOut,
} from "./types";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, options);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `API lỗi: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

function authHeaders(accessToken: string): HeadersInit {
  return { Authorization: `Bearer ${accessToken}` };
}

export const api = {
  listStocks: (q?: string) =>
    request<StockSummary[]>(`/api/stocks${q ? `?q=${encodeURIComponent(q)}` : ""}`),

  syncStock: (symbol: string, years = 5) =>
    request<SyncResult>(`/api/stocks/${symbol}/sync?years=${years}`, { method: "POST" }),

  syncDefaults: (years = 5) =>
    request<SyncResult[]>(`/api/stocks/sync-defaults?years=${years}`, { method: "POST" }),

  getHistory: (symbol: string) => request<PricePoint[]>(`/api/stocks/${symbol}/history`),

  getAnalysis: (symbol: string) => request<AnalysisResponse>(`/api/stocks/${symbol}/analysis`),

  getScore: (symbol: string) => request<ScoreResult>(`/api/stocks/${symbol}/score`),

  getPrediction: (symbol: string) => request<PredictionResult>(`/api/stocks/${symbol}/prediction`),

  getFundamentals: (symbol: string) =>
    request<FundamentalsResult>(`/api/stocks/${symbol}/fundamentals`),

  getWatchlist: (accessToken: string) =>
    request<WatchlistOut>(`/api/watchlist`, { headers: authHeaders(accessToken) }),

  addWatchlistItem: (symbol: string, accessToken: string) =>
    request<WatchlistOut>(`/api/watchlist/items`, {
      method: "POST",
      headers: { ...authHeaders(accessToken), "Content-Type": "application/json" },
      body: JSON.stringify({ symbol }),
    }),

  removeWatchlistItem: (stockId: number, accessToken: string) =>
    request<WatchlistOut>(`/api/watchlist/items/${stockId}`, {
      method: "DELETE",
      headers: authHeaders(accessToken),
    }),

  getPortfolio: (accessToken: string) =>
    request<PortfolioResult>(`/api/portfolio`, { headers: authHeaders(accessToken) }),

  createPortfolio: (initialCapital: number, accessToken: string) =>
    request<PortfolioOut>(`/api/portfolio`, {
      method: "POST",
      headers: { ...authHeaders(accessToken), "Content-Type": "application/json" },
      body: JSON.stringify({ initial_capital: initialCapital }),
    }),

  resetPortfolio: (accessToken: string, initialCapital?: number) =>
    request<PortfolioOut>(`/api/portfolio/reset`, {
      method: "POST",
      headers: { ...authHeaders(accessToken), "Content-Type": "application/json" },
      // Body `null` hợp lệ: endpoint nhận `PortfolioCreate | None` — không
      // truyền vốn mới nghĩa là giữ nguyên mức vốn ban đầu.
      body: initialCapital === undefined ? "null" : JSON.stringify({ initial_capital: initialCapital }),
    }),

  placeOrder: (
    symbol: string,
    side: "buy" | "sell",
    quantity: number,
    accessToken: string,
  ) =>
    request<OrderResult>(`/api/portfolio/orders`, {
      method: "POST",
      headers: { ...authHeaders(accessToken), "Content-Type": "application/json" },
      body: JSON.stringify({ symbol, side, quantity }),
    }),

  getTransactions: (accessToken: string, limit = 50) =>
    request<TransactionOut[]>(`/api/portfolio/transactions?limit=${limit}`, {
      headers: authHeaders(accessToken),
    }),
};
