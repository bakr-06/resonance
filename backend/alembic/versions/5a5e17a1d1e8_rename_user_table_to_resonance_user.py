"""rename user table to resonance_user

Revision ID: 5a5e17a1d1e8
Revises: fa51e323b32f
Create Date: 2026-10-30 13:34:44.269405

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5a5e17a1d1e8'
down_revision: Union[str, Sequence[str], None] = 'fa51e323b32f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.rename_table("user", "resonance_user")
    op.drop_constraint("session_user_id_fkey", "session", type_="foreignkey")
    op.create_foreign_key("session_user_id_fkey", "session", "resonance_user", ["user_id"], ["id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("session_user_id_fkey", "session", type_="foreignkey")
    op.rename_table("resonance_user", "user")
    op.create_foreign_key("session_user_id_fkey", "session", "user", ["user_id"], ["id"])
