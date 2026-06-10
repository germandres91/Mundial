@echo off
REM ===========================================================================
REM  Mundial 2026 - Arranque del FRONTEND (React + Vite)
REM ===========================================================================
setlocal
cd /d "%~dp0\frontend"

if not exist ".env" (
    echo [INFO] Creando .env del frontend a partir de .env.example
    copy ".env.example" ".env" >nul
)

if not exist "node_modules" (
    echo [INFO] Instalando dependencias de Node...
    call npm install
)

echo [INFO] Iniciando servidor de desarrollo en http://localhost:5173
call npm run dev

endlocal
