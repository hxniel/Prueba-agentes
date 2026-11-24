#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

PYTHON="${PYTHON:-/opt/homebrew/bin/python3.12}"
if [ ! -x "$PYTHON" ]; then
  PYTHON="python3.12"
fi

if [ ! -d .venv ]; then
  echo "Creando entorno virtual en .venv..."
  "$PYTHON" -m venv .venv
  .venv/bin/pip install --upgrade pip
  .venv/bin/pip install -r requirements.txt
fi

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Se creó .env a partir de .env.example."
  echo "Pega tu GOOGLE_API_KEY en .env y vuelve a ejecutar ./iniciar.sh"
  exit 1
fi

.venv/bin/python scripts/inicializar_bd.py
exec .venv/bin/uvicorn app.main:app --port 8000
