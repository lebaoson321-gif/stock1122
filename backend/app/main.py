"""
Stock Intelligence Platform — Backend API
Chạy: uvicorn app.main:app --reload --port 8000
Docs tự động: http://localhost:8000/docs
"""
from datetime import date
from typing import List

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.data_fetcher import fetch_price_history, fetch_company_info
from app.database import (
    init_db, upsert_stock, save_price_history, load_price_history,
    get_connection,
)
from app.indicators import compute_all_indicators
from app.schemas import StockSummary, PricePoint, AnalysisResponse, SyncResult

app = FastAPI(
    title="Stock Intelligence API",
    description="API phục vụ nền tảng phân tích & dự đoán chứng khoán HOSE",
    version="0.1.0",
)

# Cho phép frontend (React dev server) gọi API trong lúc phát triển.
# Khi deploy thật, nên giới hạn lại đúng domain của frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/stocks", response_model=List[StockSummary])
def list_stocks():
    """Danh sách các mã cổ phiếu đã có dữ liệu trong hệ thống."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT symbol, company_name, sector FROM stocks ORDER BY symbol")
    rows = cur.fetchall()
    conn.close()
    return [
        StockSummary(symbol=r[0], company_name=r[1] or "", sector=r[2] or "")
        for r in rows
    ]


@app.post("/api/stocks/{symbol}/sync", response_model=SyncResult)
def sync_stock(symbol: str, years: int = Query(5, ge=1, le=20)):
    """
    Lấy dữ liệu mới nhất từ HOSE (qua vnstock) và lưu/ghi đè vào database.
    Gọi endpoint này trước khi xem history/analysis lần đầu cho một mã mới.
    """
    symbol = symbol.upper()
    try:
        info = fetch_company_info(symbol)
        stock_id = upsert_stock(symbol, info.get("company_name", ""), info.get("sector", ""))
        df = fetch_price_history(symbol, years=years)
        if df.empty:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy dữ liệu cho mã {symbol}")
        save_price_history(stock_id, df)
        return SyncResult(symbol=symbol, rows_synced=len(df), message="Đồng bộ thành công")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Lỗi khi lấy dữ liệu: {e}")


def _load_indicator_df(symbol: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT stock_id FROM stocks WHERE symbol = ?", (symbol,))
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"Chưa có dữ liệu cho mã {symbol}. Gọi POST /api/stocks/{symbol}/sync trước.",
        )
    stock_id = row[0]
    df = load_price_history(stock_id)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"Chưa có dữ liệu giá cho mã {symbol}")
    return compute_all_indicators(df)


@app.get("/api/stocks/{symbol}/history", response_model=List[PricePoint])
def get_history(symbol: str):
    """Toàn bộ lịch sử giá + chỉ báo kỹ thuật, dùng để vẽ biểu đồ."""
    df = _load_indicator_df(symbol.upper())
    points = []
    for _, row in df.iterrows():
        points.append(PricePoint(
            date=row["date"].date(),
            open=row["open"], high=row["high"], low=row["low"],
            close=row["close"], volume=int(row["volume"]),
            ma20=_safe(row.get("MA20")), ma50=_safe(row.get("MA50")),
            ma200=_safe(row.get("MA200")), rsi=_safe(row.get("RSI")),
            macd=_safe(row.get("MACD")), macd_signal=_safe(row.get("MACD_signal")),
            macd_hist=_safe(row.get("MACD_hist")),
        ))
    return points


@app.get("/api/stocks/{symbol}/analysis", response_model=AnalysisResponse)
def get_analysis(symbol: str):
    """Trạng thái phân tích kỹ thuật mới nhất — dùng cho card tổng quan trên dashboard."""
    symbol = symbol.upper()
    df = _load_indicator_df(symbol)
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest

    change_pct = ((latest["close"] - prev["close"]) / prev["close"]) * 100 if prev["close"] else 0.0
    trend = "bullish" if (latest.get("MA20") or 0) > (latest.get("MA50") or 0) else "bearish"

    rsi = _safe(latest.get("RSI"))
    if rsi is None:
        rsi_status = "neutral"
    elif rsi > 70:
        rsi_status = "overbought"
    elif rsi < 30:
        rsi_status = "oversold"
    else:
        rsi_status = "neutral"

    macd_val = _safe(latest.get("MACD"))
    macd_sig = _safe(latest.get("MACD_signal"))
    macd_status = "buy" if (macd_val or 0) > (macd_sig or 0) else "sell"

    return AnalysisResponse(
        symbol=symbol,
        date=latest["date"].date(),
        close=latest["close"],
        change_pct=round(change_pct, 2),
        ma20=_safe(latest.get("MA20")),
        ma50=_safe(latest.get("MA50")),
        trend=trend,
        rsi=rsi,
        rsi_status=rsi_status,
        macd=macd_val,
        macd_signal_value=macd_sig,
        macd_signal_status=macd_status,
    )


def _safe(value):
    """pandas NaN -> None để JSON serialize không lỗi."""
    if value is None:
        return None
    try:
        import math
        if math.isnan(value):
            return None
    except TypeError:
        pass
    return float(value)
