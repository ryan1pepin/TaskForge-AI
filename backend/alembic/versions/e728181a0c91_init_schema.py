"""init_schema

Revision ID: e728181a0c91
Revises: 
Create Date: 2026-07-13 15:59:09.137603

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e728181a0c91'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Create core tables and composite indexes manually."""
    
    # 1. CREATE USERS TABLE
    # - Using UUID for PK to prevent enumeration attacks and support distributed id generation
    # - unique constraint on email to prevent duplicate accounts
    op.create_table(
        'users',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    # Explicit index for fast email lookups (e.g. at login/registration check)
    op.create_index('idx_users_email', 'users', ['email'], unique=True)

    # 2. CREATE REFRESH TOKENS TABLE
    # - Storing SHA256 hashes of refresh tokens rather than raw strings for cryptographic safety in DB
    # - CASCADE deletion deletes all session tokens if a user account is deleted
    op.create_table(
        'refresh_tokens',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('token_hash', sa.String(length=255), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash')
    )
    # Composite index for filtering active/inactive sessions by user
    op.create_index('idx_rt_user_expires', 'refresh_tokens', ['user_id', 'expires_at'])

    # 3. CREATE PROJECTS TABLE
    # - status restricted to 50 chars to accommodate draft/active/archived enums
    # - deleted_at supports soft-delete auditing without breaking foreign keys
    op.create_table(
        'projects',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('owner_id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(length=1000), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='draft'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    # Composite index targeting our paginated lists (where we query by owner, status, and filter deleted_at)
    op.create_index('idx_proj_owner_status_deleted', 'projects', ['owner_id', 'status', 'deleted_at'])

    # 4. CREATE TASKS TABLE
    # - priority constrained between 0 and 3 (low to critical) using a CheckConstraint
    # - order_index used for sorting tasks (crucial for drag-and-drop sync)
    op.create_table(
        'tasks',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(length=1000), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='todo'),
        sa.Column('priority', sa.SmallInteger(), nullable=False, server_default='0'),
        sa.Column('order_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint('priority >= 0 AND priority <= 3', name='check_priority_range'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    # Composite index for querying tasks inside a project sorted by drag-and-drop index
    op.create_index('idx_task_proj_order_deleted', 'tasks', ['project_id', 'order_index', 'deleted_at'])


def downgrade() -> None:
    """Downgrade schema: Drop tables in reverse order to respect foreign key constraints."""
    op.drop_index('idx_task_proj_order_deleted', table_name='tasks')
    op.drop_table('tasks')
    op.drop_index('idx_proj_owner_status_deleted', table_name='projects')
    op.drop_table('projects')
    op.drop_index('idx_rt_user_expires', table_name='refresh_tokens')
    op.drop_table('refresh_tokens')
    op.drop_index('idx_users_email', table_name='users')
    op.drop_table('users')
