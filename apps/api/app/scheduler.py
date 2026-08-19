"""
Scheduler chạy trong tiến trình FastAPI, CHỈ khởi động khi
`RUN_SCHEDULER=true` (xem app/main.py lifespan). Đây là lựa chọn có chủ
đích thay vì Celery+Redis ở giai đoạn này — xem README phần "Deploy" để
biết cách deploy an toàn (tách service `api` không chạy scheduler, có
thể scale nhiều instance, và service `worker` duy nhất chạy scheduler).

An toàn multi-instance dù đã tách service:
- SQLAlchemyJobStore: job state (lần chạy kế tiếp...) sống sót qua restart.
- coalesce=True, max_instances=1, misfire_grace_time: một job chạy trễ/chậm
  không bị dồn thành nhiều lần chạy chồng nhau.
- pg_try_advisory_xact_lock: phòng hờ nếu lỡ có 2 instance worker cùng
  chạy (vd. deploy config sai) — instance thứ 2 tự bỏ qua thay vì ghi
  trùng, không dựa hoàn toàn vào "chỉ deploy đúng 1 instance".
- Mọi lần chạy job (kể cả bị skip do lock, kể cả lỗi) đều ghi 1 dòng
  data_sync_log — đây là tín hiệu duy nhất để biết scheduler có "chết
  âm thầm" hay không. Xem GET /internal/scheduler/status.
"""
import zlib
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import text

from app.collectors.factory import get_market_data_provider
from app.collectors.historical import list_active_symbols, list_active_symbols_by_exchange, sync_stock_history
from app.collectors.realtime import poll_and_store_price_board
from app.config import get_settings
from app.db import SessionLocal, engine
from app.models.sync_log import DataSyncLog
from app.services.market_session import get_market_status

settings = get_settings()

_scheduler: BackgroundScheduler | None = None


def _advisory_lock_key(name: str) -> int:
    # pg_try_advisory_xact_lock nhận bigint; CRC32 cho ra uint32 ổn định,
    # đủ để tránh đụng độ giữa vài job cố định (sync/poll) của app này.
    return zlib.crc32(name.encode())


def _log_sync(
    db, *, stock_id: int | None, sync_type: str, status: str,
    rows_synced: int, error_message: str | None, started_at: datetime,
):
    db.add(
        DataSyncLog(
            stock_id=stock_id, sync_type=sync_type, status=status,
            rows_synced=rows_synced, error_message=error_message,
            started_at=started_at, finished_at=datetime.now(timezone.utc),
        )
    )
    db.commit()


def sync_all_active_stocks() -> None:
    """Job hằng ngày: đồng bộ lịch sử giá cho tất cả mã đang active."""
    started_at = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        locked = db.execute(
            text("SELECT pg_try_advisory_xact_lock(:key)"),
            {"key": _advisory_lock_key("sync_all_active_stocks")},
        ).scalar()
        if not locked:
            _log_sync(
                db, stock_id=None, sync_type="historical", status="skipped_locked",
                rows_synced=0, error_message="Một instance khác đang chạy job này",
                started_at=started_at,
            )
            return

        provider = get_market_data_provider()
        symbols = list_active_symbols(db)
        for symbol in symbols:
            sym_started = datetime.now(timezone.utc)
            try:
                rows = sync_stock_history(db, provider, symbol)
                _log_sync(
                    db, stock_id=None, sync_type="historical",
                    status="success" if rows else "no_data",
                    rows_synced=rows, error_message=None, started_at=sym_started,
                )
            except Exception as e:
                db.rollback()
                _log_sync(
                    db, stock_id=None, sync_type="historical", status="provider_error",
                    rows_synced=0, error_message=f"{symbol}: {e}", started_at=sym_started,
                )
    finally:
        db.close()


_VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def _is_vn_trading_hours(now: datetime) -> bool:
    # Giờ giao dịch HOSE: 09:00–15:00, Thứ 2–Thứ 6, giờ Việt Nam (UTC+7,
    # không có DST). Dùng zoneinfo thay vì cộng tay để tránh sai lệch
    # ngày khi giờ UTC gần ranh giới nửa đêm.
    vn_now = now.astimezone(_VN_TZ)
    is_weekday = vn_now.weekday() < 5  # 0=Mon .. 4=Fri
    return is_weekday and 9 <= vn_now.hour < 15


def poll_realtime() -> None:
    """Job định kỳ: poll giá khớp lệnh cho tất cả mã active, chỉ trong
    giờ giao dịch — ngoài giờ gọi cũng không có dữ liệu mới, chỉ tốn quota.

    _is_vn_trading_hours() ở trên chỉ là cổng THÔ 9:00-15:00 (đủ rộng để
    phủ cả 3 sàn, tránh mở DB session/lock ngoài giờ đó hoàn toàn). Cổng
    THẬT xét RIÊNG từng sàn bằng get_market_status(exchange=...) bên
    trong — HOSE và HNX đóng khớp liên tục lúc 14:45 như nhau, CHỈ UPCOM
    khớp liên tục tới 15:00; một cổng chung sẽ poll nhầm HOSE/HNX sau
    14:45 hoặc bỏ sót UPCOM tới 15:00. Cùng lý do với INDEX_EXCHANGE ở
    routers/market.py."""
    started_at = datetime.now(timezone.utc)
    if not _is_vn_trading_hours(started_at):
        return

    db = SessionLocal()
    try:
        locked = db.execute(
            text("SELECT pg_try_advisory_xact_lock(:key)"),
            {"key": _advisory_lock_key("poll_realtime")},
        ).scalar()
        if not locked:
            _log_sync(
                db, stock_id=None, sync_type="realtime", status="skipped_locked",
                rows_synced=0, error_message="Một instance khác đang chạy job này",
                started_at=started_at,
            )
            return

        provider = get_market_data_provider()
        by_exchange = list_active_symbols_by_exchange(db)
        total_rows = 0
        errors: list[str] = []
        for exchange, symbols in by_exchange.items():
            if not get_market_status(started_at, exchange=exchange).is_open:
                continue
            try:
                total_rows += poll_and_store_price_board(db, provider, symbols)
            except Exception as e:  # noqa: BLE001 — 1 sàn lỗi không chặn sàn còn lại
                db.rollback()
                errors.append(f"{exchange}: {e}")

        _log_sync(
            db, stock_id=None, sync_type="realtime",
            status="success" if total_rows else ("provider_error" if errors else "no_data"),
            rows_synced=total_rows, error_message="; ".join(errors) or None, started_at=started_at,
        )
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    jobstores = {"default": SQLAlchemyJobStore(engine=engine)}
    executors = {"default": ThreadPoolExecutor(max_workers=2)}
    job_defaults = {"coalesce": True, "max_instances": 1, "misfire_grace_time": 300}

    scheduler = BackgroundScheduler(jobstores=jobstores, executors=executors, job_defaults=job_defaults)
    scheduler.add_job(
        sync_all_active_stocks,
        CronTrigger.from_crontab(settings.historical_sync_cron, timezone=_VN_TZ),
        id="sync_all_active_stocks", replace_existing=True,
    )
    scheduler.add_job(
        poll_realtime, IntervalTrigger(seconds=settings.realtime_poll_interval_seconds),
        id="poll_realtime", replace_existing=True,
    )
    scheduler.start()
    _scheduler = scheduler
    return scheduler


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
