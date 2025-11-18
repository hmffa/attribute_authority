"""add new_field to users

Revision ID: 929c3845f5a3
Revises: cd48ce93666f
Create Date: 2025-11-18 09:46:32.430914

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '929c3845f5a3'
down_revision: Union[str, Sequence[str], None] = 'cd48ce93666f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # rename the table instead of drop + create
    op.rename_table('userattribute', 'attribute')

    op.drop_index('ix_userattribute_id', table_name='attribute')
    op.create_index('ix_attribute_id', 'attribute', ['id'])

    # add new columns to user table
    op.add_column('user', sa.Column('name', sa.String(length=255), nullable=True))
    op.add_column('user', sa.Column('email', sa.String(length=255), nullable=True))



def downgrade() -> None:
    op.drop_column('user', 'email')
    op.drop_column('user', 'name')

    op.drop_index('ix_attribute_id', table_name='attribute')
    op.create_index('ix_userattribute_id', 'attribute', ['id'])
    op.rename_table('attribute', 'userattribute')

