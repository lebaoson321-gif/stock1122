"""
Giá dùng để khớp lệnh mua/bán ảo và định giá danh mục.

Ưu tiên giá khớp trong phiên (`realtime_quotes`, do job poll ghi vào);
ngoài giờ hoặc khi dữ liệu quá cũ thì lùi về giá đóng cửa gần nhất
(`price_history`). Router KHÔNG tự đọc 2 bảng đó — mọi nơi cần "giá hiện
tại" đều đi qua đây để tránh mỗi chỗ tự định nghĩa "hiện tại" một kiểu.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.price import PriceHistory
from app.models.realtime import RealtimeQuote

# Giá khớp cũ hơn ngưỡng này coi như không còn phản ánh thị trường (job
# poll chạy ~15 phút/lần nên vẫn còn dư địa cho 1-2 lần poll lỗi).
REALTIME_MAX_AGE = timedelta(minutes=45)

# `price_history` lưu giá theo NGHÌN VND (FPT ~70.70 = 70.700đ) vì đó là
# đơn vị vnstock trả về ở API lịch sử. Bảng giá realtime của VCI đi qua
# một API khác và KHÔNG chắc cùng đơn vị — có thể là VND thô (70700).
# Lẫn lộn 2 đơn vị sẽ sai gấp 1000 lần số dư tiền, nên thay vì đoán,
# quy giá realtime về cùng đơn vị với giá đóng cửa gần nhất: thử các hệ
# số quy đổi khả dĩ, chọn hệ số cho ra giá gần giá đóng cửa nhất, và bỏ
# hẳn giá realtime nếu không hệ số nào cho kết quả hợp lý.
_SCALE_CANDIDATES = (Decimal(1), Decimal(1) / Decimal(1000), Decimal(1000))
# Biên độ trần/sàn HOSE là ±7%/phiên. Nới rộng thành 30% để bao được
# trường hợp giá đóng cửa tham chiếu đã cũ vài phiên (mã lâu chưa sync),
# nhưng vẫn đủ chặt để loại lệch đơn vị 1000 lần.
_MAX_DEVIATION = Decimal("0.30")


@dataclass
class CurrentPrice:
    price: Decimal
    # "realtime" (khớp trong phiên) hoặc "close" (giá đóng cửa gần nhất)
    source: str
    as_of: datetime


def _latest_close(db: Session, stock_id: int) -> tuple[Decimal, datetime] | None:
    row = db.execute(
        select(PriceHistory.close, PriceHistory.trade_date)
        .where(PriceHistory.stock_id == stock_id)
        .order_by(PriceHistory.trade_date.desc())
        .limit(1)
    ).first()
    if row is None or row.close is None:
        return None
    as_of = datetime.combine(row.trade_date, datetime.min.time(), tzinfo=timezone.utc)
    return Decimal(row.close), as_of


def _rescale_to_match(raw: Decimal, reference: Decimal) -> Decimal | None:
    """Quy giá realtime về cùng đơn vị với `reference` (giá đóng cửa).
    Trả về None nếu không hệ số nào cho ra giá hợp lý — khi đó caller nên
    bỏ giá realtime thay vì dùng một con số có thể sai đơn vị."""
    if reference <= 0:
        return None
    best: Decimal | None = None
    best_deviation: Decimal | None = None
    for scale in _SCALE_CANDIDATES:
        candidate = raw * scale
        deviation = abs(candidate - reference) / reference
        if deviation <= _MAX_DEVIATION and (best_deviation is None or deviation < best_deviation):
            best, best_deviation = candidate, deviation
    return best


def get_current_price(db: Session, stock_id: int) -> CurrentPrice | None:
    """Giá hiện tại của 1 mã, hoặc None nếu mã chưa có dữ liệu giá nào."""
    close = _latest_close(db, stock_id)

    quote = db.execute(
        select(RealtimeQuote.match_price, RealtimeQuote.captured_at)
        .where(RealtimeQuote.stock_id == stock_id, RealtimeQuote.match_price.is_not(None))
        .order_by(RealtimeQuote.captured_at.desc())
        .limit(1)
    ).first()

    if quote is not None and datetime.now(timezone.utc) - quote.captured_at <= REALTIME_MAX_AGE:
        raw = Decimal(quote.match_price)
        if close is None:
            # Chưa có giá đóng cửa để đối chiếu đơn vị — không dùng giá
            # realtime, vì đoán sai đơn vị nguy hiểm hơn là báo chưa có giá.
            return None
        rescaled = _rescale_to_match(raw, close[0])
        if rescaled is not None and rescaled > 0:
            return CurrentPrice(price=rescaled, source="realtime", as_of=quote.captured_at)

    if close is None:
        return None
    return CurrentPrice(price=close[0], source="close", as_of=close[1])
