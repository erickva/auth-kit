"""
Reference Migration: Add Social OAuth Tables

This is a reference migration script for adding Social OAuth support.
Copy and adapt this to your project's Alembic migrations.

Revision ID: social_oauth_001
Revises: <your_previous_revision>
Create Date: 2024-01-01 00:00:00.000000

To use this migration in your project:
1. Copy this file to your alembic/versions/ directory
2. Update the revision ID and revises fields
3. Run: alembic upgrade head
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'social_oauth_001'
down_revision = None  # Update this to your previous revision
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add has_usable_password column to users table
    # Default is True for existing users (they have passwords)
    op.add_column(
        'users',
        sa.Column(
            'has_usable_password',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('true')
        )
    )

    # Create social_accounts table
    op.create_table(
        'social_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'user_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
            index=True
        ),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('provider_user_id', sa.String(255), nullable=False),
        sa.Column('provider_email', sa.String(255), nullable=True),
        sa.Column('provider_username', sa.String(255), nullable=True),
        sa.Column('access_token_enc', sa.Text(), nullable=True),
        sa.Column('refresh_token_enc', sa.Text(), nullable=True),
        sa.Column('id_token_enc', sa.Text(), nullable=True),
        sa.Column('token_type', sa.String(50), nullable=True),
        sa.Column('scope', sa.String(500), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        # Unique constraints
        sa.UniqueConstraint(
            'provider', 'provider_user_id',
            name='uq_social_provider_user'
        ),
        sa.UniqueConstraint(
            'user_id', 'provider',
            name='uq_social_user_provider'
        ),
    )

    # Create index on user_id for faster lookups
    op.create_index(
        'ix_social_accounts_user_id',
        'social_accounts',
        ['user_id']
    )


def downgrade() -> None:
    # Drop social_accounts table
    op.drop_index('ix_social_accounts_user_id', table_name='social_accounts')
    op.drop_table('social_accounts')

    # Remove has_usable_password column
    op.drop_column('users', 'has_usable_password')
