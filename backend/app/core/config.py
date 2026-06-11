"""Configuración central de la aplicación basada en variables de entorno."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parents[2]
_PROJECT_ROOT = _BACKEND_DIR.parent


def resolve_path(value: str) -> Path:
    """Resuelve una ruta relativa probando cwd, raíz del proyecto y backend.

    Permite que la app encuentre /data tanto en desarrollo (cwd=backend) como
    en Docker (cwd=/app).
    """
    raw = Path(value)
    if raw.is_absolute():
        return raw
    for base in (Path.cwd(), _PROJECT_ROOT, _BACKEND_DIR):
        candidate = base / raw
        if candidate.exists():
            return candidate
    return _PROJECT_ROOT / raw


def resolved_database_url(url: str) -> str:
    """Ancla las rutas SQLite relativas a la raíz del proyecto.

    Evita que la base de datos se cree en ubicaciones distintas según el
    directorio de trabajo (backend/ en desarrollo, /app en Docker).
    """
    if url.startswith("sqlite") and ":memory:" not in url:
        raw = url.split(":///", 1)[-1]
        path = Path(raw)
        if not path.is_absolute():
            path = _PROJECT_ROOT / Path(raw.lstrip("./"))
        path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{path.as_posix()}"
    return url


class Settings(BaseSettings):
    """Configuración tipada cargada desde el entorno / archivo .env."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "Mundial 2026 Predictions"
    environment: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # Seguridad
    secret_key: str = "change-me-super-secret-key-please-rotate"
    access_token_expire_minutes: int = 1440
    algorithm: str = "HS256"

    first_admin_email: str = "germandres_91@hotmail.com"
    first_admin_password: str = "Mundial2026!"
    first_admin_name: str = "German Andres Bello Garcia"

    # Permitir auto-registro público de usuarios (solo lectura). Por defecto
    # desactivado: solo el administrador crea cuentas desde el panel.
    allow_public_registration: bool = False

    # Base de datos
    database_url: str = "sqlite:///./data/mundial.db"

    # CORS (lista separada por comas en el .env)
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    # Regex de orígenes permitidos (por defecto cualquier Azure Static Web App)
    cors_origin_regex: str = r"https://.*\.azurestaticapps\.net"

    # Proveedor de fútbol
    football_provider: str = "mock"
    football_api_key: str = ""
    football_api_timeout: int = 15
    football_competition_id: str = "WC"

    # Automatización
    sync_enabled: bool = True
    sync_interval_minutes: int = 5
    # Si es False, la sincronización SOLO actualiza partidos existentes
    # (empareja por equipos); no crea partidos nuevos desde la API externa.
    sync_create_missing: bool = False

    # Excel
    excel_predictions_path: str = "./data/predicciones.xlsx"
    excel_rules_path: str = "./data/reglas_puntaje.xlsx"
    exports_dir: str = "./data/exports"

    @property
    def cors_origins_list(self) -> list[str]:
        """Devuelve los orígenes CORS como lista."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def predictions_file(self) -> Path:
        return resolve_path(self.excel_predictions_path)

    @property
    def rules_file(self) -> Path:
        return resolve_path(self.excel_rules_path)

    @property
    def exports_path(self) -> Path:
        return resolve_path(self.exports_dir)

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """Devuelve una instancia cacheada de la configuración."""
    return Settings()


settings = get_settings()
