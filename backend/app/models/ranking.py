"""Modelo de ranking agregado por participante."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Ranking(Base):
    __tablename__ = "rankings"

    participant_id: Mapped[int] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE"), primary_key=True
    )
    puntos_totales: Mapped[int] = mapped_column(Integer, default=0, index=True)
    posicion: Mapped[int] = mapped_column(Integer, default=0)
    aciertos_exactos: Mapped[int] = mapped_column(Integer, default=0)
    partidos_acertados: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    participant: Mapped["Participant"] = relationship(back_populates="ranking")  # noqa: F821
