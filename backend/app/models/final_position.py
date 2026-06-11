"""Modelo de las posiciones finales reales del torneo (1° a 4°)."""
from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FinalPosition(Base):
    """Resultado oficial de un puesto final del Mundial.

    Hay como máximo 4 filas (posiciones 1 a 4). Se usan para puntuar los
    pronósticos de posiciones de cada participante al terminar el torneo.
    """

    __tablename__ = "final_positions"

    posicion: Mapped[int] = mapped_column(Integer, primary_key=True)
    equipo: Mapped[str] = mapped_column(String(80), nullable=False)
