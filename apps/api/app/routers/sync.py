from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.collectors.base import MarketDataProvider
from app.collectors.factory import get_market_data_provider
from app.collectors.historical import list_active_symbols, sync_stock_history
from app.collectors.realtime import poll_and_store_price_board
from app.db import get_db
from app.models.sync_log import DataSyncLog
from app.schemas.stock import PollResult, SyncResult

router = APIRouter(prefix="/api/stocks", tags=["sync"])

# Watchlist mặc định để bootstrap danh sách mã — các mã vốn hoá lớn quen
# thuộc trên HOSE (đa số nằm trong VN30), dùng cho nút "Đồng bộ nhanh"
# ở trang danh sách mã, để người dùng không phải tự gõ tìm từng mã một.
DEFAULT_WATCHLIST = ["FPT", "VNM", "HPG", "VCB", "VIC", "VHM", "MSN", "MWG", "TCB", "GAS"]


def _sync_one(db: Session, provider: MarketDataProvider, symbol: str, years: int) -> SyncResult:
    symbol = symbol.upper()
    started_at = datetime.now(timezone.utc)

    try:
        rows = sync_stock_history(db, provider, symbol, years=years)
    except Exception as e:
        db.rollback()
        db.add(
            DataSyncLog(
                stock_id=None, sync_type="historical", status="provider_error",
                rows_synced=0, error_message=f"{symbol}: {e}",
                started_at=started_at, finished_at=datetime.now(timezone.utc),
            )
        )
        db.commit()
        return SyncResult(symbol=symbol, rows_synced=0, message=f"Lỗi khi lấy dữ liệu: {e}")

    status_str = "success" if rows else "no_data"
    db.add(
        DataSyncLog(
            stock_id=None, sync_type="historical", status=status_str, rows_synced=rows,
            error_message=None, started_at=started_at, finished_at=datetime.now(timezone.utc),
        )
    )
    db.commit()

    if rows == 0:
        return SyncResult(symbol=symbol, rows_synced=0, message=f"Không tìm thấy dữ liệu cho mã {symbol}")
    return SyncResult(symbol=symbol, rows_synced=rows, message="Đồng bộ thành công")


@router.post("/{symbol}/sync", response_model=SyncResult)
def sync_stock(symbol: str, years: int = Query(5, ge=1, le=20), db: Session = Depends(get_db)):
    """
    Lấy dữ liệu mới nhất từ HOSE (qua vnstock) và lưu/ghi đè vào database,
    rồi tính lại chỉ báo kỹ thuật + điểm chấm. Gọi endpoint này trước khi
    xem history/analysis lần đầu cho một mã mới.
    """
    provider = get_market_data_provider()
    result = _sync_one(db, provider, symbol, years)
    if result.rows_synced == 0:
        code = status.HTTP_502_BAD_GATEWAY if "Lỗi" in result.message else status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=code, detail=result.message)
    return result


@router.post("/sync-defaults", response_model=list[SyncResult])
def sync_default_watchlist(years: int = Query(5, ge=1, le=20), db: Session = Depends(get_db)):
    """
    Đồng bộ một watchlist mặc định (các mã vốn hoá lớn quen thuộc trên
    HOSE) trong một lần gọi — dùng để bootstrap danh sách mã cho người
    dùng mới, không cần tự gõ tìm từng mã. Lỗi ở 1 mã không chặn các mã
    còn lại (mỗi mã xử lý độc lập, lỗi vẫn trả về trong kết quả thay vì
    raise exception).
    """
    provider = get_market_data_provider()
    return [_sync_one(db, provider, symbol, years) for symbol in DEFAULT_WATCHLIST]


@router.post("/poll-realtime", response_model=PollResult)
def poll_realtime(
    batch_size: int = Query(50, ge=1, le=200, description="Số mã mỗi lần gọi bảng giá"),
    db: Session = Depends(get_db),
):
    """
    Poll giá khớp trong phiên cho mọi mã đã có trong DB, ghi vào
    `realtime_quotes`. Đây là nguồn giá cho khớp lệnh mua/bán ảo trong
    phiên (xem services/pricing.py) — ngoài giờ hoặc khi dữ liệu quá cũ
    thì hệ thống tự lùi về giá đóng cửa.

    Gọi bằng job bên ngoài (GitHub Actions, xem
    .github/workflows/intraday-poll.yml) vì scheduler nội bộ không chạy
    được trên Render gói miễn phí.

    Chia lô: bảng giá nhận nhiều mã một lần, nhưng gửi cả vài trăm mã
    trong một request dễ bị provider từ chối — lô lỗi không làm hỏng lô
    khác.
    """
    provider = get_market_data_provider()
    symbols = list_active_symbols(db)
    started_at = datetime.now(timezone.utc)

    total_rows = 0
    failed_batches = 0
    errors: list[str] = []
    for start in range(0, len(symbols), batch_size):
        batch = symbols[start : start + batch_size]
        try:
            total_rows += poll_and_store_price_board(db, provider, batch)
        except Exception as e:  # noqa: BLE001 — 1 lô lỗi không dừng các lô còn lại
            db.rollback()
            failed_batches += 1
            if len(errors) < 3:  # giữ thông báo ngắn, đủ để chẩn đoán
                errors.append(f"{batch[0]}..{batch[-1]}: {e}")

    db.add(
        DataSyncLog(
            stock_id=None,
            sync_type="realtime",
            status="success" if total_rows else ("provider_error" if failed_batches else "no_data"),
            rows_synced=total_rows,
            error_message="; ".join(errors) or None,
            started_at=started_at,
            finished_at=datetime.now(timezone.utc),
        )
    )
    db.commit()

    return PollResult(
        symbols_requested=len(symbols),
        rows_synced=total_rows,
        failed_batches=failed_batches,
        message="Không có mã nào trong DB — đồng bộ giá lịch sử trước."
        if not symbols
        else f"Đã ghi {total_rows} bản ghi giá khớp.",
    )
