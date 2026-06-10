"""Modelo de puntaje obtenido por un participante en un partido."""
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Score(Base):
    __tablename__ = "scores"
    __table_args__ = (
        UniqueConstraint("participant_id", "match_id", name="uq_score_participant_match"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    participant_id: Mapped[int] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE"), index=True
    )
    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), index=True
    )
    puntos: Mapped[int] = mapped_column(Integer, default=0)
    detalle: Mapped[str | None] = mapped_column(String(200))

    participant: Mapped["Participant"] = relationship(back_populates="scores")  # noqa: F821
    match: Mapped["Match"] = relationship(back_populates="scores")  # noqa: F821
