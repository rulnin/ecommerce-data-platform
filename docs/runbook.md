# Operations, recovery and backup

Operate from the repository root in WSL using the existing Python 3.14.4 `.venv`.
Credentials stay in ignored `.env`; do not print Compose's fully rendered config
or log connection URLs. Use `docker compose config --quiet` for validation.

## Start, inspect and stop

```bash
source .venv/bin/activate
docker compose up -d --wait postgres
docker compose ps
docker stats --no-stream
# Optional source when extracting inventory:
docker compose --profile sqlserver up -d --wait sqlserver
# Configured Airflow runtime (heavier; includes SQL Server):
bash scripts/airflow.sh start
bash scripts/airflow.sh status
# Release heavier services while retaining PostgreSQL and every named volume:
bash scripts/airflow.sh stop
# Stop PostgreSQL when all work has finished:
docker compose stop postgres
```

Never use `docker compose down -v`, prune volumes, delete `.env`, or reinstall
Docker to recover a failed job. The named PostgreSQL, SQL Server and Airflow-log
volumes retain state across container restarts. Changing an existing `.env`
password does not rotate credentials already initialized inside a DB volume.

## Observe a run

Use ingestion run IDs in logs and metadata. `metadata.ingestion_runs` contains
CSV mode/status/timestamps/counts/fingerprints/error code;
`metadata.checkpoints` contains nonregressing source watermarks;
`metadata.rejections` contains sanitized record/field/error details.
`metadata.external_runs` and external_checkpoints track FX/stock independently.
`metadata.orchestration_steps` ties Airflow run/task/attempts to source UUIDs.
`metadata.quality_runs` records failed/published quality attempts.

```sql
SELECT run_id, batch_id, mode, status, started_at, finished_at,
       extract(epoch FROM finished_at-started_at) AS duration_seconds,
       error_code, counts
FROM metadata.ingestion_runs ORDER BY started_at DESC LIMIT 20;
SELECT source, status, count(*) AS attempts
FROM metadata.external_runs GROUP BY source, status;
SELECT run_id, source, record_number, field, error_code
FROM metadata.rejections ORDER BY reported_at DESC LIMIT 20;
SELECT source, watermark FROM metadata.external_checkpoints;
SELECT run_id, status, started_at, finished_at
FROM metadata.quality_runs ORDER BY started_at DESC LIMIT 20;
```

Inspect database activity/resource limits before increasing concurrency. Logs can
contain public identifiers; restrict local access, bound retention and do not
export secrets or raw row payloads. Compose limits Docker logs to three 10 MB
files per service. Phase 8's sanitized CSV run logs and audit durations are saved
in docs/performance and docs/phase8-evidence.json. Database duration includes the
transactional loader work; caller wall time also includes connection/cleanup.
Neither metric includes source CSV download time.

## Failed ingestion, replay and backfill

1. Locate the failed run ID and safe error code. Check rejects and source
   availability. A failed whole CSV batch rolls back target rows/checkpoints;
   a failed stock batch rolls back target changes and its sequence cursor.
2. Correct the input or restore source availability. Preserve reviewed CSV
   fingerprints; never edit the sole original snapshot just to make a run pass.
3. Replay the same source batch/date. Upserts preserve business keys, and completed
   unchanged references can be skipped. Historical CSV slices simulate arrivals;
   they still scan/have hash costs and are not live CDC.

```bash
python -m src.ingestion.csv_pipeline --batch-id recovered-day \
  --start 2017-11-24 --end 2017-11-25
# End is exclusive. Full initial load or deliberate full replay:
python -m src.ingestion.csv_pipeline --batch-id full-replay
```

For FX, first inspect the requested/actual observation dates. Weekend fallback is
normal; stale/missing data is not. Cached requests do not require a network call;
explicit refresh is a correction, not automatic substitution of today's rate.
For stock, never reset the target cursor to work around source sequence reset or
missing outbox events. Restore a compatible source/target pair and investigate
retention. Tombstones and identical timestamps are handled by committed sequence,
not timestamp ordering. See the source-specific runbooks.

For Airflow, retain the historical end bound and paused defaults. Clear only the
failed tasks after fixing the cause; retry does not roll back previously committed
source tasks. Native backfill and recovery examples are in docs/airflow.md. A
stale running ingestion audit after a killed process is not proof of success;
inspect actual committed checkpoints before replay. Do not silently rewrite audit
history to manufacture success.

## Quality/publication failure

Airflow runs publication after operational checks. For manual recovery, run
`python -m src.quality.publication` after ingestion is idle. Nonzero status
means publication did not complete. Read docs/quality-report.json and the
metadata audit, fix the relevant source contract, then rerun. Read consumer data
from `published`, not `marts` or `candidate_marts`. Candidates may be incomplete;
known invalid candidates must never be copied manually into published tables.
See docs/data-quality.md for count baselines, source locks and revenue semantics.

## Warehouse backup and verified restore

Backups contain public source records and operational metadata. They are local
artifacts under ignored data/backups, with restrictive permissions. They are not
committed. A database dump is not a backup of `.env`, PostgreSQL roles, Airflow's
separate metadata database or SQL Server. Preserve secrets separately in an
appropriate private backup; loss of required encryption keys may prevent metadata
recovery. Local disk backups do not protect against host/disk loss.

With PostgreSQL healthy, create a unique dump without overwriting an old file:

```bash
umask 077
mkdir -p data/backups
backup_path="data/backups/warehouse-$(date -u +%Y%m%dT%H%M%SZ).dump"
(set -o noclobber; docker compose exec -T postgres sh -c \
  'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --no-owner --no-privileges' \
  > "$backup_path")
# Inspect the archive before restoring:
docker compose exec -T postgres pg_restore --list < "$backup_path"
```

Restore into a NEW database for review. Choose a fresh name; createdb must fail
if it already exists. Never pass --clean against the working warehouse:

```bash
docker compose exec -T postgres sh -c \
  'createdb -U "$POSTGRES_USER" restore_review'
docker compose exec -T postgres sh -c \
  'pg_restore -U "$POSTGRES_USER" --dbname restore_review --no-owner --no-privileges --exit-on-error' \
  < "$backup_path"
```

Use the same PostgreSQL major/client version (17 here), confirm all table counts
and logical content hashes, test representative queries, and only plan a cutover
after review. Do not overwrite the live DB or remove its volume as a restore test.
The Phase 8 verifier actually dumped the existing warehouse, restored a uniquely
named database, compared every user table's row count and order-independent row
hash, rechecked the original, then dropped only that disposable restored DB.
Backup size/hash and dump/restore duration are in docs/phase8-evidence.json.
The ignored dump is retained locally; no automatic retention deletion runs.

Airflow metadata (`airflow_meta`) needs a separate pg_dump plus retained Fernet/
JWT/admin configuration and log volume if historical logs are needed. SQL Server
needs its own native database backup and compatible outbox/counter history;
its named volume is persistence, not an independent backup. Those separate
backup/restores were not tested by the warehouse restore exercise. Do not claim
the warehouse dump restores those services. For full disaster recovery, coordinate
source sequence/cursor consistency before resuming stock extraction.

## Resource envelope and measured performance

The Compose limits are PostgreSQL 1 GiB, SQL Server 3 GiB (SQL memory 2048 MiB),
and Airflow API/scheduler/DAG processor 1/2/1 GiB, plus host/cache overhead. Keep
SQL Server/Airflow stopped during standalone CSV/dbt benchmarking. Peak Python
RSS and sampled Docker memory are different measures, and samples are not peak
container utilization. WSL memory and CPU availability influence results.

Use `python -m scripts.verify_phase8` with the unchanged reviewed Olist snapshot,
PostgreSQL running, and other loaders idle. The script requires CREATEDB and Docker
client access, uses two disposable databases sequentially, and retains one ignored
warehouse dump. It records the exact dataset hashes/settings and distinguishes
empty-target full load, existing-target full replays and incremental day replays.
Only additive measured-useful lookup indexes are applied to the persistent raw
schema. It does not reset production caches, change server memory, or claim a
network/SQL Server/Airflow end-to-end performance number.

## Metabase operations

See [Metabase](metabase.md) for startup, warehouse connection and refresh settings.
Back up `metabase_app` separately using the existing PostgreSQL backup procedure
with that database name. Preserve `METABASE_ENCRYPTION_SECRET_KEY` with credentials.
Airflow-generated quality/analytics reports live in `airflow_reports`; inspect them
inside the scheduler container as described in [Airflow](airflow.md).
