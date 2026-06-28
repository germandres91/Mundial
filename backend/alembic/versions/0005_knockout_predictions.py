"""Predicciones bloqueadas y solicitudes tardías de eliminatorias.

Revision ID: 0005
Revises: 0004
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "predictions",
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "late_prediction_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("participant_id", sa.Integer(), sa.ForeignKey("participants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("matches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("pred_local", sa.Integer(), nullable=False),
        sa.Column("pred_visitante", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PENDING", "APPROVED", "REJECTED", name="latepredictionstatus"),
            nullable=False,
        ),
        sa.Column("admin_note", sa.String(length=300), nullable=True),
        sa.Column("reviewed_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("participant_id", "match_id", name="uq_late_prediction_participant_match"),
    )


def downgrade() -> None:
    op.drop_table("late_prediction_requests")
    op.drop_column("predictions", "locked_at")
