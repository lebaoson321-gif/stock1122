"""
Module quản lý database SQLite cho hệ thống Stock Intelligence.
Schema theo đúng thiết kế: stocks, price_history
(financial_report, prediction_result sẽ thêm ở giai đoạn sau).
"""
import sqlite3
from pathlib import Path
import pandas as pd

DB_PATH = Path(__file__).parent / "stock_data.db"


def get_connection() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS stocks (
            stock_id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT UNIQUE NOT NULL,
            company_name TEXT,
            sector TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            UNIQUE(stock_id, date),
            FOREIGN KEY(stock_id) REFERENCES stocks(stock_id)
        )
        """
    )
    conn.commit()
    conn.close()


def upsert_stock(symbol: str, company_name: str = "", sector: str = "") -> int:
    """Thêm mã CP nếu chưa có, trả về stock_id."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO stocks (symbol, company_name, sector) VALUES (?, ?, ?)",
        (symbol, company_name, sector),
    )
    conn.commit()
    cur.execute("SELECT stock_id FROM stocks WHERE symbol = ?", (symbol,))
    stock_id = cur.fetchone()[0]
    conn.close()
    return stock_id


def save_price_history(stock_id: int, df: pd.DataFrame):
    """Lưu (hoặc ghi đè) dữ liệu giá vào database."""
    conn = get_connection()
    cur = conn.cursor()
    rows = [
        (
            stock_id,
            row["date"].strftime("%Y-%m-%d"),
            float(row["open"]),
            float(row["high"]),
            float(row["low"]),
            float(row["close"]),
            int(row["volume"]),
        )
        for _, row in df.iterrows()
    ]
    cur.executemany(
        """
        INSERT OR REPLACE INTO price_history
            (stock_id, date, open, high, low, close, volume)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    conn.close()


def load_price_history(stock_id: int) -> pd.DataFrame:
    """Đọc lại toàn bộ lịch sử giá của một mã CP từ database."""
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT date, open, high, low, close, volume
        FROM price_history
        WHERE stock_id = ?
        ORDER BY date
        """,
        conn,
        params=(stock_id,),
    )
    conn.close()
    df["date"] = pd.to_datetime(df["date"])
    return df
