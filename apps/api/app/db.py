"""
SQLAlchemy engine/session cho DB runtime (connection pooled qua Supabase
Supavisor — xem config.database_url).

Dùng NullPool: Supavisor/PgBouncer ở phía Supabase đã pool connection cho
mình rồi, pool thêm một lớp nữa ở SQLAlchemy chỉ tổ tăng nguy cơ giữ
connection cũ/chiếm slot của pooler một cách vô ích.

sync SQLAlchemy + psycopg (v3), không dùng async/asyncpg — asyncpg qua
PgBouncer transaction-mode pooling gặp lỗi "prepared statement already
exists" nếu không tắt prepared-statement cache; ở quy mô dashboard +
scheduler hiện tại, threadpool của FastAPI xử lý đủ, không cần async.
"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import get_settings

settings = get_settings()

engine = create_engine(settings.database_url, poolclass=NullPool, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
