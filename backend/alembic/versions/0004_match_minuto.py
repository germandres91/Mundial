"""Minuto de juego en vivo en partidos

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-11 00:00:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("matches", sa.Column("minuto", sa.String(length=16), nullable=True))


def downgrade() -> None:
    op.drop_column("matches", "minuto")
