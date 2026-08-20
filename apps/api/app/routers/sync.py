import zlib
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.collectors.base import MarketDataProvider
from app.collectors.factory import get_market_data_provider
from app.collectors.historical import list_active_symbols_by_exchange, sync_stock_history
from app.collectors.realtime import poll_and_store_price_board
from app.db import SessionLocal, get_db
from app.models.sync_log import DataSyncLog
from app.schemas.stock import PollResult, SyncResult
from app.services.market_session import get_market_status

router = APIRouter(prefix="/api/stocks", tags=["sync"])

# Watchlist mặc định để bootstrap danh sách mã — các mã vốn hoá lớn quen
# thuộc trên HOSE (đa số nằm trong VN30), dùng cho nút "Đồng bộ nhanh"
# ở trang danh sách mã, để người dùng không phải tự gõ tìm từng mã một.
DEFAULT_WATCHLIST = ["FPT", "VNM", "HPG", "VCB", "VIC", "VHM", "MSN", "MWG", "TCB", "GAS"]


def _sync_one(
    db: Session, provider: MarketDataProvider, symbol: str, years: int, refresh_info: bool = False
) -> SyncResult:
    symbol = symbol.upper()
    started_at = datetime.now(timezone.utc)

    try:
        rows = sync_stock_history(db, provider, symbol, years=years, refresh_info=refresh_info)
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
def sync_stock(
    symbol: str,
    years: int = Query(5, ge=1, le=20),
    refresh_info: bool = Query(
        False, description="Ép gọi lại provider để làm mới tên công ty/ngành/sàn niêm yết"
    ),
    db: Session = Depends(get_db),
):
    """
    Lấy dữ liệu mới nhất từ HOSE (qua vnstock) và lưu/ghi đè vào database,
    rồi tính lại chỉ báo kỹ thuật + điểm chấm. Gọi endpoint này trước khi
    xem history/analysis lần đầu cho một mã mới.

    Tên công ty/ngành/sàn niêm yết chỉ được lấy lại từ provider khi mã
    mới, lần trước lấy hụt, hoặc refresh_info=true — bình thường dùng
    thẳng bản ghi đã có trong `stocks` để đỡ 1 lượt gọi mạng mỗi lần sync.
    """
    provider = get_market_data_provider()
    result = _sync_one(db, provider, symbol, years, refresh_info=refresh_info)
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


def _advisory_lock_key(name: str) -> int:
    # Cùng công thức với scheduler.py — CÙNG key "poll_realtime" để 2
    # đường gọi (HTTP ở đây và job nội bộ APScheduler khi RUN_SCHEDULER=
    # true) loại trừ lẫn nhau nếu lỡ cả hai cùng bật, thay vì ghi trùng.
    return zlib.crc32(name.encode())


def _poll_realtime_core(
    db: Session,
    provider: MarketDataProvider,
    by_exchange: dict[str, list[str]],
    batch_size: int,
    force: bool,
) -> tuple[int, int, int, list[str], list[str]]:
    """Vòng lặp poll thật: gom mã theo sàn, xét trạng thái phiên RIÊNG
    cho từng sàn (lý do xem docstring cũ của poll_realtime bên dưới),
    gọi provider theo lô. Tách khỏi _poll_realtime_background để test
    được bằng SQLite/provider giả — không đụng SessionLocal thật hay
    pg_try_advisory_xact_lock (hàm Postgres-only, không chạy trên SQLite).

    Trả về (total_rows, failed_batches, symbols_requested, skipped, errors)
    thay vì tự ghi DataSyncLog — việc ghi log gộp 1 dòng duy nhất cho cả
    lượt poll là việc của caller (_poll_realtime_background), để đảm bảo
    log được ghi dù hàm này ném lỗi ngoài dự kiến (bọc try/finally ở đó).
    """
    total_rows = 0
    failed_batches = 0
    symbols_requested = 0
    skipped: list[str] = []
    errors: list[str] = []

    for exchange, symbols in by_exchange.items():
        # Ngoài giờ khớp lệnh CỦA SÀN ĐÓ, bảng giá không đổi — gọi
        # provider chỉ tốn công và làm tăng nguy cơ bị VCI chặn IP (đã
        # gặp khi đồng bộ hàng loạt).
        session = get_market_status(exchange=exchange)  # không đặt tên `status`: trùng với fastapi.status dùng ở trên
        if not force and not session.is_open:
            skipped.append(f"{exchange} ({session.label})")
            continue

        symbols_requested += len(symbols)
        for start in range(0, len(symbols), batch_size):
            batch = symbols[start : start + batch_size]
            try:
                total_rows += poll_and_store_price_board(db, provider, batch)
            except Exception as e:  # noqa: BLE001 — 1 lô lỗi không dừng các lô còn lại
                db.rollback()
                failed_batches += 1
                if len(errors) < 3:  # giữ thông báo ngắn, đủ để chẩn đoán
                    errors.append(f"{batch[0]}..{batch[-1]}: {e}")

    return total_rows, failed_batches, symbols_requested, skipped, errors


def _poll_realtime_background(batch_size: int, force: bool) -> None:
    """Chạy SAU khi response 202 đã gửi (BackgroundTasks) — KHÔNG được
    nhận `db` từ Depends(get_db): dependency đó đóng session ngay sau khi
    response được gửi đi, còn BackgroundTasks chạy sau đó nữa — dùng lại
    session đã đóng gây lỗi rất khó hiểu (lúc được lúc không, tuỳ thời
    điểm connection thật sự bị dọn). Phải tự mở bằng SessionLocal() và tự
    đóng trong finally, y hệt cách scheduler.py làm cho job nội bộ.

    Trả 202 nghĩa là cron-job.org/GH Actions LUÔN thấy thành công, kể cả
    khi poll hỏng thật — bù lại bằng cách ghi đúng 1 dòng data_sync_log
    trong MỌI trường hợp (kể cả exception ngoài dự kiến, vd. lỗi mở
    session hoặc lỗi advisory lock), để data_sync_log/GET /api/market/status
    (last_quote_at) là nơi DUY NHẤT xác nhận poll có chạy hay không.
    """
    started_at = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        # CẠM BẪY (biết nhưng chấp nhận, xem poll_and_store_price_board()
        # trong collectors/realtime.py để biết chi tiết + bằng chứng):
        # khoá này theo TRANSACTION, nhưng _poll_realtime_core() gọi
        # poll_and_store_price_board() nhiều lần (mỗi lô 50 mã), mà hàm
        # đó commit() sau MỖI lần gọi — nên khoá chỉ thật sự giữ được
        # cho LÔ ĐẦU TIÊN, các lô sau chạy không có bảo vệ. Bằng chứng
        # thật (2026-08-20): data_sync_log id 4452 chạy 08:01:11, NẰM
        # TRONG cửa sổ chạy 08:00:49-08:01:21 của id 4453, mà KHÔNG bị
        # skipped_locked như lẽ ra phải vậy nếu khoá còn hiệu lực. Chấp
        # nhận được hiện tại vì chỉ còn 1 bộ lập lịch (cron-job.org) gọi
        # endpoint này — 2 lượt cách nhau 10 phút không tự chồng ở
        # ~32s/lượt. Nếu có bộ lập lịch thứ 2 cùng gọi, PHẢI tắt bớt 1
        # bộ (xem intraday-poll.yml) — khoá không đủ để chặn va chạm.
        locked = db.execute(
            text("SELECT pg_try_advisory_xact_lock(:key)"),
            {"key": _advisory_lock_key("poll_realtime")},
        ).scalar()
        if not locked:
            db.add(
                DataSyncLog(
                    stock_id=None, sync_type="realtime", status="skipped_locked",
                    rows_synced=0, error_message="Một lượt poll khác đang chạy",
                    started_at=started_at, finished_at=datetime.now(timezone.utc),
                )
            )
            db.commit()
            return

        provider = get_market_data_provider()
        by_exchange = list_active_symbols_by_exchange(db)
        total_rows, failed_batches, _symbols_requested, _skipped, errors = _poll_realtime_core(
            db, provider, by_exchange, batch_size, force
        )
        db.add(
            DataSyncLog(
                stock_id=None, sync_type="realtime",
                status="success" if total_rows else ("provider_error" if failed_batches else "no_data"),
                rows_synced=total_rows, error_message="; ".join(errors) or None,
                started_at=started_at, finished_at=datetime.now(timezone.utc),
            )
        )
        db.commit()
    except Exception as e:  # noqa: BLE001 — phải ghi log dù lỗi ở đâu (mở session, lock, provider...)
        db.rollback()
        db.add(
            DataSyncLog(
                stock_id=None, sync_type="realtime", status="provider_error",
                rows_synced=0, error_message=f"Lỗi ngoài dự kiến: {e}",
                started_at=started_at, finished_at=datetime.now(timezone.utc),
            )
        )
        db.commit()
    finally:
        db.close()


@router.post("/poll-realtime", response_model=PollResult, status_code=status.HTTP_200_OK)
def poll_realtime(
    background_tasks: BackgroundTasks,
    response: Response,
    batch_size: int = Query(50, ge=1, le=200, description="Số mã mỗi lần gọi bảng giá"),
    force: bool = Query(False, description="Poll cả khi thị trường đang đóng"),
    db: Session = Depends(get_db),
):
    """
    Kích hoạt poll giá khớp trong phiên cho mọi mã đã có trong DB, ghi
    vào `realtime_quotes`. Đây là nguồn giá cho khớp lệnh mua/bán ảo
    trong phiên (xem services/pricing.py) — ngoài giờ hoặc khi dữ liệu
    quá cũ thì hệ thống tự lùi về giá đóng cửa.

    Trả về NGAY, không đợi poll xong: gọi provider cho vài trăm mã đo
    thực tế mất 30s+ — vượt trần timeout 30s của các dịch vụ cron miễn
    phí (cron-job.org...). Nếu để đồng bộ, dịch vụ cron ghi nhận timeout
    là "fail" dù backend vẫn chạy xong phía sau, và tự TẮT job sau đủ số
    lần fail liên tiếp (cron-job.org: >25 lần) — một kiểu hỏng âm thầm.
      - Ngoài giờ khớp lệnh của MỌI sàn (và không force): trả 200 ngay,
        đồng bộ, không tốn quota provider, không có việc chạy nền.
      - Trong giờ khớp lệnh của ÍT NHẤT 1 sàn (hoặc force=true): việc
        poll thật chạy nền (BackgroundTasks, xem _poll_realtime_background)
        SAU khi response đã gửi — trả 202. response 202 CHỈ xác nhận đã
        nhận yêu cầu, KHÔNG đảm bảo poll thành công; xem kết quả thật qua
        data_sync_log hoặc GET /api/market/status (last_quote_at).

    Gom mã theo `stocks.exchange` (list_active_symbols_by_exchange) và
    xét trạng thái phiên RIÊNG cho từng sàn: HOSE và HNX đóng khớp liên
    tục lúc 14:45 như nhau (cùng có ATC rồi "post" thoả thuận tới 15:00
    — xem market_session.py), CHỈ UPCOM khớp liên tục thẳng tới 15:00.
    Một cổng chung sẽ sai theo 1 trong 2 hướng — chặn quá sớm bỏ sót 15
    phút cuối của UPCOM, hoặc nới quá muộn khiến HOSE/HNX bị poll thêm
    sau khi đã đóng. Cùng lý do với INDEX_EXCHANGE ở routers/market.py,
    áp cho cổ phiếu.

    Gọi bằng job bên ngoài (cron-job.org hoặc GitHub Actions, xem
    .github/workflows/intraday-poll.yml) vì scheduler nội bộ không chạy
    được trên Render gói miễn phí.

    Chia lô: bảng giá nhận nhiều mã một lần, nhưng gửi cả vài trăm mã
    trong một request dễ bị provider từ chối — lô lỗi không làm hỏng lô
    khác.
    """
    by_exchange = list_active_symbols_by_exchange(db)
    if not by_exchange:
        return PollResult(
            symbols_requested=0, rows_synced=0, failed_batches=0,
            message="Không có mã nào trong DB — đồng bộ giá lịch sử trước.",
        )

    statuses = {exchange: get_market_status(exchange=exchange) for exchange in by_exchange}
    if not force and not any(s.is_open for s in statuses.values()):
        skipped = [f"{exchange} ({s.label})" for exchange, s in statuses.items()]
        return PollResult(
            symbols_requested=0, rows_synced=0, failed_batches=0,
            message=f"Bỏ qua: {', '.join(skipped)}. Dùng ?force=true nếu vẫn muốn poll.",
        )

    background_tasks.add_task(_poll_realtime_background, batch_size, force)
    response.status_code = status.HTTP_202_ACCEPTED
    return PollResult(
        symbols_requested=0,
        rows_synced=0,
        failed_batches=0,
        message="Đã nhận yêu cầu, poll đang chạy trong nền — xem data_sync_log hoặc GET /api/market/status (last_quote_at) để biết kết quả.",
    )
