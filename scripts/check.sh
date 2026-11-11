#!/usr/bin/env bash
# Same checks in WSL and GitHub Actions. No external API or raw dataset required.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
PYTHON="${PYTHON:-.venv/bin/python}"
"$PYTHON" -m ruff check src scripts tests airflow/dags
"$PYTHON" -m ruff format --check src scripts tests airflow/dags
"$PYTHON" -m compileall -q src scripts tests airflow/dags
case "${1:-unit}" in
  unit) "$PYTHON" -m pytest -q tests/unit ;;
  integration) RUN_DB_TESTS=1 "$PYTHON" -m pytest -q tests/integration ;;
  *) echo 'Usage: bash scripts/check.sh [unit|integration]' >&2; exit 2 ;;
esac
