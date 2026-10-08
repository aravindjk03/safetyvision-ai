#!/usr/bin/env bash
# SafetyVision AI — Linux / macOS launcher
#   ./run.sh            start the Streamlit dashboard (http://localhost:8501)
#   ./run.sh api        start the FastAPI service      (http://localhost:8080/docs)
#   ./run.sh all        start both
set -euo pipefail
cd "$(dirname "$0")"

if [ -d .venv ]; then source .venv/bin/activate; elif [ -d venv ]; then source venv/bin/activate; fi

start_dashboard() { streamlit run app/main.py --server.port "${PORT:-8501}" --server.address 0.0.0.0; }
start_api() { python -m uvicorn app.api:app --host 0.0.0.0 --port "${API_PORT:-8080}"; }

case "${1:-dashboard}" in
  dashboard) start_dashboard ;;
  api) start_api ;;
  all) start_api & trap 'kill $!' EXIT; start_dashboard ;;
  *) echo "Usage: $0 [dashboard|api|all]"; exit 1 ;;
esac
