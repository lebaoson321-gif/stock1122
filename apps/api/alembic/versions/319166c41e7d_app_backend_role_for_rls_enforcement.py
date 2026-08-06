"""app_backend role for RLS enforcement

Revision ID: 319166c41e7d
Revises: 4440556391f6
Create Date: 2026-08-06 09:10:44.747739

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '319166c41e7d'
down_revision: Union[str, None] = '4440556391f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # QUAN TRỌNG: Postgres KHÔNG áp dụng RLS cho superuser hay chủ sở hữu
    # bảng (table owner), dù policy có bật hay không. `postgres` (role
    # mặc định Supabase cấp cho connection string trực tiếp) sở hữu các
    # bảng do Alembic tạo ra -> nếu app dùng role `postgres` để kết nối,
    # RLS ở migration trước hoàn toàn vô tác dụng dù trông như đang chạy
    # đúng (đã tự phát hiện lỗi này khi test cục bộ). App PHẢI kết nối
    # bằng role riêng, không sở hữu bảng, để RLS thật sự có hiệu lực.
    #
    # KHÔNG đặt password ở đây (migration nằm trong version control).
    # Sau khi chạy migration này, đặt password thủ công:
    #   ALTER ROLE app_backend WITH PASSWORD '<mật khẩu mạnh>';
    # rồi dùng role đó trong DATABASE_URL/DIRECT_URL — xem README phần
    # Supabase.
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_backend') THEN
                CREATE ROLE app_backend LOGIN;
            END IF;
        END
        $$;
        """
    )
    op.execute("GRANT USAGE ON SCHEMA public TO app_backend")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_backend")
    op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_backend")
    # Áp dụng luôn cho bảng được tạo ở các migration sau này (nếu người
    # tạo migration đó cũng dùng chung role đã tạo bảng, thường là owner
    # hiện tại của schema — xem lưu ý trong README nếu đổi role chạy Alembic).
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_backend"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "GRANT USAGE, SELECT ON SEQUENCES TO app_backend"
    )


def downgrade() -> None:
    op.execute("REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM app_backend")
    op.execute("REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM app_backend")
    op.execute("REVOKE USAGE ON SCHEMA public FROM app_backend")
    op.execute("DROP ROLE IF EXISTS app_backend")
