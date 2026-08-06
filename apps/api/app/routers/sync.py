from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.collectors.base import MarketDataProvider
from app.collectors.factory import get_market_data_provider
from app.collectors.historical import sync_stock_history
from app.db import get_db
from app.models.sync_log import DataSyncLog
from app.schemas.stock import SyncResult

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
