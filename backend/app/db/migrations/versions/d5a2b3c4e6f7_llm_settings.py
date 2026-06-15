"""llm settings (api credentials + models)

Revision ID: d5a2b3c4e6f7
Revises: c4f1a2b3d5e6
Create Date: 2026-06-16 05:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5a2b3c4e6f7'
down_revision: str | None = 'c4f1a2b3d5e6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'api_credentials',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('provider', sa.String(length=32), nullable=False),
        sa.Column('label', sa.String(length=255), nullable=False),
        sa.Column('encrypted_key', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_api_credentials_provider', 'api_credentials', ['provider'])
    op.create_table(
        'llm_models',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('label', sa.String(length=255), nullable=False),
        sa.Column('provider', sa.String(length=32), nullable=False),
        sa.Column('model', sa.String(length=255), nullable=False),
        sa.Column('credential_id', sa.String(length=36), nullable=True),
        sa.Column('enabled', sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_llm_models_provider', 'llm_models', ['provider'])


def downgrade() -> None:
    op.drop_index('ix_llm_models_provider', table_name='llm_models')
    op.drop_table('llm_models')
    op.drop_index('ix_api_credentials_provider', table_name='api_credentials')
    op.drop_table('api_credentials')
