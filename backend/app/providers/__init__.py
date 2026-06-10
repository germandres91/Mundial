"""Proveedores de datos de fútbol."""
from app.providers.base import BaseFootballProvider, ProviderMatch
from app.providers.factory import get_provider

__all__ = ["BaseFootballProvider", "ProviderMatch", "get_provider"]
