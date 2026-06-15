"""job proposal fields

Revision ID: c4f1a2b3d5e6
Revises: b2c3d4e5f6a7
Create Date: 2026-06-16 04:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4f1a2b3d5e6'
down_revision: str | None = 'b2c3d4e5f6a7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('client', sa.String(length=255), server_default='', nullable=False)
        )
        batch_op.add_column(
            sa.Column('with_proposal', sa.Boolean(), server_default=sa.text('0'), nullable=False)
        )
        batch_op.add_column(sa.Column('proposal_json', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('proposal_model', sa.String(length=128), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.drop_column('proposal_model')
        batch_op.drop_column('proposal_json')
        batch_op.drop_column('with_proposal')
        batch_op.drop_column('client')
