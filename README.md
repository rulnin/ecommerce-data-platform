# E-Commerce Data Platform

A local-first data engineering portfolio integrating historical Olist e-commerce
orders, public exchange rates, and synthetic SQL Server inventory into PostgreSQL.
The business goal is validated order, customer and daily sales analytics without
multiplying item and payment totals. Phase 1 provides reproducible source acquisition,
profiling, contracts and a verified PostgreSQL service. Ingestion, Airflow orchestration,
dbt models and reporting belong to subsequent phases and are not implemented yet.

```text
Olist CSVs -> data/raw -> source profiling + contracts
                              |
                              v (Phase 2 onward)
API + synthetic SQL Server -> PostgreSQL raw -> staging -> marts
                                   ^
                           Airflow + dbt (later phases)
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
The optional `requirements-compatibility.txt` reproduces the tested dbt pair;
install it only when checking compatibility or starting the dbt phase.
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
an existing database password. No analytical tables are loaded in Phase 1.

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
the Python commands above are the verified path. Phase 1 evidence is in the tracker;
no CI success, pipeline load, warehouse metrics or performance benchmarks are claimed.
