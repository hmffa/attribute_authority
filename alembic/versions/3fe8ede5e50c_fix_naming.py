"""fix naming

Revision ID: 3fe8ede5e50c
Revises: 5fb89e5363eb
Create Date: 2025-11-30 23:33:44.640394

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3fe8ede5e50c'
down_revision: Union[str, Sequence[str], None] = '5fb89e5363eb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema with safe renames."""
    # 1. Rename the table from the old concatenated name to snake_case
    op.rename_table('userattributevalues', 'user_attribute_values')

    # 2. Rename the indexes to match the new table name
    # Note: We use execute for safer index renaming on Postgres
    op.execute('ALTER INDEX IF EXISTS ix_userattributevalues_id RENAME TO ix_user_attribute_values_id')
    op.execute('ALTER INDEX IF EXISTS ix_userattributevalues_user_id RENAME TO ix_user_attribute_values_user_id')
    op.execute('ALTER INDEX IF EXISTS ix_userattributevalues_attribute_id RENAME TO ix_user_attribute_values_attribute_id')

    # 3. Rename the constraint on 'users' to match the Model definition
    # The previous migration named it 'uq_users_sub_iss', but the Model defines 'uq_user_sub_iss'
    op.execute('ALTER TABLE users RENAME CONSTRAINT uq_users_sub_iss TO uq_user_sub_iss')

    # 4. Ensure nullability is enforced (Alembic detected these might be nullable in DB)
    op.alter_column('users', 'sub',
               existing_type=sa.VARCHAR(length=255),
               nullable=False)
    op.alter_column('users', 'iss',
               existing_type=sa.VARCHAR(length=255),
               nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    # 1. Revert constraint name on users
    op.execute('ALTER TABLE users RENAME CONSTRAINT uq_user_sub_iss TO uq_users_sub_iss')

    # 2. Revert nullability (optional, but good for strict downgrade)
    op.alter_column('users', 'iss',
               existing_type=sa.VARCHAR(length=255),
               nullable=True)
    op.alter_column('users', 'sub',
               existing_type=sa.VARCHAR(length=255),
               nullable=True)

    # 3. Rename table back to old name
    op.rename_table('user_attribute_values', 'userattributevalues')

    # 4. Revert index names
    op.execute('ALTER INDEX IF EXISTS ix_user_attribute_values_id RENAME TO ix_userattributevalues_id')
    op.execute('ALTER INDEX IF EXISTS ix_user_attribute_values_user_id RENAME TO ix_userattributevalues_user_id')
    op.execute('ALTER INDEX IF EXISTS ix_user_attribute_values_attribute_id RENAME TO ix_userattributevalues_attribute_id')