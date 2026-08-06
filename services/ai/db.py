"""
Kết nối Postgres riêng cho services/ai — đọc trực tiếp bảng
price_history/technical_indicators/stocks, KHÔNG dùng chung ORM model
với apps/api (services/ai là service độc lập, chỉ cần đọc dữ liệu bằng
SQL thuần qua pandas, không cần SQLAlchemy ORM đầy đủ).
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        database_url = os.environ["DATABASE_URL"]
        _engine = create_engine(database_url, pool_pre_ping=True)
    return _engine
