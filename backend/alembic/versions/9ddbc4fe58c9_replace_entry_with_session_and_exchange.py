"""replace_entry_with_session_and_exchange

Revision ID: 9ddbc4fe58c9
Revises: 0b720c8d04f4
Create Date: 2026-06-29 23:40:04.139874

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9ddbc4fe58c9'
down_revision: Union[str, Sequence[str], None] = '0b720c8d04f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop old FKs, then old tables entirely (starting fresh)
    op.drop_constraint(op.f('analysis_metrics_id_fkey'), 'analysis_metrics', type_='foreignkey')
    op.drop_constraint(op.f('transcription_metrics_id_fkey'), 'transcription_metrics', type_='foreignkey')
    op.drop_table('analysis_metrics')
    op.drop_table('transcription_metrics')
    op.drop_table('entry')

    # Create new tables
    op.create_table('session',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('exchange',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('session_id', sa.UUID(), nullable=False),
    sa.Column('transcript', sa.Text(), nullable=False),
    sa.Column('reflection', sa.Text(), nullable=False),
    sa.Column('detected_mode', sa.String(length=20), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['session_id'], ['session.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('transcription_metrics',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('transcript_segments', postgresql.JSONB(), nullable=False),
    sa.Column('transcript_duration_ms', sa.Integer(), nullable=False),
    sa.Column('processing_ms', sa.Integer(), nullable=False),
    sa.Column('detected_language', sa.String(length=10), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['id'], ['exchange.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('analysis_metrics',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('prompt_tokens', sa.Integer(), nullable=False),
    sa.Column('completion_tokens', sa.Integer(), nullable=False),
    sa.Column('openrouter_request_id', sa.String(), nullable=False),
    sa.Column('model_used', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('processing_ms', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['id'], ['exchange.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop new tables
    op.drop_table('analysis_metrics')
    op.drop_table('transcription_metrics')
    op.drop_table('exchange')
    op.drop_table('session')

    # Recreate old tables with original structure + FKs
    op.create_table('entry',
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('transcript', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('analysis', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False),
    sa.Column('detected_mode', sa.VARCHAR(length=20), autoincrement=False, nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('entry_pkey'))
    )
    op.create_table('transcription_metrics',
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('transcript_segments', postgresql.JSONB(), autoincrement=False, nullable=False),
    sa.Column('transcript_duration_ms', sa.Integer(), autoincrement=False, nullable=False),
    sa.Column('processing_ms', sa.Integer(), autoincrement=False, nullable=False),
    sa.Column('detected_language', sa.VARCHAR(length=10), autoincrement=False, nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('transcription_metrics_pkey')),
    postgresql_ignore_search_path=True
    )
    op.create_table('analysis_metrics',
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('prompt_tokens', sa.Integer(), autoincrement=False, nullable=False),
    sa.Column('completion_tokens', sa.Integer(), autoincrement=False, nullable=False),
    sa.Column('openrouter_request_id', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('model_used', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False),
    sa.Column('processing_ms', sa.Integer(), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('analysis_metrics_pkey'))
    )
    op.create_foreign_key(op.f('transcription_metrics_id_fkey'), 'transcription_metrics', 'entry', ['id'], ['id'])
    op.create_foreign_key(op.f('analysis_metrics_id_fkey'), 'analysis_metrics', 'entry', ['id'], ['id'])
