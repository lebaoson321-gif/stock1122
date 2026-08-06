"""
Endpoint nội bộ để gắn uptime monitor bên ngoài, phát hiện scheduler
"chết âm thầm" (worker service không còn chạy job, hoặc job lỗi liên
tục mà không ai để ý). Không có dữ liệu người dùng — không cần auth,
nhưng cân nhắc giới hạn IP/network khi deploy nếu muốn kín đáo hơn.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.sync_log import DataSyncLog

router = APIRouter(prefix="/internal", tags=["internal"])


@router.get("/scheduler/status")
def scheduler_status(db: Session = Depends(get_db)):
    result = {}
    for sync_type in ("historical", "realtime"):
        row = db.execute(
            select(DataSyncLog.finished_at, DataSyncLog.status, DataSyncLog.rows_synced)
            .where(DataSyncLog.sync_type == sync_type, DataSyncLog.status == "success")
            .order_by(DataSyncLog.finished_at.desc())
            .limit(1)
        ).first()
        result[f"last_successful_{sync_type}"] = (
            {"finished_at": row.finished_at, "rows_synced": row.rows_synced} if row else None
        )

    # apscheduler_jobs.next_run_time là unix timestamp (float), đọc trực
    # tiếp không cần unpickle job — bảng này do SQLAlchemyJobStore tự tạo,
    # không phải do Alembic quản lý.
    try:
        job_rows = db.execute(text("SELECT id, next_run_time FROM apscheduler_jobs")).all()
        result["scheduled_jobs"] = [
            {
                "id": r.id,
                "next_run_time": (
                    datetime.fromtimestamp(r.next_run_time, tz=timezone.utc) if r.next_run_time else None
                ),
            }
            for r in job_rows
        ]
    except Exception:
        # Bảng chưa tồn tại nếu scheduler chưa từng chạy ở instance nào
        # (vd. đang xem status từ service `api` không chạy scheduler).
        result["scheduled_jobs"] = []

    return result
