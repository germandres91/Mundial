"""Utilidades para separar marcador de 90 minutos vs resultado oficial."""
from __future__ import annotations


def _parse_period_scores(linescores: list | None) -> list[int]:
    if not linescores:
        return []
    out: list[int] = []
    for item in linescores:
        try:
            out.append(int(str(item.get("displayValue", item)).strip()))
        except (TypeError, ValueError, AttributeError):
            out.append(0)
    return out


def regulation_from_linescores(
    home_linescores: list | None, away_linescores: list | None
) -> tuple[int | None, int | None]:
    """Suma 1.er y 2.º tiempo (índices 0 y 1) como marcador reglamentario."""
    home = _parse_period_scores(home_linescores)
    away = _parse_period_scores(away_linescores)
    if len(home) < 2 or len(away) < 2:
        return None, None
    return home[0] + home[1], away[0] + away[1]


def penalties_from_linescores(
    home_linescores: list | None, away_linescores: list | None
) -> tuple[int | None, int | None]:
    """Último periodo suele ser la tanda de penales cuando hay 5 líneas."""
    home = _parse_period_scores(home_linescores)
    away = _parse_period_scores(away_linescores)
    if len(home) >= 5 and len(away) >= 5:
        return home[4], away[4]
    return None, None


def winner_team_name(home: dict, away: dict) -> str | None:
    """Nombre del equipo clasificado según la API (winner/advance)."""
    for comp in (home, away):
        if comp.get("winner") or comp.get("advance"):
            return (comp.get("team") or {}).get("displayName")
    return None
