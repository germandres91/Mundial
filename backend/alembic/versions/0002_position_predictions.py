"""Pronósticos de puestos finales

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-10 00:00:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "position_predictions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("participant_id", sa.Integer(), nullable=False),
        sa.Column("posicion", sa.Integer(), nullable=False),
        sa.Column("equipo", sa.String(length=80), nullable=False),
        sa.Column("puntos", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("participant_id", "posicion", name="uq_position_participant"),
    )
    op.create_index(
        "ix_position_predictions_participant_id", "position_predictions", ["participant_id"]
    )


def downgrade() -> None:
    op.drop_table("position_predictions")
