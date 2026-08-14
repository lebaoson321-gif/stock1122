"""clear fundamentals cache after switching source to fireant

Revision ID: 9c46159f3bc0
Revises: ed0476867449
Create Date: 2026-08-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c46159f3bc0'
down_revision: Union[str, None] = 'ed0476867449'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # `company_fundamentals` chỉ là CACHE của dữ liệu provider, xoá là an
    # toàn — endpoint tự nạp lại khi có ai xem mã đó.
    #
    # Phải xoá vì các dòng cũ lấy từ VCI (qua vnstock) có P/E và EPS sai
    # ~1,9 lần (VCI dùng cơ sở lợi nhuận chỉ bằng nửa TTM thật — không
    # phải lỗi đơn vị, không phép quy đổi nào chữa được). Nguồn mặc định
    # cho chỉ số tài chính giờ là FireAnt khi FUNDAMENTALS_PROVIDER=fireant
    # (xem collectors/fireant_adapter.py), và raw của các dòng cũ không
    # có khoá "_source" nên router sẽ hiểu nhầm là vnstock và áp sai công
    # thức suy đơn vị ROE/ROA.
    op.execute("DELETE FROM company_fundamentals")


def downgrade() -> None:
    # Không có gì để hoàn tác: chỉ xoá cache, dữ liệu tự nạp lại.
    pass
