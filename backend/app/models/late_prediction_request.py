"""Solicitud de predicción fuera de plazo (requiere aprobación del admin)."""
from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class LatePredictionStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class LatePredictionRequest(Base):
    __tablename__ = "late_prediction_requests"
    __table_args__ = (
        UniqueConstraint(
            "participant_id", "match_id", name="uq_late_prediction_participant_match"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    participant_id: Mapped[int] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE"), index=True
    )
    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), index=True
    )
    pred_local: Mapped[int] = mapped_column(Integer, nullable=False)
    pred_visitante: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[LatePredictionStatus] = mapped_column(
        Enum(LatePredictionStatus), default=LatePredictionStatus.PENDING
    )
    admin_note: Mapped[str | None] = mapped_column(String(300))
    reviewed_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    participant: Mapped["Participant"] = relationship()  # noqa: F821
    match: Mapped["Match"] = relationship()  # noqa: F821
