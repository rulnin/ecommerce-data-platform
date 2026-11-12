# Automated tests and CI

Use the existing Python 3.14.4 project venv in WSL. Install only the direct pins
in requirements.txt for these checks; dbt, Airflow, native ODBC and pyodbc are not
required. All unit requests/source connections are mocked; no source CSVs,
Kaggle account, FX API, SQL Server or cloud credentials are needed.

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
bash scripts/check.sh unit

docker compose up -d --wait postgres
bash scripts/check.sh integration
# All tests, including the opt-in PostgreSQL tests:
RUN_DB_TESTS=1 python -m pytest -q
```

`PYTHON` defaults to `.venv/bin/python` and can select another isolated test venv.
Both script modes run Ruff lint, Ruff format --check and compileall first, then
the specified pytest suite. `set -euo pipefail` propagates every failure. Optional
`make verify` / `make verify-integration` invoke these same scripts; make itself is
not required. Invalid script modes return exit status 2.

## Coverage and database lifecycle

Existing unit coverage includes CSV parsing/field structure, exact monetary
validation, stable keys, FX response contracts/retries/bounds, config precedence,
connection retry/redaction, source mapping and publication-gate decisions. Phase 7
adds start-inclusive/end-exclusive simulated arrival dates and stock checkpoint
coverage for frozen complete intervals, gaps, incomplete ranges and source resets.
Database semantics stay in integration tests rather than being claimed from mocks.

PostgreSQL tests create uniquely named disposable databases using the configured
POSTGRES_HOST/PORT/USER/PASSWORD/DB. The development/CI role needs CREATEDB and
permission to drop its own databases. Tests clean up their own databases in finally
blocks. They never reset the warehouse or source volume. Failed tests still run
cleanup; interrupted processes may leave a test database requiring manual review.
Without RUN_DB_TESTS=1 the eight integration tests skip explicitly.

Integration tests exercise atomic CSV writes/checkpoints, unchanged replay,
corrections, nonregressing backfill, duplicate rejection, DB constraints, changed
input fingerprints, FX cache/refresh/failure, stock sequence/tombstone guards,
and orchestration failure/release and independent item/payment aggregation.
They use small generated fixtures, not the ignored Olist snapshot. SQL Server
itself is not required: committed-sequence source behavior was verified separately
in Phase 3. Full dbt/publication scenarios remain explicit Phase 5/6 scripts;
the lightweight CI does not claim to rerun those or the Airflow runtime.

## Coding style

pyproject.toml declares Python 3.14, 100-character formatting width, four spaces,
double quotes, and Ruff syntax/undefined-name/import-order checks (E4/E7/E9/F/I).
Ruff is pinned to 0.17.4. Format Python with:

```bash
python -m ruff format src scripts tests airflow/dags
python -m ruff check src scripts tests airflow/dags
```

Keep source modules small, use explicit data contracts, bound network/DB operations,
and redact secrets at error boundaries. Add tests for observable behavior and
failure paths; avoid tests that merely restate generated SQL. Project formatting
was applied mechanically and checked for identical parsed Python syntax trees.
No SQL/model business rules were changed by that formatting.

## GitHub Actions

.github/workflows/ci.yml runs on push, pull_request and workflow_dispatch, with
read-only contents permission and checkout credentials disabled. Two independent
Ubuntu 24.04 jobs use .python-version (3.14.4), a fresh `.venv`, pip 26.3 and
requirements.txt. The hosted runner's Python has venv/ensurepip; this does not
replace the WSL system interpreter or the project's uv-created local environment.

- Unit job: `bash scripts/check.sh unit`.
- Integration job: `bash scripts/check.sh integration` with a healthy, ephemeral
  postgres:17.11-bookworm service. CI-only throwaway credentials are declared in
  the workflow and are not warehouse secrets. No external/paid service is used.

Both jobs have ten-minute bounds. Dependency cache keys track requirements.txt;
transitive dependencies are not fully locked. Tests are not allowed to fail via
continue-on-error or swallowed shell statuses. The local commands are identical
to the test steps; GitHub additionally provides checkout/Python/cache/service
setup. See official [checkout](https://github.com/actions/checkout) and
[setup-python](https://github.com/actions/setup-python) documentation.

Local workflow syntax is validated with the checksum-verified official
[actionlint](https://github.com/rhysd/actionlint) 1.7.12 executable. Local script
success and intentional failure propagation are recorded separately from a
hosted GitHub Actions result. Hosted verification passed for commit `67271c2b3f3a76d46ecd60ea6cd6bef8030e128b`:
[successful GitHub Actions run](https://github.com/rulnin/ecommerce-data-platform/actions/runs/43006266346). Both unit and integration jobs
completed successfully. The complete result and job links are captured in
Phase 7 evidence (generated locally); P7.6 is now verified.

## Airflow and Metabase smoke checks

The current lightweight suite has 47 unit and eight PostgreSQL integration tests.
The warehouse subprocess test checks that a nonzero exit fails its caller.
For full runtime validation, start the configured services, trigger a historical
Airflow run, and confirm all seven tasks succeed. Metabase setup provisions eight
SQL questions; open **E-commerce overview** and confirm charts return results.
Repeated `bash scripts/metabase.sh setup` preserves the populated dashboard.
These service checks require loaded sources and are separate from lightweight CI.

Local verification on 2026-11-12: 47 unit tests and eight integration tests passed;
Airflow run `reporting_update_1794459481` completed all seven tasks successfully.
All eight Metabase question queries completed, reporting grants were checked for
existing and future tables, and repeated setup preserved the dashboard. These are
local checks of the updated workflow, not a new hosted CI result.
