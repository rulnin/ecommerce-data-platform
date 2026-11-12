# Local setup and verification

[Project overview](../README.md) · [Documentation index](README.md)

For the shortest path, use the [quick start](quickstart.md). This guide includes
additional verification and development commands. See [deployment](deployment.md)
for remote hosting.

Run commands from the repository root.

## Prerequisites and Python environment

Use the Linux filesystem, not `/mnt/c`. Verified host: Ubuntu 26.04.1 WSL2 x86_64,
Docker Engine 29.9.3, Compose v5.7.0 and about 11 GiB WSL RAM. Prerequisites are
Git, working Docker/Compose, the existing Python 3.14.4 and
[uv](https://docs.astral.sh/uv/getting-started/installation/). Do not replace system
Python or install Python 3.12. The old temporary uv installation is not required;
install uv persistently through its official instructions if it is absent.

```bash
git clone https://github.com/rulnin/ecommerce-data-platform.git
cd ecommerce-data-platform
python3.14 --version                 # 3.14.4
uv --version
docker info                         # must work in this WSL session
bash scripts/setup_venv.sh
source .venv/bin/activate
python -m pip install -r requirements-dbt.txt
python -m pip check
```

The setup script preserves/repairs an existing venv, prohibits Python downloads,
and seeds pip. Direct package versions are pinned; transitive dependencies are not
fully locked. [Python compatibility evidence](python-compatibility.md) records
what was tested. Use the commands below to verify your environment; generated verification reports
are local outputs and are excluded from Git.

Create `.env` without overwriting an existing configuration:

```bash
python - <<'PY'
from pathlib import Path
import secrets
p = Path('.env')
if not p.exists():
    with p.open('x') as stream:
        stream.write(Path('.env.example').read_text().replace(
            'POSTGRES_PASSWORD=\n', 'POSTGRES_PASSWORD=' + secrets.token_hex(24) + '\n'))
    p.chmod(0o600)
PY
docker compose config --quiet
docker compose up -d --wait postgres
```

`.env`, `.venv`, native driver files, CSVs and backups are ignored. Environment
variables override `.env`. Ports bind to localhost. Changing `.env` passwords does
not rotate credentials in an initialized database volume. Avoid printing rendered
Compose config or connection URLs. The developer DB role needs CREATEDB for the
disposable integration tests; production RBAC is outside this local demo.

## Load sources and publish

Download the public snapshot, compare its hashes with
[the reviewed manifest](dataset-manifest.json), then load raw data:

```bash
python scripts/download_dataset.py
# If public download is unavailable: use --archive /path/to/downloaded.zip
python scripts/profile_dataset.py --input data/raw --output docs/source-profile.json
python -m src.ingestion.csv_pipeline --batch-id initial-full
python -m src.ingestion.api_ingestion --date 2017-11-25 --batch-id fx-demo
```

The downloader preserves identical files and refuses to overwrite differing ones.
Daily CSV slices are a simulation, not live CDC:

```bash
python -m src.ingestion.csv_pipeline --batch-id day-2017-11-24 \
  --start 2017-11-24 --end 2017-11-25
```

For the synthetic source, configure unique MSSQL_SA_PASSWORD and SQLSERVER_PASSWORD
in local `.env`. Start the source, install the project-local native driver, seed
100 mapped demo products, then ingest its committed outbox:

```bash
python -m pip install -r requirements-sqlserver.txt
bash scripts/setup_odbc.sh
docker compose --profile sqlserver up -d --wait sqlserver
python -m scripts.seed_synthetic_inventory
python -m src.ingestion.sqlserver_ingestion --batch-id stock-demo
```

The native-driver setup is explicitly for this verified Ubuntu 26.04 amd64 host;
see [source setup, credential and platform details](sqlserver-source.md).
Do not reset its source sequence or a target cursor to hide an inconsistency.

For manual development/debugging, build and inspect dbt models with the following
commands. The Airflow workflow below runs publication and analytics automatically:

```bash
python scripts/dbt.py debug
python scripts/dbt.py build
python scripts/dbt.py docs generate
python scripts/dbt.py docs serve --host 127.0.0.1 --port 8081
# In another activated terminal, after stopping docs serve if preferred:
python -m src.quality.publication
python -m scripts.verify_phase9
```

Publication builds candidates, tests every enabled model/test and updates all seven
`published` tables in one transaction. Nonzero exit means publication did not
complete. Consumer queries use `published`, not developer/candidate marts. Review
the report (generated locally) and fix failed source contracts before replay.
The baseline drift gate expects the reviewed full snapshot; loading a small slice
into an otherwise empty warehouse does not satisfy that contract.

## Airflow and failure recovery

After source configuration, `bash scripts/airflow.sh setup` creates missing local
metadata secrets/database, builds the constrained image and starts services.
Open localhost:8080; admin credentials remain in `.env`. The DAG defaults paused,
has a historical date bound, retries and bounded task execution. See the
[Airflow runbook](airflow.md) for manual dates, native backfill and failed-task
clearing. Do not expose the local development service publicly.

The linked screenshots record the original five-task ingestion pipeline. The current
DAG adds `publish` and `analytics`; use a historical logical date when triggering
it, as described in the runbook.

[Successful run](screenshots/phase4-success.png) ·
[Recovered run](screenshots/phase4-recovered.png) ·
Recorded attempts (generated locally)

## Metabase dashboard

```bash
bash scripts/metabase.sh setup
```

Open http://localhost:3000 and sign in with `METABASE_ADMIN_EMAIL` and
`METABASE_ADMIN_PASSWORD` from `.env`. Setup creates the read-only warehouse
connection and an eight-question **E-commerce overview** dashboard; its printed
URL enables five-minute auto-refresh. See [Metabase setup](metabase.md). Metabase accounts/questions
persist in a separate `metabase_app` database on the existing PostgreSQL volume.
Airflow publication updates the data; dashboard refresh reruns its queries.

## Tests and repeatable evidence

```bash
bash scripts/check.sh unit            # no datasets, SQL Server, API or cloud
bash scripts/check.sh integration     # healthy Postgres, disposable test DBs
RUN_DB_TESTS=1 python -m pytest -q     # complete lightweight suite
```

Both CI jobs use these same check scripts for lint, format, compilation and tests.
[Testing scope/style](testing.md) explains dependencies and cleanup. See the workflow in `.github/workflows/ci.yml` for the current CI configuration.

Heavier explicit verification commands are `python -m scripts.verify_phase5`,
`python -m scripts.verify_phase6`, and `python -m scripts.verify_phase8`. They
create disposable databases and may take several minutes; Phase 8 also retains
an ignored warehouse dump. Read their runbooks before invoking them. Phase 2/3
source evidence remains available without repeating completed source mutations.


## Stop services

Stop heavier services with `bash scripts/airflow.sh stop` and
`bash scripts/metabase.sh stop`. `docker compose stop postgres` stops the warehouse
while preserving its volume. Never delete working volumes as a recovery shortcut.
Use `deactivate` to leave the host venv. See the [operations runbook](runbook.md)
for replay and backup/restore.
