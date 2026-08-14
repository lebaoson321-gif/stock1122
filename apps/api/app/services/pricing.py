"""
Giá dùng để khớp lệnh mua/bán ảo và định giá danh mục.

Ưu tiên giá khớp trong phiên (`realtime_quotes`, do job poll ghi vào);
ngoài giờ hoặc khi dữ liệu quá cũ thì lùi về giá đóng cửa gần nhất
(`price_history`). Router KHÔNG tự đọc 2 bảng đó — mọi nơi cần "giá hiện
tại" đều đi qua đây để tránh mỗi chỗ tự định nghĩa "hiện tại" một kiểu.
"""
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.price import PriceHistory
from app.models.realtime import RealtimeQuote
from app.services.market_session import VN_TZ

# Giá khớp được chấp nhận khi nó thuộc CHÍNH NGÀY GIAO DỊCH HÔM NAY (giờ
# VN), không giới hạn theo số phút.
#
# Trước đây dùng ngưỡng 45 phút, nhưng job poll chạy trên GitHub Actions
# gói miễn phí và thường xuyên trễ hoặc nhảy nhịp — quá 45 phút là giá
# vừa lấy được bị vứt đi để quay về giá đóng cửa của phiên TRƯỚC, tức là
# thay một số hơi cũ bằng một số cũ hơn hẳn.
#
# Giá khớp cuối cùng của hôm nay luôn sát thực tế hơn giá đóng cửa hôm
# qua, kể cả sau khi thị trường đã đóng và bảng `price_history` chưa kịp
# sync. Quote từ ngày trước thì bị loại — lúc đó giá đóng cửa mới đúng.

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


@dataclass
class PriceSnapshot:
    price: Decimal
    source: str
    change_pct: float | None


def get_price_snapshots(db: Session, stock_ids: list[int]) -> dict[int, PriceSnapshot]:
    """Giá hiện tại + % thay đổi cho NHIỀU mã cùng lúc.

    Danh sách mã có thể tới vài trăm dòng, gọi `get_current_price` từng mã
    sẽ thành vài trăm lượt truy vấn. Ở đây chỉ 2 truy vấn cho toàn bộ.
    Quy tắc chọn giá và quy đổi đơn vị giữ y hệt `get_current_price` —
    dùng chung `_rescale_to_match` để hai đường không lệch nhau.
    """
    if not stock_ids:
        return {}

    today_vn = datetime.now(VN_TZ).date()

    # 2 phiên gần nhất mỗi mã: phiên mới nhất để lấy giá, phiên liền trước
    # làm mốc tính % thay đổi.
    ranked = (
        select(
            PriceHistory.stock_id,
            PriceHistory.close,
            PriceHistory.trade_date,
            func.row_number()
            .over(partition_by=PriceHistory.stock_id, order_by=PriceHistory.trade_date.desc())
            .label("rn"),
        )
        .where(PriceHistory.stock_id.in_(stock_ids))
        .subquery()
    )
    closes: dict[int, list[tuple[Decimal, object]]] = {}
    for row in db.execute(select(ranked).where(ranked.c.rn <= 2).order_by(ranked.c.stock_id, ranked.c.rn)):
        closes.setdefault(row.stock_id, []).append((Decimal(row.close), row.trade_date))

    quotes = {
        row.stock_id: (Decimal(row.match_price), row.captured_at)
        for row in db.execute(
            select(RealtimeQuote.stock_id, RealtimeQuote.match_price, RealtimeQuote.captured_at)
            .where(
                RealtimeQuote.stock_id.in_(stock_ids),
                RealtimeQuote.match_price.is_not(None),
            )
            .distinct(RealtimeQuote.stock_id)
            .order_by(RealtimeQuote.stock_id, RealtimeQuote.captured_at.desc())
        )
    }

    snapshots: dict[int, PriceSnapshot] = {}
    for stock_id in stock_ids:
        rows = closes.get(stock_id)
        if not rows:
            continue
        latest_close, latest_date = rows[0]

        price, source = latest_close, "close"
        quote = quotes.get(stock_id)
        if quote is not None and quote[1].astimezone(VN_TZ).date() == today_vn:
            rescaled = _rescale_to_match(quote[0], latest_close)
            if rescaled is not None and rescaled > 0:
                price, source = rescaled, "realtime"

        # Cùng quy tắc mốc tham chiếu với routers/analysis.py.
        if source == "realtime" and latest_date != today_vn:
            reference = latest_close
        else:
            reference = rows[1][0] if len(rows) > 1 else latest_close

        change_pct = float((price - reference) / reference * 100) if reference else None
        snapshots[stock_id] = PriceSnapshot(
            price=price, source=source, change_pct=round(change_pct, 2) if change_pct is not None else None
        )

    return snapshots


@dataclass
class IntradayCandle:
    trade_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


def get_intraday_candle(db: Session, stock_id: int) -> IntradayCandle | None:
    """Cây nến ĐANG CHẠY của phiên hôm nay, dựng từ bảng giá.

    Vì sao cần: `price_history` chỉ có dòng của hôm nay SAU KHI job đồng bộ
    chạy (sau giờ đóng cửa), nên trong phiên cây nến cuối trên biểu đồ vẫn
    là của hôm qua — biểu đồ chậm một ngày so với giá hiển thị ở tiêu đề.

    Số liệu lấy nguyên từ bảng giá chứ KHÔNG tự tổng hợp từ các lần poll:
    provider trả sẵn giá mở/cao/thấp và khối lượng luỹ kế của cả phiên, nên
    chính xác tuyệt đối. Nếu tự gom từ các mẫu poll 10 phút/lần thì sẽ bỏ
    sót đỉnh/đáy xảy ra giữa hai lần poll.

    Trả None khi: chưa có giá khớp hôm nay, hoặc `price_history` đã có dòng
    của hôm nay rồi (lúc đó dùng dòng thật, không cần nến tạm).
    """
    quote = db.execute(
        select(RealtimeQuote)
        .where(RealtimeQuote.stock_id == stock_id, RealtimeQuote.match_price.is_not(None))
        .order_by(RealtimeQuote.captured_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if quote is None:
        return None

    # Ưu tiên ngày provider khai báo; thiếu thì suy từ lúc mình gọi.
    quote_date = quote.trading_date or quote.captured_at.astimezone(VN_TZ).date()
    if quote_date != datetime.now(VN_TZ).date():
        return None

    close = _latest_close(db, stock_id)
    if close is None:
        return None
    latest_close, latest_as_of = close
    if latest_as_of.date() >= quote_date:
        # price_history đã có phiên này rồi — dùng dữ liệu thật, không vẽ
        # thêm nến tạm chồng lên.
        return None

    # Giá bảng giá là VND thô (52300) còn price_history theo nghìn VND
    # (52.30) — quy đổi qua đúng hàm dùng cho giá hiện tại để hai đường
    # không thể lệch nhau.
    def rescaled(value) -> Decimal | None:
        return None if value is None else _rescale_to_match(Decimal(value), latest_close)

    close_price = rescaled(quote.match_price)
    if close_price is None or close_price <= 0:
        return None

    # Thiếu trường nào thì lấy giá khớp bù vào: một cây nến "phẳng" ở giá
    # hiện tại vẫn đúng hơn là không vẽ gì.
    open_price = rescaled(quote.open_price) or close_price
    high_price = rescaled(quote.high_price) or max(open_price, close_price)
    low_price = rescaled(quote.low_price) or min(open_price, close_price)

    return IntradayCandle(
        trade_date=quote_date,
        open=open_price,
        # Giá khớp hiện tại có thể đã vượt cao/thấp nhất provider ghi nhận
        # (dữ liệu 2 trường không nhất thiết cùng thời điểm) — mở rộng để
        # nến không bao giờ có thân nằm ngoài bóng.
        high=max(high_price, open_price, close_price),
        low=min(low_price, open_price, close_price),
        close=close_price,
        volume=int(quote.accumulated_volume or quote.match_volume or 0),
    )


def get_current_price(db: Session, stock_id: int) -> CurrentPrice | None:
    """Giá hiện tại của 1 mã, hoặc None nếu mã chưa có dữ liệu giá nào."""
    close = _latest_close(db, stock_id)

    quote = db.execute(
        select(RealtimeQuote.match_price, RealtimeQuote.captured_at)
        .where(RealtimeQuote.stock_id == stock_id, RealtimeQuote.match_price.is_not(None))
        .order_by(RealtimeQuote.captured_at.desc())
        .limit(1)
    ).first()

    if quote is not None and quote.captured_at.astimezone(VN_TZ).date() == datetime.now(VN_TZ).date():
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
