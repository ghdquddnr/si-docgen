"""job requirement fields

Revision ID: c7a1e2f4b9d0
Revises: b454f4d7e3ae
Create Date: 2026-06-14 18:10:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7a1e2f4b9d0'
down_revision: str | None = 'b454f4d7e3ae'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'with_requirements', sa.Boolean(), server_default=sa.text('0'), nullable=False
            )
        )
        batch_op.add_column(sa.Column('requirement_spec_json', sa.JSON(), nullable=True))
        batch_op.add_column(
            sa.Column('requirement_spec_model', sa.String(length=128), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.drop_column('requirement_spec_model')
        batch_op.drop_column('requirement_spec_json')
        batch_op.drop_column('with_requirements')
