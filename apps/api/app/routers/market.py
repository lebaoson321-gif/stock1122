"""
Trạng thái phiên giao dịch + độ tươi của dữ liệu giá.

Web dùng endpoint này để hiển thị thị trường đang mở/đóng và để quyết
định có tự làm mới số liệu hay không — không tự tính giờ ở frontend, vì
đồng hồ máy người dùng có thể lệch hoặc đặt sai múi giờ.
"""
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.realtime import RealtimeQuote
from app.services.market_session import get_market_status

router = APIRouter(prefix="/api/market", tags=["market"])


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
