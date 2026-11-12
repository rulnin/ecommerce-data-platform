#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
compose=(docker compose -f docker-compose.yml -f docker-compose.metabase.yml --profile metabase)
case "${1:-status}" in
  setup)
    # The base file can start Postgres before Metabase secrets exist.
    docker compose up -d --wait postgres
    .venv/bin/python -m scripts.init_metabase_db
    "${compose[@]}" up -d --wait --wait-timeout 360 metabase
    .venv/bin/python -m scripts.setup_metabase
    ;;
  start) "${compose[@]}" up -d --wait --wait-timeout 360 metabase ;;
  stop) "${compose[@]}" stop metabase ;;
  status) "${compose[@]}" ps -a ;;
  logs) "${compose[@]}" logs --tail 100 metabase ;;
  *) echo 'Usage: bash scripts/metabase.sh setup|start|stop|status|logs' >&2; exit 2 ;;
esac
