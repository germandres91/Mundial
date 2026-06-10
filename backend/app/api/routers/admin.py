"""Endpoints de administración: sync, import Excel, reglas, auditoría, usuarios."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.audit_repository import AuditRepository
from app.repositories.scoring_rule_repository import ScoringRuleRepository
from app.schemas.auth import UserCreate, UserOut
from app.schemas.scoring_rule import ScoringRuleOut, ScoringRuleUpdate
from app.services.auth_service import AuthService
from app.services.excel_service import ExcelImportError, ExcelService
from app.services.sync_service import SyncService

router = APIRouter()


@router.post("/sync")
def trigger_sync(db: Session = Depends(get_db)) -> dict:
    """Ejecuta una sincronización manual con el proveedor de fútbol."""
    return SyncService(db).sync()


@router.post("/import/calendar")
def import_calendar(db: Session = Depends(get_db)) -> dict:
    """Importa el calendario de partidos desde el proveedor configurado."""
    return {"partidos": SyncService(db).import_calendar()}


@router.post("/import/predictions")
def import_predictions(db: Session = Depends(get_db)) -> dict:
    """Importa participantes y predicciones desde el Excel configurado."""
    try:
        return ExcelService(db).import_predictions()
    except ExcelImportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/import/rules")
def import_rules(db: Session = Depends(get_db)) -> dict:
    """Importa las reglas de puntaje desde el Excel configurado."""
    return {"reglas": ExcelService(db).import_rules()}


@router.get("/rules", response_model=list[ScoringRuleOut])
def list_rules(db: Session = Depends(get_db)) -> list:
    return ScoringRuleRepository(db).list()


@router.put("/rules/{code}", response_model=ScoringRuleOut)
def update_rule(code: str, payload: ScoringRuleUpdate, db: Session = Depends(get_db)):
    repo = ScoringRuleRepository(db)
    rule = repo.get_by_code(code.upper())
    if rule is None:
        raise HTTPException(status_code=404, detail="Regla no encontrada")
    if payload.descripcion is not None:
        rule.descripcion = payload.descripcion
    if payload.puntos is not None:
        rule.puntos = payload.puntos
    if payload.activo is not None:
        rule.activo = payload.activo
    db.commit()
    return rule


@router.get("/audit")
def list_audit(limit: int = 200, db: Session = Depends(get_db)) -> list:
    return [
        {
            "id": a.id,
            "actor": a.actor,
            "accion": a.accion,
            "entidad": a.entidad,
            "detalle": a.detalle,
            "created_at": a.created_at,
        }
        for a in AuditRepository(db).list(limit=limit)
    ]


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    service = AuthService(db)
    if service.users.get_by_email(payload.email.lower()):
        raise HTTPException(status_code=409, detail="El email ya está registrado")
    return service.register(
        email=payload.email,
        nombre=payload.nombre,
        password=payload.password,
        role=payload.role,
    )


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)) -> list:
    return AuthService(db).users.list()
