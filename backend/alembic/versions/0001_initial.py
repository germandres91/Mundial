"""Esquema inicial

Revision ID: 0001
Revises:
Create Date: 2026-01-01 00:00:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

match_status = sa.Enum(
    "SCHEDULED", "LIVE", "FINISHED", "POSTPONED", "CANCELLED", name="matchstatus"
)
user_role = sa.Enum("ADMIN", "PARTICIPANT", name="userrole")


def upgrade() -> None:
    op.create_table(
        "participants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=180), nullable=False),
        sa.Column("fecha_creacion", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_participants_email", "participants", ["email"], unique=True)

    op.create_table(
        "matches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fifa_id", sa.String(length=64), nullable=True),
        sa.Column("grupo", sa.String(length=10), nullable=True),
        sa.Column("fase", sa.String(length=40), nullable=True),
        sa.Column("local", sa.String(length=80), nullable=False),
        sa.Column("visitante", sa.String(length=80), nullable=False),
        sa.Column("fecha", sa.DateTime(timezone=True), nullable=True),
        sa.Column("goles_local", sa.Integer(), nullable=True),
        sa.Column("goles_visitante", sa.Integer(), nullable=True),
        sa.Column("estado", match_status, nullable=False),
    )
    op.create_index("ix_matches_fifa_id", "matches", ["fifa_id"], unique=True)
    op.create_index("ix_matches_fecha", "matches", ["fecha"])
    op.create_index("ix_matches_estado", "matches", ["estado"])

    op.create_table(
        "predictions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("participant_id", sa.Integer(), nullable=False),
        sa.Column("match_id", sa.Integer(), nullable=False),
        sa.Column("pred_local", sa.Integer(), nullable=False),
        sa.Column("pred_visitante", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "participant_id", "match_id", name="uq_prediction_participant_match"
        ),
    )
    op.create_index("ix_predictions_participant_id", "predictions", ["participant_id"])
    op.create_index("ix_predictions_match_id", "predictions", ["match_id"])

    op.create_table(
        "scores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("participant_id", sa.Integer(), nullable=False),
        sa.Column("match_id", sa.Integer(), nullable=False),
        sa.Column("puntos", sa.Integer(), nullable=True),
        sa.Column("detalle", sa.String(length=200), nullable=True),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("participant_id", "match_id", name="uq_score_participant_match"),
    )
    op.create_index("ix_scores_participant_id", "scores", ["participant_id"])
    op.create_index("ix_scores_match_id", "scores", ["match_id"])

    op.create_table(
        "rankings",
        sa.Column("participant_id", sa.Integer(), primary_key=True),
        sa.Column("puntos_totales", sa.Integer(), nullable=True),
        sa.Column("posicion", sa.Integer(), nullable=True),
        sa.Column("aciertos_exactos", sa.Integer(), nullable=True),
        sa.Column("partidos_acertados", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_rankings_puntos_totales", "rankings", ["puntos_totales"])

    op.create_table(
        "scoring_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("descripcion", sa.String(length=200), nullable=False),
        sa.Column("puntos", sa.Integer(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=True),
    )
    op.create_index("ix_scoring_rules_code", "scoring_rules", ["code"], unique=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=180), nullable=False),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("participant_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor", sa.String(length=180), nullable=True),
        sa.Column("accion", sa.String(length=120), nullable=False),
        sa.Column("entidad", sa.String(length=80), nullable=True),
        sa.Column("detalle", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_audit_logs_accion", "audit_logs", ["accion"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("users")
    op.drop_table("scoring_rules")
    op.drop_table("rankings")
    op.drop_table("scores")
    op.drop_table("predictions")
    op.drop_table("matches")
    op.drop_table("participants")
    match_status.drop(op.get_bind(), checkfirst=True)
    user_role.drop(op.get_bind(), checkfirst=True)
