"""
Trạng thái phiên giao dịch + độ tươi của dữ liệu giá.

Web dùng endpoint này để hiển thị thị trường đang mở/đóng và để quyết
định có tự làm mới số liệu hay không — không tự tính giờ ở frontend, vì
đồng hồ máy người dùng có thể lệch hoặc đặt sai múi giờ.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.collectors.factory import get_market_data_provider
from app.collectors.vnstock_adapter import VALID_INDEX_CODES
from app.db import get_db
from app.models.market_index import MarketIndex
from app.models.realtime import RealtimeQuote
from app.schemas.market import (
    IndexBarOut,
    IndexPollItem,
    IndexPollResult,
    IndexQuote,
    IndexSyncItem,
    IndexSyncResult,
)
from app.services.market_session import get_market_status

router = APIRouter(prefix="/api/market", tags=["market"])

INDEX_NAMES = {
    "VNINDEX": "VN-Index",
    "HNX": "HNX-Index",
    "UPCOM": "UPCoM-Index",
    "VN30": "VN30",
}

# Sàn thật của từng chỉ số. VNINDEX/VN30 (HOSE) và HNX đóng khớp liên
# tục lúc 14:45 như nhau (cùng có ATC 14:30-14:45 rồi "post" thoả thuận
# tới 15:00 — xem market_session.py); CHỈ UPCOM không có ATO/ATC, khớp
# liên tục thẳng tới 15:00. Vẫn tra riêng exchange của từng mã (không
# dùng chung "HOSE" cho cả 4) dù HNX trùng giờ với HOSE — đúng theo
# nguyên tắc, và không phụ thuộc 2 sàn đó mãi mãi trùng giờ nhau.
#
# Dùng để hỏi get_market_status() ĐÚNG sàn của từng mã trong
# /indices/poll, KHÔNG dùng một cổng chung: nới cổng chung tới 15:00 để
# không bỏ sót UPCOM sẽ khiến 14:45-15:00 mỗi ngày VNINDEX/VN30/HNX bị
# poll lại và ghi is_intraday=True đè lên dòng đã chốt, sai tới khi
# daily-sync chạy buổi tối.
INDEX_EXCHANGE = {
    "VNINDEX": "HOSE",
    "VN30": "HOSE",
    "HNX": "HNX",
    "UPCOM": "UPCOM",
}


class MarketStatusResponse(BaseModel):
    state: str
    label: str
    is_open: bool
    is_trading_day: bool
    server_time: datetime
    next_change: datetime | None
    last_quote_at: datetime | None
    """Lần gần nhất job poll ghi được giá khớp — để web nói rõ dữ liệu cũ
    bao lâu thay vì để người dùng tưởng giá đang chạy real-time."""


@router.get("/status", response_model=MarketStatusResponse)
def market_status(db: Session = Depends(get_db)):
    # Luôn trả trạng thái của HOSE — hợp lý cho huy hiệu CHUNG của trang,
    # nhưng có giới hạn thật: UPCOM khớp liên tục tới 15:00 (không có
    # ATO/ATC) trong khi HOSE đóng lúc 14:45, nên người xem mã UPCOM lúc
    # 14:50 sẽ thấy huy hiệu "đã đóng cửa" dù mã đó vẫn đang khớp. (HNX
    # thì trùng giờ với HOSE — cùng có ATC 14:30-14:45 — nên không bị
    # ảnh hưởng.) Chưa cần sửa (huy hiệu này dùng chung cho cả trang,
    # không riêng theo mã), nhưng cần biết nếu sau này có huy hiệu theo
    # từng mã.
    status = get_market_status()
    last_quote_at = db.execute(select(func.max(RealtimeQuote.captured_at))).scalar_one_or_none()
    return MarketStatusResponse(
        state=status.state,
        label=status.label,
        is_open=status.is_open,
        is_trading_day=status.is_trading_day,
        server_time=status.server_time,
        next_change=status.next_change,
        last_quote_at=last_quote_at,
    )


@router.post("/indices/sync", response_model=IndexSyncResult)
def sync_indices(years: int = Query(1, ge=1, le=20), db: Session = Depends(get_db)):
    """Đồng bộ lịch sử 4 chỉ số thị trường. Lỗi ở 1 mã không chặn các mã
    còn lại (giống sync-defaults ở routers/sync.py)."""
    provider = get_market_data_provider()
    results = []
    for code in VALID_INDEX_CODES:
        try:
            bars = provider.get_index_history(code, years=years)
        except Exception as e:  # noqa: BLE001 — provider không chính thức, lỗi là chuyện thường
            results.append(IndexSyncItem(code=code, rows_synced=0, message=f"Lỗi khi lấy dữ liệu: {e}"))
            continue

        if not bars:
            results.append(IndexSyncItem(code=code, rows_synced=0, message="Không có dữ liệu"))
            continue

        for bar in bars:
            # is_intraday=False LUÔN được ghi ở đây, kể cả dòng của hôm
            # nay: đây là số CHỐT chính thức, ghi đè lên dòng "đang chạy"
            # mà /indices/poll để lại lúc trong phiên. Thiếu dòng này thì
            # dòng của hôm nay mãi mãi mang nhãn "đang giao dịch".
            values = {
                "open": bar.open, "high": bar.high, "low": bar.low,
                "close": bar.close, "volume": bar.volume, "is_intraday": False,
            }
            stmt = (
                insert(MarketIndex)
                .values(code=code, trade_date=bar.trade_date, **values)
                .on_conflict_do_update(index_elements=["code", "trade_date"], set_=values)
            )
            db.execute(stmt)
        db.commit()
        results.append(IndexSyncItem(code=code, rows_synced=len(bars), message="Đồng bộ thành công"))

    return IndexSyncResult(results=results)


@router.post("/indices/poll", response_model=IndexPollResult)
def poll_indices(force: bool = Query(False, description="Poll cả khi thị trường đang đóng"), db: Session = Depends(get_db)):
    """
    Poll giá trị đang chạy giữa phiên của 4 chỉ số thị trường, ghi vào
    `market_indices` với is_intraday=True — tương tự /api/stocks/poll-realtime
    nhưng cho chỉ số thay vì từng mã cổ phiếu.

    Ngoài giờ khớp lệnh thì chặn — nhưng xét THEO TỪNG MÃ bằng
    INDEX_EXCHANGE, không phải một cổng chung: CHỈ UPCOM khớp liên tục
    tới 15:00, còn HOSE (VNINDEX/VN30) và HNX đều đóng lúc 14:45.
    14:45-15:00 mỗi ngày chỉ UPCOM được poll, 3 mã còn lại bị bỏ qua (đã
    chốt). Không dựa vào cron canh đúng giờ, giống hệt
    /api/stocks/poll-realtime: job bên ngoài (GitHub Actions) có thể
    chạy trễ so với lịch.

    Dòng "đang chạy" này bị /indices/sync ghi đè bằng số CHỐT chính thức
    (is_intraday=False) khi daily-sync chạy sau giờ đóng cửa — không cần
    dọn dẹp gì thêm ở đây.
    """
    provider = get_market_data_provider()
    results = []
    for code in VALID_INDEX_CODES:
        # không đặt tên `status`: trùng với fastapi.status dùng ở trên
        session = get_market_status(exchange=INDEX_EXCHANGE[code])
        if not force and not session.is_open:
            results.append(IndexPollItem(code=code, rows_synced=0, message=f"Bỏ qua: {session.label}."))
            continue

        try:
            bar = provider.get_index_intraday(code)
        except Exception as e:  # noqa: BLE001 — provider không chính thức, lỗi là chuyện thường
            results.append(IndexPollItem(code=code, rows_synced=0, message=f"Lỗi khi lấy dữ liệu: {e}"))
            continue

        if bar is None:
            results.append(IndexPollItem(code=code, rows_synced=0, message="Không có nến nào của hôm nay"))
            continue

        values = {
            "open": bar.open, "high": bar.high, "low": bar.low,
            "close": bar.close, "volume": bar.volume, "is_intraday": True,
        }
        stmt = (
            insert(MarketIndex)
            .values(code=code, trade_date=bar.trade_date, **values)
            .on_conflict_do_update(index_elements=["code", "trade_date"], set_=values)
        )
        db.execute(stmt)
        db.commit()
        results.append(IndexPollItem(code=code, rows_synced=1, message="Đã cập nhật giá đang chạy"))

    return IndexPollResult(results=results)


@router.get("/indices", response_model=list[IndexQuote])
def get_indices(db: Session = Depends(get_db)):
    """Giá trị mới nhất + % thay đổi của cả 4 chỉ số, dùng cho khối
    "Tổng quan thị trường" ở trang chủ.

    Mốc tham chiếu là dòng liền trước dòng mới nhất trong market_indices —
    đơn giản hơn quy tắc ở routers/analysis.py vì chỉ số chỉ có DUY NHẤT
    một nguồn dữ liệu (đồng bộ qua /indices/sync), không có nguồn giá
    khớp trong phiên riêng biệt (realtime_quotes) như cổ phiếu nên không
    có 2 nguồn có thể lệch ngày nhau để phải xử lý riêng — 2 dòng gần
    nhất theo trade_date luôn đúng là "giá trị hiện tại" và "phiên đã
    đóng gần nhất trước đó", bất kể dòng mới nhất là hôm nay hay hôm qua.
    """
    quotes = []
    for code in VALID_INDEX_CODES:
        rows = (
            db.execute(
                select(MarketIndex)
                .where(MarketIndex.code == code)
                .order_by(MarketIndex.trade_date.desc())
                .limit(2)
            )
            .scalars()
            .all()
        )
        if not rows:
            continue
        latest = rows[0]
        prev = rows[1] if len(rows) > 1 else latest
        prev_close = float(prev.close)
        close = float(latest.close)
        change_point = close - prev_close
        change_pct = (change_point / prev_close * 100) if prev_close else 0.0
        quotes.append(
            IndexQuote(
                code=code, name=INDEX_NAMES[code], date=latest.trade_date, close=close,
                change_point=round(change_point, 2), change_pct=round(change_pct, 2),
                is_intraday=bool(latest.is_intraday),
            )
        )
    return quotes


@router.get("/indices/{code}/history", response_model=list[IndexBarOut])
def get_index_history_endpoint(code: str, db: Session = Depends(get_db)):
    code = code.upper()
    if code not in VALID_INDEX_CODES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mã chỉ số không hợp lệ: {code}. Chỉ hỗ trợ: {', '.join(VALID_INDEX_CODES)}",
        )

    rows = (
        db.execute(select(MarketIndex).where(MarketIndex.code == code).order_by(MarketIndex.trade_date))
        .scalars()
        .all()
    )
    return [
        IndexBarOut(
            date=r.trade_date, open=float(r.open), high=float(r.high),
            low=float(r.low), close=float(r.close), volume=r.volume,
        )
        for r in rows
    ]
