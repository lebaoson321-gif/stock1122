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

psycopg (v3) CŨNG tự động prepare statement phía server sau vài lần
chạy cùng câu lệnh trên 1 connection (mặc định prepare_threshold=5) —
gặp lỗi "DuplicatePreparedStatement" y hệt asyncpg khi qua PgBouncer
transaction-mode, vì connection vật lý phía server có thể đổi giữa các
transaction (mỗi commit = hết transaction = trả conn về pool), nên tên
statement tự sinh (_pg3_0, _pg3_1, ...) từ 1 client connection có thể
đụng tên đã tồn tại từ client khác trên cùng conn vật lý được tái dùng.
Tắt hẳn qua prepare_threshold=None theo khuyến nghị chính thức của
psycopg3 khi chạy sau connection pooler transaction-mode:
https://www.psycopg.org/psycopg3/docs/advanced/prepared_statements.html
"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    poolclass=NullPool,
    pool_pre_ping=True,
    connect_args={"prepare_threshold": None},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
