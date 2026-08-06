// Mirror của app/schemas/*.py bên backend (apps/api). Giữ tên field khớp
// 1-1 với JSON response để khỏi phải viết lớp map riêng.

export interface StockSummary {
  symbol: string;
  company_name: string;
  sector: string;
}

export interface PricePoint {
  date: string; // "YYYY-MM-DD"
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  ma20: number | null;
  ma50: number | null;
  ma200: number | null;
  ema12: number | null;
  ema26: number | null;
  rsi14: number | null;
  macd: number | null;
  macd_signal: number | null;
  macd_hist: number | null;
  bb_upper: number | null;
  bb_middle: number | null;
  bb_lower: number | null;
}

export interface AnalysisResponse {
  symbol: string;
  date: string;
  close: number;
  change_pct: number;
  ma20: number | null;
  ma50: number | null;
  trend: "bullish" | "bearish";
  rsi14: number | null;
  rsi_status: "overbought" | "oversold" | "neutral";
  macd: number | null;
  macd_signal_value: number | null;
  macd_signal_status: "buy" | "sell";
}

export interface SyncResult {
  symbol: string;
  rows_synced: number;
  message: string;
}

export interface ScoreResponse {
  symbol: string;
  available: true;
  date: string;
  trend_score: number | null;
  liquidity_score: number | null;
  volatility_score: number | null;
  total_score: number | null;
}

export interface ScorePlaceholder {
  symbol: string;
  available: false;
  message: string;
}

export type ScoreResult = ScoreResponse | ScorePlaceholder;

export interface PredictionResponse {
  symbol: string;
  available: true;
  date: string;
  model_name: string;
  model_version: string;
  prob_up: number | null;
  predicted_label: "up" | "down" | null;
}

export interface PredictionPlaceholder {
  symbol: string;
  available: false;
  message: string;
}

export type PredictionResult = PredictionResponse | PredictionPlaceholder;

export interface WatchlistItemOut {
  stock_id: number;
  symbol: string;
  company_name: string;
  added_at: string;
}

export interface WatchlistOut {
  id: number;
  name: string;
  items: WatchlistItemOut[];
}
