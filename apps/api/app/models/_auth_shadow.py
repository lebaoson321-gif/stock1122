"""
"Shadow" table cho auth.users — bảng này do Supabase Auth (GoTrue) tự
quản lý, KHÔNG phải của app. Định nghĩa tối thiểu này chỉ để SQLAlchemy
resolve được ForeignKey('auth.users.id') từ watchlists.user_id; Alembic
autogenerate đã được cấu hình loại schema `auth` ra khỏi diff (xem
alembic/env.py::include_object), nên bảng này sẽ không bao giờ bị tạo/
sửa/xoá bởi migration của app.
"""
from sqlalchemy import Column, Table
from sqlalchemy.dialects.postgresql import UUID

from app.db import Base

auth_users = Table(
    "users",
    Base.metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    schema="auth",
)
