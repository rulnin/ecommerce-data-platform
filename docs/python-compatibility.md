# Python 3.14.4 compatibility — 2026-11-10

Selected interpreter: existing WSL `/usr/bin/python3.14`, CPython 3.14.4.
No system Python replacement, Python download, or Python 3.12 installation occurred.
uv 0.13.7 was installed into `/tmp/ecommerce-uv` using the official installer without
changing shell configuration. `scripts/setup_venv.sh` successfully repaired and
then reverified the existing partial `.venv` using `--allow-existing --seed`.
Activation resolved Python to `.venv/bin/python`, with prefix at the project `.venv`
and base prefix `/usr`. Pip 26.3 works inside the venv despite absent system ensurepip.

No dependency manifests previously existed, so no existing package pins were
upgraded. The following explicit candidates were selected using PyPI metadata,
upstream support statements, installation, and runtime checks. These are direct
dependency pins; transitive dependencies are not fully locked.

| Dependency | Verified version | Evidence / limit |
|---|---|---|
| pandas | 3.1.1 | CPython 3.14 wheel, import and CSV aggregation |
| SQLAlchemy | 2.1.8 | import and PostgreSQL psycopg dialect construction |
| psycopg / psycopg-binary | 3.3.8 | binary wheel and import |
| requests / python-dotenv | 2.34.2 / 1.2.4 | imports |
| pytest / Ruff | 9.2.0 / 0.17.4 | existing test passes; Ruff runs |
| dbt-core / dbt-postgres | 1.12.6 / 1.11.0 | adapter import, `dbt --version`, dependency check |
| psycopg2-binary (dbt adapter) | 2.9.13 | CPython 3.14 wheel and import |
| Airflow | 3.4.0 | isolated install with official Python 3.14 constraints, `airflow version` and uv dependency check |
| pyodbc | 5.5.0 | wheel installs; import BLOCKED by missing libodbc.so.2 |

The [dbt Python support matrix](https://docs.getdbt.com/faqs/Core/install-python-compatibility)
supports Python 3.14 in Core 1.12; older Core 1.11 does not support it. The tested
1.12.6/adapter 1.11.0 pair is the proposed pair for Phase 5, subject to database tests.
[Airflow 3.4 prerequisites](https://airflow.apache.org/docs/apache-airflow/3.4.0/installation/prerequisites.html)
list Python 3.14. Its verification used `/tmp/ecommerce-airflow-check` and constraints
from `https://raw.githubusercontent.com/apache/airflow/constraints-3.4.0/constraints-3.14.txt`.
Airflow was not installed into the project venv; its deployment remains containerized.
Its constrained SQLAlchemy differs from the local pin, reinforcing that separation.

Executed validation:

```bash
source .venv/bin/activate
python -m pip install -r requirements-compatibility.txt
python -m pip check
python -m pytest -q
dbt --version
python -m compileall -q scripts tests
```

Actual installation used equivalent explicit dbt pins alongside `requirements.txt`.
Results: no broken requirements, 1 pytest test passed, dbt Core 1.12.6 and postgres
adapter 1.11.0 reported, compilation passed. `dbt --version` could not query the
latest release inside the network-restricted sandbox; installed versions loaded.
`airflow version` returned 3.4.0 with upstream FileType deprecation warnings;
`uv pip check` passed for all 132 packages in the isolated Airflow environment.

`python -m ruff check scripts tests` reported I001 on the existing profiler import
block. No unrelated source formatting was changed. The version TOML and pin file
were parsed/checked successfully. No CI workflow existed to migrate; Phase 7 will
use `.python-version` and the setup script.

Remaining limits: database connectivity, dbt build, DAG execution, and container
deployment have not been tested. pyodbc was tested separately in
`/tmp/ecommerce-odbc-check`; its missing unixODBC library is a system dependency
blocker, not evidence of Python incompatibility. Phase 3 must verify/install the
appropriate unixODBC runtime and Microsoft ODBC Driver 18 before SQL Server tests.
No driver or system library was installed as part of this migration.
