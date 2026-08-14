"""
Chỉ số cơ bản doanh nghiệp — đọc cache trong DB, tự nạp lại khi thiếu
hoặc quá cũ (xem models/fundamentals.py về lý do cache).
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.collectors.factory import get_fundamentals_provider
from app.db import get_db
from app.models.fundamentals import CompanyFundamentals
from app.routers.common import get_stock_or_404
from app.schemas.fundamentals import FundamentalsResponse, FundamentalsUnavailable
from app.services.fundamentals_math import normalise_profitability, roe_roa_from_fireant
from app.services.pricing import get_current_price
from app.services.trading import PRICE_UNIT_VND

router = APIRouter(prefix="/api/stocks", tags=["fundamentals"])

# Chỉ số cơ bản đổi theo quý — 7 ngày là đủ tươi, mà vẫn tránh gọi
# provider liên tục.
CACHE_TTL = timedelta(days=7)

_STORED_FIELDS = (
    "market_cap", "pe", "pb", "eps", "roe", "roa",
    "dividend_yield", "issue_share", "charter_capital",
    "company_profile", "industry", "raw",
)


def _fetch_and_store(db: Session, stock_id: int, symbol: str) -> CompanyFundamentals | None:
    provider = get_fundamentals_provider()
    try:
        data = provider.get_company_fundamentals(symbol)
    except Exception:  # noqa: BLE001 — provider không chính thức, lỗi là chuyện thường
        return None

    values = {field: getattr(data, field) for field in _STORED_FIELDS}
    if all(v is None for v in values.values()):
        # Không moi được gì — đừng ghi một dòng rỗng rồi cache nó suốt 7
        # ngày; để lần sau thử lại.
        return None

    values["fetched_at"] = datetime.now(timezone.utc)
    stmt = (
        insert(CompanyFundamentals)
        .values(stock_id=stock_id, **values)
        .on_conflict_do_update(index_elements=["stock_id"], set_=values)
        .returning(CompanyFundamentals)
    )
    row = db.execute(stmt).scalar_one()
    db.commit()
    return row


def _market_cap(db: Session, stock_id: int, cached: CompanyFundamentals) -> float | None:
    """Vốn hoá = số cổ phiếu lưu hành × giá hiện tại.

    Tính lại thay vì dùng thẳng số của provider: với DHC, provider trả
    1,29 nghìn tỷ trong khi 106,2 triệu cp × 34.900đ = 3,71 nghìn tỷ —
    lệch 2,9 lần, không phải bội số 1000 nên không phải sai đơn vị mà là
    khớp nhầm cột. Hai đầu vào ở đây đều đã đối chiếu đúng với thực tế,
    và đây đúng là định nghĩa của vốn hoá.

    Chỉ lùi về số của provider khi thiếu một trong hai đầu vào.
    """
    if cached.issue_share is None:
        return float(cached.market_cap) if cached.market_cap is not None else None
    current = get_current_price(db, stock_id)
    if current is None:
        return float(cached.market_cap) if cached.market_cap is not None else None
    # Giá lưu theo nghìn VND (xem services/trading.py), vốn hoá trả về VND.
    return float(cached.issue_share) * float(current.price) * float(PRICE_UNIT_VND)


@router.get(
    "/{symbol}/fundamentals",
    response_model=FundamentalsResponse | FundamentalsUnavailable,
)
def get_fundamentals(
    symbol: str,
    refresh: bool = Query(False, description="Bỏ qua cache, lấy lại từ provider"),
    db: Session = Depends(get_db),
):
    stock = get_stock_or_404(db, symbol)

    cached = db.execute(
        select(CompanyFundamentals).where(CompanyFundamentals.stock_id == stock.id)
    ).scalar_one_or_none()

    stale = cached is None or datetime.now(timezone.utc) - cached.fetched_at > CACHE_TTL
    if refresh or stale:
        fresh = _fetch_and_store(db, stock.id, stock.symbol)
        if fresh is not None:
            cached = fresh
        # Nếu nạp mới thất bại mà vẫn còn cache cũ: trả cache cũ kèm
        # fetched_at để UI tự nói rõ dữ liệu cũ từ bao giờ — vẫn hơn là
        # báo lỗi và không hiện gì.

    if cached is None:
        return FundamentalsUnavailable(symbol=stock.symbol)

    pe = float(cached.pe) if cached.pe is not None else None
    pb = float(cached.pb) if cached.pb is not None else None
    raw_roe = float(cached.roe) if cached.roe is not None else None
    raw_roa = float(cached.roa) if cached.roa is not None else None
    if (cached.raw or {}).get("_source") == "fireant":
        # FireAnt trả ROE/ROA đã là phần trăm — dùng thẳng, chỉ lọc giá
        # trị vô lý. Xem services/fundamentals_math.py::roe_roa_from_fireant.
        roe, roa = roe_roa_from_fireant(raw_roe, raw_roa)
    else:
        # vnstock (VCI): đơn vị ROE/ROA không xác định được từ chính nó —
        # suy ra bằng đẳng thức ROE = P/B ÷ P/E.
        roe, roa = normalise_profitability(pe, pb, raw_roe, raw_roa)

    return FundamentalsResponse(
        symbol=stock.symbol,
        company_name=stock.company_name,
        market_cap=_market_cap(db, stock.id, cached),
        pe=pe,
        pb=pb,
        eps=cached.eps,
        roe=roe,
        roa=roa,
        dividend_yield=cached.dividend_yield,
        issue_share=cached.issue_share,
        charter_capital=cached.charter_capital,
        company_profile=cached.company_profile,
        industry=cached.industry or stock.sector or None,
        fetched_at=cached.fetched_at,
    )
