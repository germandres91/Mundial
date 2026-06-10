"""Modelo de participante del concurso."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(180), unique=True, index=True, nullable=False)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    predictions: Mapped[list["Prediction"]] = relationship(  # noqa: F821
        back_populates="participant", cascade="all, delete-orphan"
    )
    scores: Mapped[list["Score"]] = relationship(  # noqa: F821
        back_populates="participant", cascade="all, delete-orphan"
    )
    ranking: Mapped["Ranking | None"] = relationship(  # noqa: F821
        back_populates="participant", cascade="all, delete-orphan", uselist=False
    )
    position_predictions: Mapped[list["PositionPrediction"]] = relationship(  # noqa: F821
        back_populates="participant", cascade="all, delete-orphan"
    )
