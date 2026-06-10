"""Fábrica de proveedores según la configuración FOOTBALL_PROVIDER."""
from __future__ import annotations

from app.core.config import settings
from app.core.logging import get_logger
from app.providers.api_football_provider import APIFootballProvider
from app.providers.base import BaseFootballProvider
from app.providers.football_data_provider import FootballDataProvider
from app.providers.mock_provider import MockProvider
from app.providers.worldcup_api_provider import WorldCupAPIProvider

logger = get_logger(__name__)

_REGISTRY: dict[str, type[BaseFootballProvider]] = {
    "mock": MockProvider,
    "football_data": FootballDataProvider,
    "api_football": APIFootballProvider,
    "worldcup_api": WorldCupAPIProvider,
}


def get_provider(name: str | None = None) -> BaseFootballProvider:
    """Instancia el proveedor configurado (o el indicado por nombre)."""
    key = (name or settings.football_provider or "mock").lower()
    provider_cls = _REGISTRY.get(key)
    if provider_cls is None:
        logger.warning("Proveedor '%s' desconocido; usando MockProvider", key)
        provider_cls = MockProvider
    logger.info("Usando proveedor de fútbol: %s", provider_cls.name)
    return provider_cls()
