#!/bin/bash
# Comando de arranque para Azure App Service (FastAPI / ASGI).
# Configúralo también en Azure → Configuration → General settings → Startup Command.
cd /home/site/wwwroot
gunicorn app.main:app \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --workers 1
