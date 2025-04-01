"""update user fields

Revision ID: update_user_fields
Revises: add_bot_instances_table
Create Date: 2024-04-01 18:40:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'update_user_fields'
down_revision = 'add_bot_instances_table'
branch_labels = None
depends_on = None


def upgrade():
    # Удаляем старые колонки
    op.drop_column('users', 'age')
    op.drop_column('users', 'gender')
    op.drop_column('users', 'profession')
    op.drop_column('users', 'interests')
    op.drop_column('users', 'language')
    op.drop_column('users', 'meeting_time')

    # Добавляем новые колонки
    op.add_column('users', sa.Column('city', sa.String(), nullable=True))
    op.add_column('users', sa.Column(
        'social_link', sa.String(), nullable=True))
    op.add_column('users', sa.Column('about', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('job', sa.String(), nullable=True))
    op.add_column('users', sa.Column(
        'birth_date', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('avatar', sa.String(), nullable=True))
    op.add_column('users', sa.Column('hobbies', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('status', sa.String(50),
                  nullable=False, server_default='active'))
    op.add_column('users', sa.Column('is_active', sa.Boolean(),
                  nullable=False, server_default='true'))
    op.add_column('users', sa.Column('show_profile', sa.Boolean(),
                  nullable=False, server_default='true'))
    op.add_column('users', sa.Column('experience_level',
                  sa.Integer(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('total_meetings',
                  sa.Integer(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('average_rating',
                  sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('users', sa.Column('last_active', sa.DateTime(),
                  nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')))
    op.add_column('users', sa.Column('settings', sa.Text(), nullable=True))


def downgrade():
    # Удаляем новые колонки
    op.drop_column('users', 'city')
    op.drop_column('users', 'social_link')
    op.drop_column('users', 'about')
    op.drop_column('users', 'job')
    op.drop_column('users', 'birth_date')
    op.drop_column('users', 'avatar')
    op.drop_column('users', 'hobbies')
    op.drop_column('users', 'status')
    op.drop_column('users', 'is_active')
    op.drop_column('users', 'show_profile')
    op.drop_column('users', 'experience_level')
    op.drop_column('users', 'total_meetings')
    op.drop_column('users', 'average_rating')
    op.drop_column('users', 'last_active')
    op.drop_column('users', 'settings')

    # Возвращаем старые колонки
    op.add_column('users', sa.Column('age', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('gender', sa.String(50), nullable=True))
    op.add_column('users', sa.Column(
        'profession', sa.String(255), nullable=True))
    op.add_column('users', sa.Column(
        'interests', sa.String(500), nullable=True))
    op.add_column('users', sa.Column(
        'language', sa.String(100), nullable=True))
    op.add_column('users', sa.Column(
        'meeting_time', sa.String(100), nullable=True))
