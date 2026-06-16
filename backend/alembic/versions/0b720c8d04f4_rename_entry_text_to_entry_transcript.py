"""rename entry.text to entry.transcript

Revision ID: 0b720c8d04f4
Revises: 31578e0882d1
Create Date: 2026-06-16 14:46:07.059268

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0b720c8d04f4'
down_revision: Union[str, Sequence[str], None] = '31578e0882d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('entry', 'text', new_column_name='transcript')


def downgrade() -> None:
    op.alter_column('entry', 'transcript', new_column_name='text')
