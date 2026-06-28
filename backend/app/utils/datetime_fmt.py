"""Serialización de fechas en UTC para la API."""
from __future__ import annotations

from datetime import datetime, timezone


def utc_iso(dt: datetime | None) -> str | None:
    """ISO-8601 en UTC con offset explícito (SQLite guarda naive = UTC)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()
