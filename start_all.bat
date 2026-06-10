@echo off
REM ===========================================================================
REM  Mundial 2026 - Arranque COMPLETO (backend + frontend en ventanas aparte)
REM ===========================================================================
cd /d "%~dp0"

echo [INFO] Lanzando backend en una nueva ventana...
start "Mundial 2026 - Backend" cmd /k "%~dp0start_backend.bat"

echo [INFO] Esperando a que el backend levante...
timeout /t 8 /nobreak >nul

echo [INFO] Lanzando frontend en una nueva ventana...
start "Mundial 2026 - Frontend" cmd /k "%~dp0start_frontend.bat"

echo.
echo  Backend:  http://localhost:8000  (Swagger: /docs)
echo  Frontend: http://localhost:5173
echo.
echo  Cierra esta ventana cuando termines.
pause
