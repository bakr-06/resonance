"""add occupation to resonance_user

Revision ID: 1debde5ff346
Revises: 9920fe88ac84
Create Date: 2026-11-02 16:36:37.285851

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1debde5ff346'
down_revision: Union[str, Sequence[str], None] = '9920fe88ac84'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("resonance_user", sa.Column("occupation", sa.String(length=255), nullable=True))
    op.execute("UPDATE resonance_user SET occupation = 'Unknown' WHERE occupation IS NULL")
    op.alter_column("resonance_user", "occupation", nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("resonance_user", "occupation")
