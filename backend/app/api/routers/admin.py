"""Endpoints de administración: sync, import Excel, reglas, auditoría, usuarios."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.match import MatchStatus
from app.models.user import User
from app.providers import get_provider
from app.repositories.audit_repository import AuditRepository
from app.repositories.final_position_repository import FinalPositionRepository
from app.repositories.match_repository import MatchRepository
from app.repositories.scoring_rule_repository import ScoringRuleRepository
from app.schemas.auth import PasswordReset, UserCreate, UserOut
from app.schemas.final_position import FinalPositionsUpdate
from app.schemas.scoring_rule import ScoringRuleOut, ScoringRuleUpdate
from app.services.auth_service import AuthService
from app.services.excel_service import ExcelImportError, ExcelService
from app.services.ranking_service import RankingService
from app.services.scoring_service import ScoringService
from app.services.sync_service import SyncService
from app.services.tournament_reset_service import TournamentResetService

router = APIRouter()


@router.post("/sync")
def trigger_sync(db: Session = Depends(get_db)) -> dict:
    """Ejecuta una sincronización manual con el proveedor de fútbol."""
    return SyncService(db).sync()


@router.get("/sync/status")
def sync_status(db: Session = Depends(get_db)) -> dict:
    """Estado del proveedor y resultado de la última sincronización."""
    from datetime import timezone

    last = AuditRepository(db).last_by_accion("SYNC")
    matches = MatchRepository(db)
    provider = (settings.football_provider or "mock").lower()

    # ESPN y mock no requieren API key; football-data sí.
    requiere_key = provider not in ("mock", "espn")
    provider_listo = (not requiere_key) or bool(settings.football_api_key)

    # Sondeo rápido: ¿la API responde y cuántos partidos trae ahora?
    api_count = None
    api_error = None
    if provider != "mock":
        try:
            api_count = len(get_provider().fetch_matches())
            if api_count == 0:
                api_error = "La API respondió pero sin partidos (revisa la configuración)"
        except Exception as exc:  # noqa: BLE001
            api_error = str(exc)

    ultima = None
    if last:
        created = last.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        ultima = {
            "detalle": last.detalle,
            "actor": last.actor,
            "created_at": created.astimezone(timezone.utc).isoformat(),
        }

    competition = settings.espn_league if provider == "espn" else settings.football_competition_id

    return {
        "provider": provider,
        "provider_listo": provider_listo,
        "competition": competition,
        "requiere_key": requiere_key,
        "api_key_configurada": bool(settings.football_api_key),
        "sync_habilitada": settings.sync_enabled,
        "intervalo_minutos": settings.sync_interval_minutes,
        "crear_faltantes": settings.sync_create_missing,
        "api_partidos_ahora": api_count,
        "api_error": api_error,
        "partidos": {
            "total": matches.count(),
            "programados": matches.count(MatchStatus.SCHEDULED),
            "en_vivo": matches.count(MatchStatus.LIVE),
            "finalizados": matches.count(MatchStatus.FINISHED),
        },
        "ultima_sync": ultima,
    }


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


@router.post("/reset/tournament")
def reset_tournament(db: Session = Depends(get_db)) -> dict:
    """Reinicia partidos/predicciones/ranking con los datos oficiales del repo.

    Conserva los usuarios de acceso. Útil cuando Azure quedó con datos mock
    antiguos o generados por fallback.
    """
    return TournamentResetService(db).reset_from_seed()


@router.get("/final-positions")
def get_final_positions(db: Session = Depends(get_db)) -> dict:
    """Posiciones finales reales del torneo y los puntos de cada puesto."""
    repo = FinalPositionRepository(db)
    actuales = {fp.posicion: fp.equipo for fp in repo.list()}
    # Puntos efectivos: defaults combinados con lo configurado en la BD.
    rules = ScoringService(db)._points_map()
    return {
        "posiciones": [
            {
                "posicion": pos,
                "equipo": actuales.get(pos, ""),
                "puntos": rules.get(f"POS_{pos}", 0),
            }
            for pos in (1, 2, 3, 4)
        ]
    }


@router.put("/final-positions")
def set_final_positions(
    payload: FinalPositionsUpdate, db: Session = Depends(get_db)
) -> dict:
    """Fija los 4 puestos finales, puntúa los pronósticos y recalcula ranking.

    Un equipo vacío limpia ese puesto (deja de otorgar puntos).
    """
    repo = FinalPositionRepository(db)
    for item in payload.posiciones:
        equipo = (item.equipo or "").strip()
        if equipo:
            repo.upsert(posicion=item.posicion, equipo=equipo)
        else:
            repo.delete(item.posicion)
    db.flush()
    aciertos = ScoringService(db).score_positions()
    db.commit()
    RankingService(db).recalculate()
    AuditRepository(db).log(
        accion="FINAL_POSITIONS",
        actor="admin",
        entidad="final_positions",
        detalle=f"aciertos={aciertos}",
    )
    db.commit()
    return {"aciertos": aciertos}


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


@router.post("/users/{user_id}/reset-password", response_model=UserOut)
def reset_password(
    user_id: int, payload: PasswordReset, db: Session = Depends(get_db)
):
    service = AuthService(db)
    user = service.users.get(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return service.set_password(user, payload.password)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    service = AuthService(db)
    user = service.users.get(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if user.email.lower() == settings.first_admin_email.lower():
        raise HTTPException(
            status_code=400, detail="No se puede eliminar la cuenta de administrador principal"
        )
    if user.id == current.id:
        raise HTTPException(status_code=400, detail="No puedes eliminar tu propia cuenta")
    service.users.delete(user)
    db.commit()
