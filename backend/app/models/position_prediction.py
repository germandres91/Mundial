"""Modelo de pronóstico de los primeros puestos del torneo."""
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PositionPrediction(Base):
    """Pronóstico de un participante para un puesto final (1° a 4°)."""

    __tablename__ = "position_predictions"
    __table_args__ = (
        UniqueConstraint("participant_id", "posicion", name="uq_position_participant"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    participant_id: Mapped[int] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE"), index=True
    )
    posicion: Mapped[int] = mapped_column(Integer, nullable=False)
    equipo: Mapped[str] = mapped_column(String(80), nullable=False)
    puntos: Mapped[int] = mapped_column(Integer, default=0)

    participant: Mapped["Participant"] = relationship(  # noqa: F821
        back_populates="position_predictions"
    )
