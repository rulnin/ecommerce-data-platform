#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
compose=(docker compose -f docker-compose.yml -f docker-compose.airflow.yml --profile airflow --profile sqlserver)
case "${1:-status}" in
  setup)
    "${compose[@]}" up -d --wait --wait-timeout 240 postgres sqlserver
    .venv/bin/python -m scripts.init_airflow_db
    "${compose[@]}" build airflow-init
    "${compose[@]}" run --rm airflow-init
    "${compose[@]}" up -d --wait --wait-timeout 240 airflow-api airflow-scheduler airflow-dag-processor
    ;;
  start)
    "${compose[@]}" up -d --wait --wait-timeout 240 postgres sqlserver airflow-api airflow-scheduler airflow-dag-processor
    ;;
  stop)
    "${compose[@]}" stop airflow-api airflow-scheduler airflow-dag-processor sqlserver
    ;;
  status) "${compose[@]}" ps -a ;;
  logs) "${compose[@]}" logs --tail 100 "${@:2}" ;;
  *) echo 'Usage: bash scripts/airflow.sh setup|start|stop|status|logs [service]' >&2; exit 2 ;;
esac
