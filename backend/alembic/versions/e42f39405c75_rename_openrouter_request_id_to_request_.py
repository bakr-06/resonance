"""Rename openrouter_request_id to request_id

Revision ID: e42f39405c75
Revises: 9ddbc4fe58c9
Create Date: 2026-10-22 23:12:00.319848

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e42f39405c75'
down_revision: Union[str, Sequence[str], None] = '9ddbc4fe58c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column('analysis_metrics', 'openrouter_request_id', new_column_name='request_id')


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('analysis_metrics', 'request_id', new_column_name='openrouter_request_id')
