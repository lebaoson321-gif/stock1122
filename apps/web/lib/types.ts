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
  /** Giá dùng để hiển thị/giao dịch — cùng nguồn với danh mục ảo. */
  current_price: number;
  price_source: string;
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

export interface PositionOut {
  stock_id: number;
  symbol: string;
  company_name: string;
  quantity: number;
  /** Nghìn VND/cp — cùng đơn vị giá trên biểu đồ. */
  avg_cost: number;
  current_price: number | null;
  price_source: string | null;
  /** VND */
  market_value: number | null;
  cost_value: number;
  pnl: number | null;
  pnl_pct: number | null;
}

export interface PortfolioOut {
  id: number;
  available?: true;
  initial_capital: number;
  cash_balance: number;
  positions: PositionOut[];
  holdings_value: number;
  total_value: number;
  total_pnl: number;
  total_pnl_pct: number;
}

export interface PortfolioMissing {
  available: false;
  message: string;
}

export type PortfolioResult = PortfolioOut | PortfolioMissing;

export interface TransactionOut {
  id: number;
  symbol: string;
  side: "buy" | "sell";
  quantity: number;
  price: number;
  amount: number;
  price_source: string;
  executed_at: string;
}

export interface OrderResult {
  transaction: TransactionOut;
  portfolio: PortfolioOut;
}

export interface FundamentalsResponse {
  symbol: string;
  available: true;
  company_name: string;
  market_cap: number | null;
  pe: number | null;
  pb: number | null;
  eps: number | null;
  roe: number | null;
  roa: number | null;
  dividend_yield: number | null;
  issue_share: number | null;
  charter_capital: number | null;
  company_profile: string | null;
  industry: string | null;
  fetched_at: string;
}

export interface FundamentalsUnavailable {
  symbol: string;
  available: false;
  message: string;
}

export type FundamentalsResult = FundamentalsResponse | FundamentalsUnavailable;

export type MarketState =
  | "pre_open"
  | "ato"
  | "morning"
  | "lunch"
  | "afternoon"
  | "atc"
  | "post"
  | "closed"
  | "weekend";

export interface MarketStatus {
  state: MarketState;
  label: string;
  is_open: boolean;
  is_trading_day: boolean;
  server_time: string;
  next_change: string | null;
  last_quote_at: string | null;
}
