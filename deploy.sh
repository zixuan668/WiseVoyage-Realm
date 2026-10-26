#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
case "${1:-}" in
  base) python -m uvicorn server.base.base_server:app --host 0.0.0.0 --port "${BACKEND_PORT:-18000}" ;;
  frontend) cd frontend; npm run dev ;;
  compose) docker compose up -d --build ;;
  *) echo "Usage: ./deploy.sh {base|frontend|compose}"; exit 1 ;;
esac
