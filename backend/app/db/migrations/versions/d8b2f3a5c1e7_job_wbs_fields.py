"""job wbs fields

Revision ID: d8b2f3a5c1e7
Revises: c7a1e2f4b9d0
Create Date: 2026-06-14 22:40:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8b2f3a5c1e7'
down_revision: str | None = 'c7a1e2f4b9d0'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('with_wbs', sa.Boolean(), server_default=sa.text('0'), nullable=False)
        )
        batch_op.add_column(sa.Column('wbs_json', sa.JSON(), nullable=True))
        batch_op.add_column(
            sa.Column('start_date', sa.String(length=10), server_default='', nullable=False)
        )
        batch_op.add_column(sa.Column('wbs_model', sa.String(length=128), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.drop_column('wbs_model')
        batch_op.drop_column('start_date')
        batch_op.drop_column('wbs_json')
        batch_op.drop_column('with_wbs')
