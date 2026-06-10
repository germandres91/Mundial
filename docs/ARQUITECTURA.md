# Documentación Técnica — Arquitectura

## 1. Visión general

La plataforma se compone de dos aplicaciones desacopladas:

- **Backend**: API REST en FastAPI con arquitectura por capas.
- **Frontend**: SPA en React que consume la API.

La comunicación es HTTP/JSON. El frontend usa React Query para *caching* y
refresco automático; el backend expone OpenAPI en `/docs`.

## 2. Capas del backend

```
api/         → Adaptadores HTTP (routers, validación, auth). Sin lógica de negocio.
services/    → Lógica de negocio (puntaje, ranking, sync, excel, export, auth).
repositories/→ Acceso a datos. Encapsula todas las consultas SQLAlchemy.
models/      → Entidades ORM (tablas).
schemas/     → Contratos de entrada/salida (Pydantic).
core/        → Configuración, base de datos, seguridad, logging.
providers/   → Integración con APIs externas de fútbol (patrón Strategy).
jobs/        → Tareas programadas (APScheduler).
```

**Regla de dependencia**: una capa solo puede depender de la inmediatamente
inferior. Los routers nunca acceden directo al ORM; lo hacen vía servicios y
repositorios.

## 3. Modelo de datos

| Tabla           | Descripción                                            |
| --------------- | ------------------------------------------------------ |
| `participants`  | Concursantes (`nombre`, `email`, `fecha_creacion`).    |
| `matches`       | Partidos (`fifa_id`, `grupo`, `fase`, marcador, estado).|
| `predictions`   | Predicción de un participante para un partido (única).  |
| `scores`        | Puntos obtenidos por predicción evaluada.              |
| `rankings`      | Agregado por participante (`puntos_totales`, `posicion`).|
| `scoring_rules` | Reglas de puntaje configurables (importadas de Excel). |
| `users`         | Autenticación (rol ADMIN/PARTICIPANT).                 |
| `audit_logs`    | Registro de acciones del sistema.                      |

Restricciones de unicidad evitan predicciones/puntajes duplicados por
`(participant_id, match_id)`. Las migraciones viven en `backend/alembic/`.

## 4. Proveedores de fútbol (Strategy)

`BaseFootballProvider` define el contrato `fetch_matches()` que devuelve una
lista normalizada de `ProviderMatch`. La fábrica `get_provider()` selecciona la
implementación según `FOOTBALL_PROVIDER`:

| Valor           | Clase                    | Fuente                      |
| --------------- | ------------------------ | --------------------------- |
| `mock`          | `MockProvider`           | JSON local (sin red)        |
| `football_data` | `FootballDataProvider`   | football-data.org           |
| `api_football`  | `APIFootballProvider`    | API-FOOTBALL (api-sports)   |
| `worldcup_api`  | `WorldCupAPIProvider`    | API REST genérica           |

Añadir un proveedor nuevo = crear una clase que herede de `BaseFootballProvider`
y registrarla en `providers/factory.py`.

## 5. Flujo de cálculo de puntaje

```
Partido FINALIZADO
   ↓
ScoringService.score_match()   → evalúa cada predicción vs resultado real
   ↓                              aplica reglas (EXACT, WINNER_GOALS, ...)
Persiste Score por participante
   ↓
RankingService.recalculate()   → agrega puntos, ordena, asigna posiciones
   ↓
Ranking actualizado
```

## 6. Automatización

`jobs/scheduler.py` registra un `BackgroundScheduler` que ejecuta
`SyncService.sync()` cada `SYNC_INTERVAL_MINUTES`:

1. Consulta el proveedor de fútbol.
2. Actualiza partidos y detecta los recién finalizados.
3. Calcula puntajes de los nuevos finalizados.
4. Recalcula el ranking.
5. Registra el evento en auditoría.

El frontend refresca automáticamente vía `refetchInterval` de React Query.

## 7. Seguridad

- Contraseñas con **bcrypt** (`passlib`).
- **JWT** firmados (HS256) con expiración configurable.
- Autorización por rol mediante dependencias FastAPI (`require_admin`).
- Validación estricta de entrada con Pydantic v2.
- Variables sensibles en `.env` (nunca en el repositorio).
- Manejo global de errores + logging rotativo en `logs/`.

## 8. Testing

- **Unitarias**: `ScoringService`, `RankingService`, proveedores.
- **Integración**: `SyncService`, `ExcelService` con base de datos real.
- **API**: endpoints completos con `TestClient` y JWT.

Cobertura mínima forzada al 80% (`--cov-fail-under=80`); actual 87%.
