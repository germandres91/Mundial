"""Modelo de regla de puntaje (importada desde Excel)."""
from __future__ import annotations

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ScoringRule(Base):
    """Reglas configurables del concurso.

    `code` identifica el tipo de acierto y `puntos` el valor asignado.
    Ejemplos: EXACT, WINNER_GOALS, WINNER, DRAW, NONE.
    """

    __tablename__ = "scoring_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    descripcion: Mapped[str] = mapped_column(String(200))
    puntos: Mapped[int] = mapped_column(Integer, default=0)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
