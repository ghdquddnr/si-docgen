"""job user_manual fields

Revision ID: a1b2c3d4e5f6
Revises: f6d8a0c2b413
Create Date: 2026-06-15 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: str | None = 'f6d8a0c2b413'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('with_user_manual', sa.Boolean(), server_default=sa.text('0'), nullable=False)
        )
        batch_op.add_column(sa.Column('user_manual_json', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('user_manual_model', sa.String(length=128), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.drop_column('user_manual_model')
        batch_op.drop_column('user_manual_json')
        batch_op.drop_column('with_user_manual')
