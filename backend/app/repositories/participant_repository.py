"""Repositorio de participantes."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.participant import Participant


class ParticipantRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self) -> list[Participant]:
        return list(self.db.scalars(select(Participant).order_by(Participant.nombre)))

    def get(self, participant_id: int) -> Participant | None:
        return self.db.get(Participant, participant_id)

    def get_by_email(self, email: str) -> Participant | None:
        return self.db.scalar(select(Participant).where(Participant.email == email))

    def create(self, nombre: str, email: str) -> Participant:
        participant = Participant(nombre=nombre, email=email)
        self.db.add(participant)
        self.db.flush()
        return participant

    def delete(self, participant: Participant) -> None:
        self.db.delete(participant)
        self.db.flush()
