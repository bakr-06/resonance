"""replace exchange with message

Revision ID: 9920fe88ac84
Revises: 4715ff1bd8f7
Create Date: 2026-11-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9920fe88ac84'
down_revision: Union[str, Sequence[str], None] = '4715ff1bd8f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Replace the exchange table with a role-tagged message log.

    The existing sessions and exchanges are development data, so they are
    discarded rather than converted (same approach as ADR 0002). The dummy
    user is kept: only session-owned data is removed.
    """
    op.execute(
        "TRUNCATE TABLE analysis_metrics, transcription_metrics, exchange, session CASCADE"
    )

    op.drop_table('analysis_metrics')
    op.drop_table('transcription_metrics')
    op.drop_table('exchange')

    op.create_table(
        'message',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column(
            'role',
            sa.Enum('user', 'assistant', name='messagerole'),
            nullable=False,
        ),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['session.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        'ix_message_session_created_at',
        'message',
        ['session_id', 'created_at', 'id'],
    )

    op.create_table(
        'transcription_metrics',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('transcript_segments', postgresql.JSONB(), nullable=False),
        sa.Column('transcript_duration_ms', sa.Integer(), nullable=False),
        sa.Column('processing_ms', sa.Integer(), nullable=False),
        sa.Column('detected_language', sa.String(length=10), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['id'], ['message.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'analysis_metrics',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('prompt_tokens', sa.Integer(), nullable=False),
        sa.Column('completion_tokens', sa.Integer(), nullable=False),
        sa.Column('request_id', sa.String(), nullable=False),
        sa.Column('model_used', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('processing_ms', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['id'], ['message.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Rebuild the exchange tables. The discarded data cannot be recovered."""
    op.drop_table('analysis_metrics')
    op.drop_table('transcription_metrics')
    op.drop_table('message')
    op.execute("DROP TYPE IF EXISTS messagerole")

    op.create_table(
        'exchange',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('transcript', sa.Text(), nullable=False),
        sa.Column('reflection', sa.Text(), nullable=False),
        sa.Column('detected_mode', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['session.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'transcription_metrics',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('transcript_segments', postgresql.JSONB(), nullable=False),
        sa.Column('transcript_duration_ms', sa.Integer(), nullable=False),
        sa.Column('processing_ms', sa.Integer(), nullable=False),
        sa.Column('detected_language', sa.String(length=10), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['id'], ['exchange.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'analysis_metrics',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('prompt_tokens', sa.Integer(), nullable=False),
        sa.Column('completion_tokens', sa.Integer(), nullable=False),
        sa.Column('request_id', sa.String(), nullable=False),
        sa.Column('model_used', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('processing_ms', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['id'], ['exchange.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
