"""Marcador de 90 minutos, penales y ganador clasificado.

Revision ID: 0006
Revises: 0005
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("matches", sa.Column("goles_local_90", sa.Integer(), nullable=True))
    op.add_column("matches", sa.Column("goles_visitante_90", sa.Integer(), nullable=True))
    op.add_column("matches", sa.Column("penales_local", sa.Integer(), nullable=True))
    op.add_column("matches", sa.Column("penales_visitante", sa.Integer(), nullable=True))
    op.add_column("matches", sa.Column("ganador", sa.String(length=80), nullable=True))


def downgrade() -> None:
    op.drop_column("matches", "ganador")
    op.drop_column("matches", "penales_visitante")
    op.drop_column("matches", "penales_local")
    op.drop_column("matches", "goles_visitante_90")
    op.drop_column("matches", "goles_local_90")
