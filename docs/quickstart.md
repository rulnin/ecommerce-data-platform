# Quick start

[Overview](../README.md) · [Troubleshooting and detailed setup](setup.md)

Run every command from the repository root in an Ubuntu/WSL terminal. On WSL,
keep the checkout in the Linux filesystem, such as `~/projects`, rather than `/mnt/c`.

## 1. Check prerequisites

The setup scripts require **Ubuntu 26.04 x86_64**, **Python 3.14.4**, uv, and
working Docker Compose. The recorded full-stack host had about 11 GiB RAM.
Other operating systems and Python versions need adaptation and are not verified.

```bash
python3.14 --version
uv --version
docker compose version
docker info
```

Stop here if a command fails. Install missing prerequisites before continuing.

## 2. Prepare Python and passwords

```bash
bash scripts/setup_venv.sh
source .venv/bin/activate
python -m pip install -r requirements-dbt.txt -r requirements-sqlserver.txt
cp -n .env.example .env
chmod 600 .env
```

Open `.env` in your editor. Fill in these three blank values with different,
long passwords. For SQL Server, include uppercase and lowercase letters,
numbers, and symbols.

```dotenv
POSTGRES_USER=ecommerce
POSTGRES_DB=ecommerce
POSTGRES_PASSWORD=replace_with_your_postgres_password
MSSQL_SA_PASSWORD=replace_with_your_sqlserver_admin_password
SQLSERVER_PASSWORD=replace_with_your_inventory_reader_password
```

Keep the other defaults. Airflow and Metabase setup generate their own missing
credentials later. Never commit `.env`.

On the first database startup, PostgreSQL creates `POSTGRES_USER` and
`POSTGRES_DB`; SQL Server initializes its `sa` login. The inventory seed command
in step 4 creates the source reader `inventory_reader`.

**Already started these databases?** Preserve the original credentials.
Changing `.env` does not change passwords in existing database volumes.

## 3. Start PostgreSQL and load the historical snapshot

```bash
docker compose config --quiet
docker compose up -d --wait postgres
python scripts/download_dataset.py
python -m src.ingestion.csv_pipeline --batch-id initial-full
python -m src.ingestion.api_ingestion --date 2017-11-25 --batch-id fx-demo
```

Load the full snapshot first; an empty warehouse with only a daily slice fails
the quality baseline. If the download fails, download the Olist ZIP from
[Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) and run
`python scripts/download_dataset.py --archive /path/to/downloaded.zip`.

## 4. Load synthetic inventory

```bash
bash scripts/setup_odbc.sh
docker compose --profile sqlserver up -d --wait --wait-timeout 240 sqlserver
python -m scripts.seed_synthetic_inventory
python -m src.ingestion.sqlserver_ingestion --batch-id inventory-initial
```

The ODBC driver installer targets the Ubuntu version above. See the
[SQL Server guide](sqlserver-source.md) for driver and connection details.

## 5. Publish and open the dashboard

```bash
python scripts/dbt.py debug
python -m src.quality.publication
python -m scripts.verify_phase9
bash scripts/metabase.sh setup
```

Publication builds and tests reporting tables before making them available to
Metabase. Stop and inspect `docs/quality-report.json` if it fails.

Open **http://localhost:3000**. Sign in with `METABASE_ADMIN_EMAIL` and
`METABASE_ADMIN_PASSWORD` from `.env`, then open **E-commerce overview**.

## 6. Add Airflow when ready

```bash
bash scripts/airflow.sh setup
```

Open **http://localhost:8080**. Username: `admin`; password:
`AIRFLOW_ADMIN_PASSWORD` in `.env`. Unpause `ecommerce_pipeline` and trigger it
with both of these values:

- Logical date: `2017-11-24T00:00:00+00:00`
- Configuration: `{"batch_date":"2017-11-24","failure_mode":"none"}`

Use a historical date. Today's date is outside the DAG's bounds and may produce
no tasks. A successful run completes all seven tasks. See the
[Airflow guide](airflow.md) for CLI triggers and recovery.

## Start and stop later

In a new terminal, activate Python again with `source .venv/bin/activate`.
After initial setup, start the full stack with:

```bash
docker compose up -d --wait postgres
bash scripts/airflow.sh start
bash scripts/metabase.sh start
```

If you have not configured Airflow, start the inventory source separately when
needed with the SQL Server command in step 4.

Stop while preserving data:

```bash
bash scripts/metabase.sh stop
bash scripts/airflow.sh stop
docker compose stop postgres
```

Without Airflow configured, stop SQL Server using
`docker compose --profile sqlserver stop sqlserver`.
Never use `docker compose down -v` for routine cleanup: it deletes database volumes.

## Common problems

| Symptom | What to check |
|---|---|
| Python setup exits immediately | `setup_venv.sh` requires exactly Python 3.14.4 and uv |
| Docker connection fails | Ensure the daemon is running and accessible from this terminal |
| Database authentication fails | Use the original credentials for existing volumes; editing `.env` does not reset them |
| SQL Server fails startup | Check password complexity and available memory |
| Driver setup fails | The installer requires Ubuntu 26.04 x86_64 and pinned native packages |
| Publication fails | Read `docs/quality-report.json`; confirm the full snapshot was loaded |
| Airflow runs no tasks | Use the historical logical date and configuration above |

Inspect services with `docker compose ps`, `bash scripts/airflow.sh status`, and
`bash scripts/metabase.sh status`. Logs: `docker compose logs --tail 50 postgres`,
`bash scripts/airflow.sh logs airflow-scheduler`, or `bash scripts/metabase.sh logs`.
