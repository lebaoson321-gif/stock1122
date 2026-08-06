import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

# Cho phép `from app... import ...` khi chạy alembic từ apps/api/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.db import Base  # noqa: E402
from app import models  # noqa: E402,F401  import để đăng ký hết model vào Base.metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Alembic PHẢI dùng DIRECT_URL (direct/session-pooler, port 5432), KHÔNG
# dùng DATABASE_URL (pooled qua Supavisor, port 6543) — DDL cần một
# connection ổn định, không qua transaction-mode pooling. Xem README
# phần Supabase để biết vì sao port 5432 "direct" mặc định chỉ IPv6 và
# khi nào cần trỏ DIRECT_URL vào Session Pooler thay vì host direct.
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.direct_url)

# Các schema Supabase tự quản lý (GoTrue/Auth, Storage, Realtime,
# extensions, PostgREST/graphql...) — KHÔNG để autogenerate động vào,
# nếu không `alembic revision --autogenerate` sẽ đề xuất DROP TABLE cho
# những bảng nó không nhận ra là của Supabase, cực kỳ nguy hiểm nếu ai
# đó chạy migration đó mà không đọc kỹ.
_SUPABASE_MANAGED_SCHEMAS = {
    "auth",
    "storage",
    "realtime",
    "extensions",
    "graphql",
    "graphql_public",
    "supabase_functions",
    "supabase_migrations",
    "pgbouncer",
    "vault",
    "pgsodium",
    "pgsodium_masks",
    "pg_catalog",
    "information_schema",
}


def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table" and getattr(object, "schema", None) in _SUPABASE_MANAGED_SCHEMAS:
        return False
    return True


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
