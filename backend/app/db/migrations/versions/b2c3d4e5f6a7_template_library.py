"""template library (folders, templates) + job template_ids

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-16 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: str | None = 'a1b2c3d4e5f6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('template_ids', sa.JSON(), nullable=True))

    op.create_table(
        'template_folders',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('parent_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_template_folders_parent_id', 'template_folders', ['parent_id'])

    op.create_table(
        'templates',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('kind', sa.String(length=32), nullable=False),
        sa.Column('folder_id', sa.String(length=36), nullable=True),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_templates_kind', 'templates', ['kind'])
    op.create_index('ix_templates_folder_id', 'templates', ['folder_id'])


def downgrade() -> None:
    op.drop_index('ix_templates_folder_id', table_name='templates')
    op.drop_index('ix_templates_kind', table_name='templates')
    op.drop_table('templates')
    op.drop_index('ix_template_folders_parent_id', table_name='template_folders')
    op.drop_table('template_folders')
    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.drop_column('template_ids')
