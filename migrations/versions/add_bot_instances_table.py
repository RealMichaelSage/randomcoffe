"""add bot instances table

Revision ID: add_bot_instances_table
Revises: 570c503e450b
Create Date: 2024-03-21 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = 'add_bot_instances_table'
down_revision = '570c503e450b'
branch_labels = None
depends_on = None


def upgrade():
    # Создаем таблицу bot_instances
    op.create_table(
        'bot_instances',
        sa.Column('instance_id', UUID(), nullable=False),
        sa.Column('last_heartbeat', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('instance_id')
    )


def downgrade():
    # Удаляем таблицу bot_instances
    op.drop_table('bot_instances')
