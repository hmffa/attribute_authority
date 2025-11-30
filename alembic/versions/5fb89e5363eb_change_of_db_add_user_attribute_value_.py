"""change of db. add user_attribute_value and privilege models

Revision ID: 5fb89e5363eb
Revises: 0e0cff7ad121
Create Date: 2025-11-30 23:09:48.794927

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '5fb89e5363eb'
down_revision: Union[str, Sequence[str], None] = '0e0cff7ad121'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema with data preservation."""
    
    # 1. Rename existing tables (User & Invitation) to match new model names
    op.rename_table('user', 'users')
    op.rename_table('invitation', 'invitations')

    # Fix indexes/constraints for 'users'
    op.execute("ALTER INDEX IF EXISTS ix_user_id RENAME TO ix_users_id")
    op.execute("ALTER INDEX IF EXISTS ix_user_iss RENAME TO ix_users_iss")
    op.execute("ALTER INDEX IF EXISTS ix_user_sub RENAME TO ix_users_sub")
    op.execute("ALTER TABLE users RENAME CONSTRAINT uq_user_sub_iss TO uq_users_sub_iss")

    # Fix indexes/constraints for 'invitations'
    op.execute("ALTER INDEX IF EXISTS ix_invitation_id RENAME TO ix_invitations_id")
    op.execute("ALTER INDEX IF EXISTS ix_invitation_hash RENAME TO ix_invitations_hash")
    # Drop old FK on invitations and recreate pointing to 'users'
    op.drop_constraint('invitation_created_by_user_id_fkey', 'invitations', type_='foreignkey')
    op.create_foreign_key(None, 'invitations', 'users', ['created_by_user_id'], ['id'])

    # 2. Create the new 'attributes' definitions table
    op.create_table('attributes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('is_multivalue', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('value_restriction', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_attribute_name')
    )
    op.create_index(op.f('ix_attributes_id'), 'attributes', ['id'], unique=False)

    # 3. DATA MIGRATION: Populate 'attributes' table
    # Extract unique keys from the existing 'attribute' table to create definitions
    op.execute("""
        INSERT INTO attributes (name, is_multivalue, enabled, created_at)
        SELECT DISTINCT key, true, true, MIN(created_at)
        FROM attribute
        GROUP BY key
    """)

    # 4. Transform old 'attribute' table to 'userattributevalues'
    op.rename_table('attribute', 'userattributevalues')

    # Drop old unique constraint (user_id, key, value)
    op.drop_constraint('uq_user_attribute_user_id_key_value', 'userattributevalues', type_='unique')

    # Add new columns
    op.add_column('userattributevalues', sa.Column('attribute_id', sa.Integer(), nullable=True))
    op.add_column('userattributevalues', sa.Column('source', sa.Text(), nullable=True))
    op.add_column('userattributevalues', sa.Column('updated_at', sa.String(length=50), nullable=True))

    # DATA MIGRATION: Map 'key' to 'attribute_id'
    op.execute("""
        UPDATE userattributevalues uav
        SET attribute_id = a.id
        FROM attributes a
        WHERE uav.key = a.name
    """)

    # Set 'updated_at' to 'created_at' for existing rows
    op.execute("UPDATE userattributevalues SET updated_at = created_at")
    op.alter_column('userattributevalues', 'updated_at', nullable=False)

    # Now that attribute_id is populated, make it non-nullable and drop 'key'
    op.alter_column('userattributevalues', 'attribute_id', nullable=False)
    op.drop_column('userattributevalues', 'key')

    # Add Foreign Keys and Constraints for userattributevalues
    op.create_foreign_key(None, 'userattributevalues', 'attributes', ['attribute_id'], ['id'], ondelete='CASCADE')
    # Update user_id FK to point to renamed 'users' table
    op.drop_constraint('userattribute_user_id_fkey', 'userattributevalues', type_='foreignkey')
    op.create_foreign_key(None, 'userattributevalues', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    
    # Create new Unique Constraint (user_id, attribute_id, value)
    op.create_unique_constraint('uq_user_attribute_value_triplet', 'userattributevalues', ['user_id', 'attribute_id', 'value'])

    # Rename indexes
    op.execute("ALTER INDEX IF EXISTS ix_attribute_id RENAME TO ix_userattributevalues_id")
    op.create_index(op.f('ix_userattributevalues_attribute_id'), 'userattributevalues', ['attribute_id'], unique=False)
    op.create_index(op.f('ix_userattributevalues_user_id'), 'userattributevalues', ['user_id'], unique=False)

    # 5. Create new 'privileges' table
    op.create_table('privileges',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('grantee_user_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.Enum('CREATE_ATTR', 'UPDATE_ATTR', 'DELETE_ATTR', 'READ_ATTR', 'SET_VALUE', 'ADD_VALUE', 'REMOVE_VALUE', 'READ_VALUE', 'ASSIGN_PRIVILEGE', name='privilege_action'), nullable=False),
        sa.Column('attribute_id', sa.Integer(), nullable=True),
        sa.Column('value_restriction', sa.Text(), nullable=True),
        sa.Column('target_restriction', sa.JSON(), nullable=True),
        sa.Column('is_delegable', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(['attribute_id'], ['attributes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['grantee_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_privileges_attribute_id'), 'privileges', ['attribute_id'], unique=False)
    op.create_index(op.f('ix_privileges_grantee_user_id'), 'privileges', ['grantee_user_id'], unique=False)
    op.create_index(op.f('ix_privileges_id'), 'privileges', ['id'], unique=False)

    # 6. Drop old Admin Role tables
    # NOTE: Explicit drop_index calls removed to prevent "Index does not exist" errors.
    # Dropping the table automatically removes its indexes in Postgres.
    op.drop_table('attribute_privilege_rule')
    op.drop_table('user_admin_role')
    op.drop_table('admin_role')


def downgrade() -> None:
    """Downgrade schema (Reverse operation)."""
    # Note: Downgrading will likely result in data loss for features specific to the new schema 
    # (e.g. source, value_restriction) unless strictly mapped back.
    
    # 1. Revert Admin Roles (Create empty tables)
    op.create_table('admin_role',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(length=1024), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_admin_role_id'), 'admin_role', ['id'], unique=False)
    
    op.create_table('user_admin_role',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['role_id'], ['admin_role.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'role_id', name='uq_user_admin_role')
    )
    op.create_index(op.f('ix_user_admin_role_id'), 'user_admin_role', ['id'], unique=False)
    
    op.create_table('attribute_privilege_rule',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('description', sa.String(length=1024), nullable=False),
        sa.Column('action', sa.Enum('create', 'read', 'update', 'delete', name='privilegeaction'), nullable=False),
        sa.Column('attribute_key_regex', sa.String(length=1024), nullable=False),
        sa.Column('attribute_value_regex', sa.String(length=1024), nullable=True),
        sa.Column('target_scope', sa.Enum('self', 'any', name='targetscope'), nullable=False),
        sa.Column('required_role_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['required_role_id'], ['admin_role.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_attribute_privilege_rule_id'), 'attribute_privilege_rule', ['id'], unique=False)

    # 2. Drop privileges
    op.drop_table('privileges')
    op.execute("DROP TYPE privilege_action")

    # 3. Revert 'userattributevalues' to 'attribute'
    op.add_column('userattributevalues', sa.Column('key', sa.String(length=1024), nullable=True))
    
    # Restore 'key' from 'attributes' table
    op.execute("""
        UPDATE userattributevalues uav
        SET key = a.name
        FROM attributes a
        WHERE uav.attribute_id = a.id
    """)
    op.alter_column('userattributevalues', 'key', nullable=False)
    
    op.drop_column('userattributevalues', 'attribute_id')
    op.drop_column('userattributevalues', 'source')
    op.drop_column('userattributevalues', 'updated_at')
    
    op.drop_constraint('uq_user_attribute_value_triplet', 'userattributevalues', type_='unique')
    op.create_unique_constraint('uq_user_attribute_user_id_key_value', 'userattributevalues', ['user_id', 'key', 'value'])
    
    op.rename_table('userattributevalues', 'attribute')
    op.drop_table('attributes')

    # 4. Revert table renames
    op.rename_table('users', 'user')
    op.rename_table('invitations', 'invitation')
    
    # Restore index names
    op.execute("ALTER INDEX IF EXISTS ix_users_id RENAME TO ix_user_id")
    op.execute("ALTER INDEX IF EXISTS ix_users_iss RENAME TO ix_user_iss")
    op.execute("ALTER INDEX IF EXISTS ix_users_sub RENAME TO ix_user_sub")
    op.execute("ALTER TABLE user RENAME CONSTRAINT uq_users_sub_iss TO uq_user_sub_iss")
    
    op.execute("ALTER INDEX IF EXISTS ix_invitations_id RENAME TO ix_invitation_id")
    op.execute("ALTER INDEX IF EXISTS ix_invitations_hash RENAME TO ix_invitation_hash")