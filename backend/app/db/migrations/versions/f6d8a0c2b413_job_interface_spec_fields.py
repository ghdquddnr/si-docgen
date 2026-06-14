"""job interface_spec fields

Revision ID: f6d8a0c2b413
Revises: e3c4a6b8f201
Create Date: 2026-06-14 02:55:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6d8a0c2b413'
down_revision: str | None = 'e3c4a6b8f201'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'with_interface_spec', sa.Boolean(), server_default=sa.text('0'), nullable=False
            )
        )
        batch_op.add_column(sa.Column('interface_spec_json', sa.JSON(), nullable=True))
        batch_op.add_column(
            sa.Column('interface_spec_model', sa.String(length=128), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.drop_column('interface_spec_model')
        batch_op.drop_column('interface_spec_json')
        batch_op.drop_column('with_interface_spec')
