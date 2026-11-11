# E-Commerce Data Platform

A local-first data engineering portfolio integrating historical Olist e-commerce
orders, public exchange rates, and synthetic SQL Server inventory into PostgreSQL.
The business goal is validated order, customer and daily sales analytics without
multiplying item and payment totals. Phase 1 provides reproducible source acquisition,
profiling, contracts and a verified PostgreSQL service. Phase 2 adds transactional
CSV ingestion, simulated date batches, checkpoints and tested recovery.
Phase 3 adds dated ECB FX rates and a synthetic SQL Server stock source with
transactional sequence-based extraction. Phase 4 orchestrates the loaders with
Airflow, retries, operational summaries and recovery checks. Phase 5 adds dbt
staging views, customer/product/seller/date dimensions and separate item/payment
facts with daily sales metrics. Phase 6 validates keys, mappings, counts and financial
totals before transactional publication to consumer tables. Reporting remains later work.

```text
Olist CSVs -> data/raw -> source profiling + contracts
                              |
                              v (Phase 2 onward)
API + synthetic SQL Server -> PostgreSQL raw -> staging -> marts
                                   ^
                           Airflow (implemented) + dbt (implemented)
```

## Setup

Use the Linux filesystem in WSL2. This project uses the existing Python 3.14.4 on
Ubuntu 26.04.1, Docker Engine 29.9.3 and Compose v5.7.0. Tested with approximately
11 GiB WSL RAM and PostgreSQL limited to 1 GiB. Do not replace system Python or
install another interpreter. Airflow dependencies stay in containers.

Install uv following its [official instructions](https://docs.astral.sh/uv/getting-started/installation/).
The verified uv version is 0.13.7. This session's temporary installation is in
`/tmp/ecommerce-uv`; add it to PATH if reusing it. A fresh developer should install
uv persistently using the official instructions. Git and Docker are required.

From a clone of this repository:

```bash
cd ecommerce-data-platform
python3.14 --version  # must be 3.14.4
uv --version
bash scripts/setup_venv.sh
source .venv/bin/activate
which python
python -m pip install -r requirements.txt
python -m pip check
python -m pytest -q
```

`.python-version` pins 3.14.4; `pyproject.toml` permits 3.14.4 through 3.14.x.
The setup script prohibits interpreter downloads, seeds pip and preserves an
existing venv. Requirements files provide direct pins; transitive dependencies
are not fully locked. Use pip inside the activated venv, rather than uv sync.
Install `requirements-dbt.txt` for the dimensional warehouse;
`requirements-compatibility.txt` retains the same dbt pins for compatibility probes.
See [Python compatibility evidence](docs/python-compatibility.md) for limitations.
Exit the shell environment with `deactivate`.

Create local configuration without overwriting an existing file:

```bash
python3 - <<'PYENV'
from pathlib import Path
import secrets
path = Path('.env')
if not path.exists():
    with path.open('x') as stream:
        stream.write(Path('.env.example').read_text().replace(
            'POSTGRES_PASSWORD=\n', 'POSTGRES_PASSWORD=' + secrets.token_hex(24) + '\n'))
    path.chmod(0o600)
PYENV
```

`.env`, `.venv`, datasets and caches are ignored. Never commit credentials or raw
CSV data. If port 5432 is occupied, change POSTGRES_PORT in `.env` before startup.

## PostgreSQL

```bash
docker compose config --quiet
docker compose up -d --wait --wait-timeout 120 postgres
docker compose ps
docker compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT version();"'
```

Verified image: `postgres:17.11-bookworm`; named volume:
`ecommerce-data-platform_postgres_data`; port bound to `127.0.0.1` only. The image
initializes credentials only on an empty volume: changing `.env` does not rotate
an existing database password. Phase 2 loads raw tables; Phase 5 builds analytical marts using dbt.

```bash
docker compose stop postgres  # stop, retaining container and data
docker compose start postgres
docker compose down           # remove containers/network, preserve database volume
```

For troubleshooting: `docker compose logs --tail 100 postgres` and
`docker compose ps`. Avoid printing `docker compose config` without `--quiet`,
which would expose substituted credentials. A fresh reset should use a different
Compose project name and fresh volume, rather than erasing existing data:
`docker compose -p ecommerce-review up -d --wait postgres` after stopping the old
service to free its port. Clean up that review container with the same `-p` name
and `down`; retain its volume until no longer needed. Do not use `down -v` casually.

In this AI session Docker/Git access requires approved execution outside the
sandbox, which maps host groups and masks Git metadata. The normal WSL terminal
works without sudo; do not reinstall Docker or change socket permissions.

## Dataset and source profiling

Phase 2 provides configuration, bounded connection retries and transactional CSV
upserts. See [loading, recovery and evidence](docs/csv-ingestion.md). For a full load:
`python -m src.ingestion.csv_pipeline --batch-id full-olist-v2`.
To inspect a file without loading it:
`python -m src.ingestion.csv_ingestion data/raw/olist_orders_dataset.csv --batch-size 1000`.
The inspection command reports counts only. To simulate one day's arrivals:
`python -m src.ingestion.csv_pipeline --batch-id day-2017-11-24 --start 2017-11-24 --end 2017-11-25`.
Configuration keys and defaults are listed in `.env.example`; process environment
values override `.env`. Connection retries do not replay failed transactions.

Source: [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce),
Kaggle dataset version 2 (publisher metadata: updated 2021-10-01). Publisher lists
CC BY-NC-SA 4.0. Attribute Olist and observe its noncommercial/share-alike terms
when reusing or distributing data; this repository includes aggregate profiles,
not CSV contents. Inventory in later phases will be explicitly synthetic.

```bash
source .venv/bin/activate
python scripts/download_dataset.py
python scripts/profile_dataset.py --input data/raw --output docs/source-profile.json
python -m pytest -q
```

The downloader uses the public Kaggle archive endpoint, bounded timeouts, retries
and size limits. It verifies all nine fixed filenames before extraction, preserves
identical existing CSVs and refuses to overwrite differing ones. Its local manifest
is `data/dataset-manifest.json`. If access requires an account or the endpoint changes,
download the ZIP yourself from the publisher page and use:
`python scripts/download_dataset.py --archive /path/to/archive.zip`.
No credentials are logged or stored by this script. This URL is not an immutable
snapshot: compare hashes with [the verified manifest](docs/dataset-manifest.json).

## Phase 3 external sources

Frankfurter v2 supplies explicitly dated ECB USD/BRL reference rates. Weekend
requests retain the earlier returned observation date. The client caches by
requested date, upserts by actual rate date and supports explicit refresh:

```bash
source .venv/bin/activate
python -m src.ingestion.api_ingestion --date 2017-11-25 --batch-id fx-2017-11-25
```

See [FX schema, coverage probes and conversion direction](docs/fx-contract.md).
SQL Server is an optional Compose profile with a named volume and localhost-only
port. Follow [synthetic source setup and recovery](docs/sqlserver-source.md) to
generate local credentials, install the project-local WSL ODBC runtime and seed
100 valid product IDs. Inventory is simulated and must not be represented as Olist
stock. The pinned pyodbc dependency is separate from system/ODBC libraries.

```bash
docker compose --profile sqlserver up -d --wait --wait-timeout 240 sqlserver
python -m scripts.seed_synthetic_inventory
python -m src.ingestion.sqlserver_ingestion --batch-id stock-initial
python -m scripts.verify_phase3
docker compose --profile sqlserver stop sqlserver
```

Run the setup steps in the linked guide before those commands. The verification
script deliberately changes synthetic rows to prove same-timestamp updates,
tombstones and rollback/recovery; it preserves the initial full-load evidence.
metadata.external_runs and metadata.external_checkpoints expose auditable external
attempts separately from the Phase 2 CSV run records. Data and checkpoints commit
together. [Phase 3 evidence](docs/phase3-evidence.json) records independent loads of
all three sources. Stop SQL Server when idle to reduce local memory use.

## Phase 4 orchestration

```bash
bash scripts/airflow.sh setup
bash scripts/airflow.sh status
```

Open http://localhost:8080 with username admin and the generated
AIRFLOW_ADMIN_PASSWORD from ignored .env. The DAG starts paused. Read the
[Airflow runbook](docs/airflow.md) before triggering, backfilling or simulating a
failure. It uses LocalExecutor and isolated constrained container dependencies;
the host venv is unchanged. The daily operational summary keeps items and payments
at separate grains. This is not the Phase 5 dimensional warehouse.

[Runtime proof](docs/airflow-runtime.json), [DAG/recovery evidence](docs/phase4-evidence.json)
and [UI captures](docs/screenshots/phase4-recovered.png) record the tested deployment.
`bash scripts/airflow.sh stop` stops Airflow and SQL Server while preserving data.

## Source profile and verification

The profile includes SHA-256, columns, counts, empty fields, candidate keys, exact
row duplicates and distinct nonempty relationship violations. It fails on missing
files or malformed CSV structure; data findings are reported diagnostically and do
not cause a failing exit status. Raw strings are retained; SQL types and final
review/geolocation key decisions belong to ingestion design.

Measured results include 99,441 orders, 112,650 items and 103,886 payments;
261,831 exact geolocation duplicates; 814 repeated review IDs without exact review
row duplicates; two untranslated product categories. Item and payment grains stay
separate. See [source contracts](docs/data-contracts.md), [profiling notes](docs/source-profiling.md),
[environment evidence](docs/environment.md), and [task tracker](ECOMMERCE_DATA_PLATFORM_TASKS.md).

`make profile` and `make verify` are optional shortcuts if make is installed;
the Python commands above are the verified path. Use `RUN_DB_TESTS=1 python -m pytest -q`
for disposable-database tests and `python -m scripts.verify_phase2` for real-data
rerun/recovery verification. Phase 1–6 evidence is in the tracker.
CI and performance benchmarking remain later-phase work.

## dbt warehouse (Phase 5)

```bash
source .venv/bin/activate
python -m pip install -r requirements-dbt.txt
python scripts/dbt.py debug
python scripts/dbt.py build
python scripts/dbt.py docs generate
python scripts/dbt.py docs serve --host 127.0.0.1 --port 8081
# Repeatable live + disposable-database validation:
python -m scripts.verify_phase5
```

The wrapper loads local `.env`; profiles contain environment references only.
Twenty models cover thirteen raw-source staging views, four dimensions and three
facts. Items and payments retain separate grains and aggregate independently.
Only the item fact is incremental; changed parent attributes are detected too.
USD measures remain null for days without a stored ECB observation within seven
days. Airflow still runs its Phase 4 operational summary; dbt runs explicitly.
See [warehouse grains, financial rules, targets and rebuild runbook](docs/dbt-warehouse.md)
and [executed Phase 5 evidence](docs/phase5-evidence.json). Generated dbt docs stay
local under ignored `dbt/target/`.

## Quality and publication (Phase 6)

```bash
source .venv/bin/activate
python -m src.quality.publication
# Exercises bad-input rejection and recovery in a disposable database:
python -m scripts.verify_phase6
```

Read validated consumer tables from `published`, rather than developer `marts`
or `candidate_marts`. Publication requires every dbt test and model to succeed;
failures leave the previous publication intact and return a nonzero exit status.
`docs/quality-report.json` records per-check expected/actual violations and failing
keys; `metadata.quality_runs` retains attempts. `revenue_brl` is delivered-order
item value excluding freight, refunds and fees, separate from payment amounts.
See [quality rules, count baseline and recovery protocol](docs/data-quality.md)
and [Phase 6 execution evidence](docs/phase6-evidence.json). Airflow publication
integration remains explicit future work; the Phase 4 DAG is unchanged.

## Automated checks (Phase 7)

```bash
bash scripts/check.sh unit
docker compose up -d --wait postgres
bash scripts/check.sh integration
```

These are the same check commands used in GitHub Actions. The unit job needs no
source data or external credentials; integration tests use disposable PostgreSQL
databases. See [test scope, setup and coding standards](docs/testing.md). Hosted
CI verification status is recorded in [Phase 7 evidence](docs/phase7-evidence.json)
and the task tracker; local validation alone does not establish hosted success.
