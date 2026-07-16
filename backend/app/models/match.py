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
    # Marcador al finalizar los 90 minutos reglamentarios (usado para puntuar).
    goles_local_90: Mapped[int | None] = mapped_column(Integer)
    goles_visitante_90: Mapped[int | None] = mapped_column(Integer)
    # Tanda de penales (solo el conteo de penales, no suma al marcador final).
    penales_local: Mapped[int | None] = mapped_column(Integer)
    penales_visitante: Mapped[int | None] = mapped_column(Integer)
    # Equipo que avanza en la llave (puede ganar en tiempo extra o penales).
    ganador: Mapped[str | None] = mapped_column(String(80))
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

    def scoring_goals(self) -> tuple[int | None, int | None]:
        """Marcador válido para calcular puntos de predicciones (solo 90 minutos)."""
        if self.goles_local_90 is not None and self.goles_visitante_90 is not None:
            return self.goles_local_90, self.goles_visitante_90
        return self.goles_local, self.goles_visitante

    def live_scoring_goals(self) -> tuple[int | None, int | None]:
        """Marcador provisional en vivo; congela en 90' si ya está registrado."""
        if self.estado != MatchStatus.LIVE:
            return self.scoring_goals()
        if self.goles_local_90 is not None and self.goles_visitante_90 is not None:
            return self.goles_local_90, self.goles_visitante_90
        return self.goles_local, self.goles_visitante

    def classified_winner(self) -> str | None:
        """Ganador de la llave (clasificado), no el resultado de los 90 minutos."""
        if self.ganador:
            return self.ganador
        if self.goles_local is None or self.goles_visitante is None:
            return None
        if self.goles_local > self.goles_visitante:
            return self.local
        if self.goles_visitante > self.goles_local:
            return self.visitante
        if self.penales_local is not None and self.penales_visitante is not None:
            return self.local if self.penales_local > self.penales_visitante else self.visitante
        return None

    def classified_loser(self) -> str | None:
        """Perdedor de la llave (va al partido de tercer puesto desde semis)."""
        winner = self.classified_winner()
        if winner is None:
            return None
        if winner == self.local:
            return self.visitante
        if winner == self.visitante:
            return self.local
        return None
