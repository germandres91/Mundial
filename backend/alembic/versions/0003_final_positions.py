"""Posiciones finales reales del torneo

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-10 00:00:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "final_positions",
        sa.Column("posicion", sa.Integer(), primary_key=True),
        sa.Column("equipo", sa.String(length=80), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("final_positions")
