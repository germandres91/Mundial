@echo off
REM ===========================================================================
REM  Mundial 2026 - Arranque del BACKEND (FastAPI)
REM  Crea el entorno virtual, instala dependencias, migra e inicia el servidor.
REM ===========================================================================
setlocal
cd /d "%~dp0"

if not exist ".env" (
    echo [INFO] Creando .env a partir de .env.example
    copy ".env.example" ".env" >nul
)

cd backend

if not exist ".venv" (
    echo [INFO] Creando entorno virtual...
    python -m venv .venv
)

echo [INFO] Activando entorno virtual...
call ".venv\Scripts\activate.bat"

echo [INFO] Instalando dependencias...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt

echo [INFO] Ejecutando migraciones (Alembic)...
alembic upgrade head

echo [INFO] Inicializando base de datos con datos de ejemplo...
python ..\scripts\seed_data.py

echo [INFO] Iniciando servidor en http://localhost:8000 (docs en /docs)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

endlocal
