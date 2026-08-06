from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.collectors.factory import get_market_data_provider
from app.collectors.historical import sync_stock_history
from app.db import get_db
from app.models.sync_log import DataSyncLog
from app.schemas.stock import SyncResult

router = APIRouter(prefix="/api/stocks", tags=["sync"])


@router.post("/{symbol}/sync", response_model=SyncResult)
def sync_stock(symbol: str, years: int = Query(5, ge=1, le=20), db: Session = Depends(get_db)):
    """
    Lấy dữ liệu mới nhất từ HOSE (qua vnstock) và lưu/ghi đè vào database,
    rồi tính lại chỉ báo kỹ thuật. Gọi endpoint này trước khi xem
    history/analysis lần đầu cho một mã mới.
    """
    symbol = symbol.upper()
    started_at = datetime.now(timezone.utc)
    provider = get_market_data_provider()

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
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Lỗi khi lấy dữ liệu: {e}")

    if rows == 0:
        db.add(
            DataSyncLog(
                stock_id=None, sync_type="historical", status="no_data", rows_synced=0,
                error_message=None, started_at=started_at, finished_at=datetime.now(timezone.utc),
            )
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Không tìm thấy dữ liệu cho mã {symbol}")

    db.add(
        DataSyncLog(
            stock_id=None, sync_type="historical", status="success", rows_synced=rows,
            error_message=None, started_at=started_at, finished_at=datetime.now(timezone.utc),
        )
    )
    db.commit()
    return SyncResult(symbol=symbol, rows_synced=rows, message="Đồng bộ thành công")
