# 🌍 Mundial 2026 · Plataforma de Predicciones

Plataforma profesional para la gestión de un concurso de predicciones de la
**Copa del Mundo 2026**. Consume resultados oficiales en tiempo real desde una
API de fútbol, compara automáticamente los marcadores reales contra las
predicciones almacenadas en Excel, calcula puntajes según las reglas del
concurso y los muestra en dashboards modernos.

![estado](https://img.shields.io/badge/tests-39%20passing-brightgreen)
![cobertura](https://img.shields.io/badge/cobertura-88%25-brightgreen)
![python](https://img.shields.io/badge/python-3.13-blue)
![react](https://img.shields.io/badge/react-18-61dafb)

---

## ✨ Características

- **Pantalla "Inicio Mundial"**: diagrama de flujo del torneo (12 grupos →
  eliminatorias → campeón) que se llena con las posiciones pronosticadas y se
  actualiza con los resultados reales.
- **Modo single-user (sin login)**: la app abre directamente; tú agregas los
  participantes que quieras.
- **Carga de participantes desde Excel**: sube un formulario (mismo formato del
  archivo de apuestas) y se importan automáticamente las 72 predicciones de
  fase de grupos + el pronóstico de los 4 primeros puestos.
- **Resultados en tiempo real** desde proveedores de fútbol intercambiables.
- **Motor de puntaje** configurable (marcador exacto, ganador + goles, etc.).
- **Ranking automático** recalculado al finalizar cada partido.
- **Automatización** cada 5 minutos vía APScheduler.
- **Dashboards y gráficas** (Recharts): evolución, puntos, aciertos, fases.
- **Exportación** a Excel (ranking, resultados, predicciones) y PDF.
- **Auditoría** de acciones del sistema.
- **Dark Mode**, diseño responsive, skeleton loading y toasts.
- **Docker Compose**, scripts `.bat` y CI con GitHub Actions.

---

## 🏗️ Arquitectura

```
Frontend (React + Vite + Tailwind)
        │  HTTP / Axios + React Query
        ▼
API Gateway (FastAPI)
        ▼
Services (lógica de negocio)
        ▼
Repositories (acceso a datos)
        ▼
Database (SQLite dev / PostgreSQL prod)
```

El backend sigue una **arquitectura por capas** estricta. La integración con
APIs externas usa el patrón *Strategy* mediante `BaseFootballProvider` con
cuatro implementaciones (`mock`, `football_data`, `api_football`, `worldcup_api`).

Consulta [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md) y
[`docs/API.md`](docs/API.md) para el detalle técnico.

---

## 🛠️ Stack Tecnológico

| Capa            | Tecnologías                                                              |
| --------------- | ----------------------------------------------------------------------- |
| Backend         | Python 3.12, FastAPI, SQLAlchemy 2, Pydantic v2, APScheduler, Pandas, OpenPyXL, ReportLab, Alembic |
| Base de datos   | SQLite (desarrollo) · PostgreSQL (producción)                           |
| Frontend        | React 18, Vite, TailwindCSS, React Query, React Router, Axios, Recharts |
| Infraestructura | Docker, Docker Compose, GitHub Actions, variables `.env`                |

---

## 🚀 Inicio rápido

### Opción A — Scripts `.bat` (Windows)

```bat
:: Levanta backend + frontend en ventanas separadas
start_all.bat
```

Cada script crea el entorno virtual, instala dependencias, ejecuta migraciones,
inicializa la base de datos con datos de ejemplo e inicia el servidor.

- `start_backend.bat` → API en http://localhost:8000 (Swagger en `/docs`)
- `start_frontend.bat` → UI en http://localhost:5173

### Opción B — Manual

**Backend**

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # En Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python ../scripts/seed_data.py    # datos de ejemplo (opcional)
uvicorn app.main:app --reload
```

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

### Opción C — Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- PostgreSQL: localhost:5432

---

## 👤 Acceso y participantes

La aplicación funciona en **modo single-user**: no requiere iniciar sesión, se
abre directamente en la pantalla **Inicio Mundial**.

- Al sembrar la base de datos se carga el participante **German Bello** con todas
  sus predicciones desde `data/formulario_german_bello.xlsm`.
- Para añadir más participantes, ve a **Participantes → Agregar participante** y
  sube su formulario Excel (`.xlsm`/`.xlsx`) con el mismo formato. Hay una
  plantilla en `data/plantilla_formulario.xlsm`.

> La autenticación JWT sigue disponible en el backend (`/api/v1/auth/*`) por si
> se necesita reactivar el control de acceso en producción.

---

## ⚙️ Configuración (`.env`)

| Variable                 | Descripción                                              | Default        |
| ------------------------ | -------------------------------------------------------- | -------------- |
| `FOOTBALL_PROVIDER`      | `mock`, `football_data`, `api_football`, `worldcup_api`  | `mock`         |
| `FOOTBALL_API_KEY`       | Clave de la API de fútbol elegida                        | —              |
| `DATABASE_URL`           | Cadena de conexión SQLAlchemy                            | SQLite local   |
| `SYNC_ENABLED`           | Activa la sincronización automática                      | `true`         |
| `SYNC_INTERVAL_MINUTES`  | Frecuencia del job de sincronización                     | `5`            |
| `SECRET_KEY`             | Clave para firmar los JWT                                 | (cambiar)      |
| `EXCEL_PREDICTIONS_PATH` | Ruta del Excel de predicciones                           | `./data/...`   |

Ver `.env.example` para la lista completa.

---

## 🧮 Reglas de puntaje

Importadas automáticamente desde Excel (`data/reglas_puntaje.xlsx`). Por defecto:

| Acierto                         | Código         | Puntos |
| ------------------------------- | -------------- | ------ |
| Marcador exacto                 | `EXACT`        | 5      |
| Ganador + goles del ganador     | `WINNER_GOALS` | 3      |
| Ganador correcto                | `WINNER`       | 2      |
| Empate correcto                 | `DRAW`         | 1      |
| Sin acierto                     | `NONE`         | 0      |

Editables desde el panel de **Administración** o el Excel.

---

## 📥 Importar predicciones desde Excel

Formato esperado de `data/predicciones.xlsx`:

| nombre | email | fifa_id | local | visitante | pred_local | pred_visitante |
| ------ | ----- | ------- | ----- | --------- | ---------- | -------------- |

Genera archivos de ejemplo con:

```bash
python scripts/generate_sample_data.py
```

---

## 🧪 Testing

```bash
cd backend
pytest                 # ejecuta tests con cobertura (mínimo 80%)
ruff check app         # linter
```

```bash
cd frontend
npm run lint           # linter
npm run build          # build de producción
```

Cobertura actual: **87%** · 35 pruebas (unitarias, integración y API).

---

## 📂 Estructura del proyecto

```
Mundial/
├── backend/
│   ├── app/
│   │   ├── api/          # Routers FastAPI + dependencias
│   │   ├── core/         # config, database, security, logging
│   │   ├── models/       # Modelos SQLAlchemy
│   │   ├── schemas/      # Esquemas Pydantic
│   │   ├── repositories/ # Acceso a datos
│   │   ├── services/     # Lógica de negocio
│   │   ├── providers/    # Proveedores de fútbol (Strategy)
│   │   └── jobs/         # APScheduler
│   ├── alembic/          # Migraciones
│   └── tests/            # Pytest
├── frontend/
│   └── src/
│       ├── components/   # UI reutilizable + charts
│       ├── pages/        # Pantallas
│       ├── layouts/      # Layout principal
│       ├── services/     # Cliente Axios
│       ├── hooks/        # React Query
│       ├── context/      # Auth, Theme, Toast
│       └── types/        # JSDoc typedefs
├── data/                 # Datos de ejemplo y exports
├── scripts/              # Seed + generación de Excel
├── docs/                 # Documentación técnica
├── docker-compose.yml
├── start_*.bat
└── README.md
```

---

## 📜 Licencia

MIT. Uso libre para fines educativos y profesionales.
