"""clear fundamentals cache after unit fix

Revision ID: be03b3ba799e
Revises: f4bdb780ca20
Create Date: 2026-08-13 07:48:05.774210

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'be03b3ba799e'
down_revision: Union[str, None] = 'f4bdb780ca20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # `company_fundamentals` chỉ là CACHE của dữ liệu provider, xoá là an
    # toàn — endpoint tự nạp lại khi có ai xem mã đó.
    #
    # Phải xoá vì ý nghĩa của cột roe/roa đã đổi: bản trước lưu số đã nhân
    # 100 ngay trong adapter, bản này lưu số THÔ rồi mới quy đổi lúc trả
    # về (dựa vào đẳng thức ROE = P/B ÷ P/E, xem
    # services/fundamentals_math.py). Để lẫn hai quy ước trong cùng một
    # bảng sẽ khiến vài mã bị nhân 100 hai lần.
    op.execute("DELETE FROM company_fundamentals")


def downgrade() -> None:
    # Không có gì để hoàn tác: chỉ xoá cache, dữ liệu tự nạp lại.
    pass
