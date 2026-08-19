"""market indices is_intraday

Revision ID: d3f8a1c9b426
Revises: a999c3f519c7
Create Date: 2026-08-19 17:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3f8a1c9b426'
down_revision: Union[str, None] = 'a999c3f519c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'market_indices',
        sa.Column('is_intraday', sa.Boolean(), nullable=True, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column('market_indices', 'is_intraday')
