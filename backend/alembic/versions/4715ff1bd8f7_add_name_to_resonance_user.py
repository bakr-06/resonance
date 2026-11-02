"""add name to resonance_user

Revision ID: 4715ff1bd8f7
Revises: 5a5e17a1d1e8
Create Date: 2026-10-30 13:40:41.833471

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4715ff1bd8f7'
down_revision: Union[str, Sequence[str], None] = '5a5e17a1d1e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("resonance_user", sa.Column("name", sa.String(length=255), nullable=True))
    op.execute("UPDATE resonance_user SET name = 'Unknown' WHERE name IS NULL")
    op.alter_column("resonance_user", "name", nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("resonance_user", "name")
