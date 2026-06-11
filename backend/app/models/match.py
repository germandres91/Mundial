"""Modelo de partido del Mundial 2026."""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MatchStatus(str, enum.Enum):
    """Estados posibles de un partido."""

    SCHEDULED = "SCHEDULED"
    LIVE = "LIVE"
    FINISHED = "FINISHED"
    POSTPONED = "POSTPONED"
    CANCELLED = "CANCELLED"


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fifa_id: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
    grupo: Mapped[str | None] = mapped_column(String(10))
    fase: Mapped[str | None] = mapped_column(String(40))
    local: Mapped[str] = mapped_column(String(80), nullable=False)
    visitante: Mapped[str] = mapped_column(String(80), nullable=False)
    fecha: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    goles_local: Mapped[int | None] = mapped_column(Integer)
    goles_visitante: Mapped[int | None] = mapped_column(Integer)
    estado: Mapped[MatchStatus] = mapped_column(
        Enum(MatchStatus), default=MatchStatus.SCHEDULED, index=True
    )
    # Minuto de juego en vivo (texto del proveedor, p. ej. "45'" o "90'+8'").
    minuto: Mapped[str | None] = mapped_column(String(16))

    predictions: Mapped[list["Prediction"]] = relationship(  # noqa: F821
        back_populates="match", cascade="all, delete-orphan"
    )
    scores: Mapped[list["Score"]] = relationship(  # noqa: F821
        back_populates="match", cascade="all, delete-orphan"
    )

    @property
    def is_finished(self) -> bool:
        return self.estado == MatchStatus.FINISHED
