"""
Realtime Stock Poller
Poll bảng giá khớp lệnh (price board) theo chu kỳ cho tất cả mã cổ phiếu
đã có trong CSDL của backend (bảng `stocks`), rồi in ra console.

Không ghi vào DB, không gọi API backend — chỉ để xem giá realtime chạy
qua terminal. Backend cần đã `POST /api/stocks/{symbol}/sync` cho ít
nhất một mã trước, để bảng `stocks` có dữ liệu cho poller đọc.

Chạy: python poller.py
Dừng: Ctrl+C
"""
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

from vnstock.api.trading import Trading

DB_PATH = Path(__file__).resolve().parent.parent / "backend" / "app" / "stock_data.db"
POLL_INTERVAL_SECONDS = 60


def load_symbols() -> list:
    """Đọc danh sách mã cổ phiếu hiện có từ DB của backend (đọc-only)."""
    if not DB_PATH.exists():
        return []
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute("SELECT symbol FROM stocks ORDER BY symbol")
        return [row[0] for row in cur.fetchall()]
    finally:
        conn.close()


def _first_present(row: dict, candidates: list):
    """Trả về giá trị đầu tiên có mặt trong `row` theo danh sách tên cột
    ưu tiên. vnstock đôi khi đổi tên cột giữa các phiên bản nên tra theo
    nhiều khả năng thay vì cố định một tên duy nhất."""
    for key in candidates:
        if key in row and row[key] is not None:
            return row[key]
    return None


def format_quote(row: dict) -> str:
    symbol = _first_present(row, ["listing_symbol", "symbol"]) or "?"
    price = _first_present(row, ["match_match_price", "match_price", "match_avg_price"])
    volume = _first_present(row, ["match_match_vol", "match_vol", "match_total_volume"])
    ref = _first_present(row, ["listing_ref_price", "ref_price"])

    parts = [f"{symbol:<6}"]
    parts.append(f"giá khớp={price}" if price is not None else "giá khớp=?")
    if volume is not None:
        parts.append(f"KL khớp={volume}")
    if ref is not None:
        parts.append(f"TC={ref}")
    return "  ".join(parts)


def poll_once(trading: Trading, symbols: list):
    board = trading.price_board(symbols_list=symbols, flatten_columns=True)
    if board is None or board.empty:
        print("  (không nhận được dữ liệu bảng giá)")
        return
    for _, row in board.iterrows():
        print("  " + format_quote(row.to_dict()))


def main():
    print(f"Realtime poller — poll mỗi {POLL_INTERVAL_SECONDS}s, Ctrl+C để dừng.")
    print(f"Đọc danh sách mã từ: {DB_PATH}")

    trading = Trading(source="vci", show_log=False)

    try:
        while True:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            symbols = load_symbols()
            if not symbols:
                print(
                    f"[{timestamp}] Chưa có mã nào trong DB. Gọi "
                    f"POST /api/stocks/{{symbol}}/sync trên backend trước. "
                    f"Thử lại sau {POLL_INTERVAL_SECONDS}s..."
                )
            else:
                print(f"[{timestamp}] Poll {len(symbols)} mã: {', '.join(symbols)}")
                try:
                    poll_once(trading, symbols)
                except Exception as e:
                    print(f"  Lỗi khi lấy bảng giá: {e}")

            time.sleep(POLL_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\nĐã dừng poller.")
        sys.exit(0)


if __name__ == "__main__":
    main()
