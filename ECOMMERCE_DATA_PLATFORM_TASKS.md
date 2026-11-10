# E-Commerce Data Platform — Master Prompt & Task Tracker

> **Goal:** Build a production-minded, reproducible, local-first, end-to-end data engineering portfolio project for international remote Data Engineer applications.
>
> **Level:** Intermediate | **Budget:** Rp0 | **Primary OS:** Windows 11 + WSL2 Ubuntu 24.04 LTS | **Working directory:** `~/projects/data-engineering/ecommerce-data-platform`
>
> **Last updated:** 2026-11-10 | **Revision:** v2 (explicit Python venv + WSL2 Docker setup) | **Status:** Phase 1 complete; Phase 2 not started

## 0. Project overview

**Business case:** Integrate public e-commerce order data (Olist CSV), an exchange-rate REST API, and synthetic inventory data in SQL Server into a PostgreSQL analytical warehouse. Orchestrate ingestion, transformation, quality checks, reconciliation, and reporting with Airflow and dbt. Show that the system is safe to rerun, observable, testable, and documented.

**Architecture**

```text
Windows 11
  └── WSL2 Ubuntu 24.04 LTS (source code on Linux filesystem)
       ├── Python 3.14.4 virtual environment: .venv/ (ingestion, dbt, pytest)
       └── Docker Compose (Docker Desktop with WSL integration OR Docker Engine in Ubuntu)
            ├── Sources
            │    ├── data/raw/ (Olist CSV; downloaded locally, gitignored)
            │    ├── REST API (daily USD/BRL rates; Frankfurter or equivalent)
            │    └── SQL Server (synthetic inventory + stock movement)
            ├── PostgreSQL (raw → staging → marts)
            ├── Apache Airflow (DAGs, retries, checkpoints, logging; own container dependencies)
            └── Optional local Metabase
       Python ingestion + dbt run in WSL .venv; Airflow triggers containerized ingestion as configured
```

**Core tech:** Python 3.14.4 in project-local `.venv` (or a verified compatible supported version), SQL Server (local container if host supports it), PostgreSQL, Docker Compose, Apache Airflow, dbt Core, pytest, Ruff, GitHub Actions. Pin compatible versions; **never blindly install the latest of everything**. If SQL Server is too heavy for 16 GB RAM, run its container only for ingestion tests. Do not run incompatible containers or claim functionality without executing tests.

**Project repositories:** `ecommerce-data-platform` (this repo). Cloud lakehouse and migration validator should be separate future repositories.

### Definition of Done (project-level)

- [ ] `README.md` (English) explains the business problem, architecture, setup, run steps, data model, trade-offs, and results.
- [ ] New reviewer can clone the repository, configure `.env`, download sample data, and run the pipeline from documented commands.
- [ ] CSV + API + SQL Server ingestions work, with clear provenance and auditable run metadata.
- [ ] Incremental ingestion, idempotent reruns, retries, backfill, and deterministic tests work.
- [ ] Warehouse models expose validated customer, product, seller, order, payment, and daily sales metrics.
- [ ] Reconciliation prevents order-item/payment join multiplication and checks business totals.
- [ ] Failed rows are quarantined or reported with actionable error detail.
- [ ] Airflow DAG shows successful and simulated failed/recovered runs.
- [ ] GitHub Actions checks pass; no credentials, private data, or heavy raw datasets committed.
- [ ] Screenshots, measured benchmarks, demo instructions, and an interview-ready explanation are included.

---

## 1. MASTER PROMPT — Copy into your coding assistant

> Paste the following block when starting the project in Cursor, VS Code Copilot, Codex, or another coding assistant. Work **one phase at a time**. Keep this task tracker updated in the repository.

```text
Act as a senior Data Engineer, technical mentor, code reviewer, and project manager. Build an intermediate, production-minded, 100%-local-first E-Commerce Data Platform portfolio project that I can showcase to international remote Data Engineer recruiters.

BACKGROUND
- My skills: Python, SQL Server, SQL, ETL/data migration. I want to gain hands-on experience in PostgreSQL, Airflow, dbt, Docker, automated testing, and CI/CD.
- Machine: Windows 11 host, WSL2 Ubuntu 24.04 LTS, approximately 16 GB RAM. Work in Ubuntu filesystem, not /mnt/c.
- Budget: Rp0. Avoid paid cloud resources, paid services, and required subscriptions.
- IMPORTANT: Create and use a dedicated project-local `.venv` under WSL Ubuntu for Python ingestion, dbt Core/dbt-postgres, and pytest. Never install project packages globally or into Windows Python.
- Keep Airflow Python dependencies in its Docker container. Do not share the local WSL venv with containers.
- Install PostgreSQL and SQL Server as Docker services, NOT with native apt/Windows installers. Use Docker named volumes for database persistence.
- Prefer Docker Desktop installed on Windows with WSL integration enabled; do not install a second competing Docker Engine inside Ubuntu if Docker Desktop already supplies it.
- For SQL Server, check host architecture (x86-64/amd64), memory and current Microsoft image support before setup; if incompatible, document an alternative source or use a compatible remote/local test system without misrepresenting the result.
- Output: Real, runnable, tested implementation, not mock code or an architecture-only demo.

BUSINESS SCENARIO / SOURCES
1) Public Olist Brazilian E-Commerce CSV from Kaggle; download to data/raw/ locally. Do not commit raw datasets.
2) Public REST exchange-rate API for USD/BRL; use a documented provider such as Frankfurter, handle rate dates and historical availability, cache/upsert by natural key.
3) Local SQL Server containing SYNTHETIC inventory and stock movement tables linked to valid product IDs from the public dataset. Document that these inventory records are simulated, not part of Olist.
4) PostgreSQL is the analytical storage and warehouse; use raw, staging, and marts layers.

ENVIRONMENT & DEPENDENCIES (MANDATORY)
- Project home: ~/projects/data-engineering/ecommerce-data-platform (Linux filesystem, NOT /mnt/c).
- Verify the installed WSL Ubuntu version, Python version, pip, git, docker, docker compose and free RAM/disk before changes.
- Use the existing WSL Python 3.14.4; do not replace system Python or install Python 3.12.
- Create virtual environment with `uv venv --python /usr/bin/python3.14 --no-python-downloads --seed --allow-existing .venv`; activate via `source .venv/bin/activate`.
- Verify `which python`, `python --version`, `python -m pip --version`, and `python -c 'import sys; print(sys.prefix, sys.base_prefix)'`; ensure the active Python points into `.venv`.
- Install packages using `python -m pip install ...` only after venv activation; use compatible pinned versions in `requirements.txt` or split `requirements-dev.txt` when justified. Avoid blind `pip freeze` of unrelated packages.
- Initially use sqlalchemy, psycopg[binary], pandas, requests or httpx, pytest, python-dotenv, and Ruff; add dbt-core and dbt-postgres when the dbt phase begins.
- SQL Server Python connection requires pyodbc plus platform dependencies and Microsoft ODBC Driver 18; verify driver installation in WSL, and do not confuse pip package with system driver.
- Ensure `.gitignore` covers `.venv/`, `.env`, `__pycache__/`, `.pytest_cache/`, logs, and local data (including CSV). Commit `.env.example`, not secrets.
- Define Docker Compose services using named volumes, sensible health checks, and environment variables; keep bind/listening ports restricted to localhost when possible.
- If resources are tight on 16 GB RAM, stop SQL Server when not needed and run Airflow separately during initial setup.
- Document a clean setup, activation, run, stop, reset and verification flow in README in English.

REQUIRED ENGINEERING CAPABILITIES
- Modular Python ingestion, environment-based configuration, logging, structured error handling, retries and bounded timeouts.
- Full-load first, then deterministic simulated incremental batches for CSV; proper per-source checkpoints/watermarks and idempotent upserts.
- SQL Server incremental ingestion using a documented updated_at/change sequence, plus a strategy for deletes and identical timestamps.
- Airflow orchestration: dependencies, retries, timeouts, safe reruns, backfills, and run metadata.
- dbt models for staging, dimensions, facts, and daily sales marts; tests for unique, not_null, relationships, accepted_values and custom business reconciliation.
- Avoid double counting when joining Olist payments with order items: model their different grains and reconcile separately.
- pytest unit/integration tests and CI with lint and tests. Document test dependencies and assumptions.
- Secure defaults: .env.example, .gitignore, no secrets, no company data, no proprietary SQL/assets, no public database ports unless necessary.
- Documentation in English: architecture, data contracts, schema/grain, runbook, troubleshooting, test evidence, performance baseline and optimizations.
- Prefer simple, maintainable SQL and Python over unnecessary complexity.

WORKING METHOD (MANDATORY)
1) Read ECOMMERCE_DATA_PLATFORM_TASKS.md and inspect the repository before making changes.
2) Work ONLY on the current phase requested by me. Do not jump ahead or silently change scope.
3) Before coding, explain the objective, files to create/edit, assumptions, dependencies, and exact commands to verify.
4) Implement small, cohesive changes. Include complete file paths and real commands.
5) Run relevant commands/tests if you have terminal access. Never state tests passed if you did not run them; report exactly what was and wasn't tested and why.
6) Do not delete/overwrite existing working files or data without my approval. Use migrations/backup where appropriate.
7) After each task, update its checkbox in ECOMMERCE_DATA_PLATFORM_TASKS.md ONLY when evidence confirms completion; add a short entry to the Progress Log with evidence, problems, and the next task.
8) If anything fails, analyze root cause, propose the smallest safe fix, and retest. Do not mark unfinished tasks done.
9) At the end of each phase, show: summary of changes, paths changed, commands run and outcomes, remaining blockers, updated completion count, and next recommended task.
10) Ask me only for essential inaccessible credentials or decisions. Otherwise use safe defaults and proceed with the specific task.
```

### Reusable prompt to resume any session

```text
Continue the E-Commerce Data Platform project. Read ECOMMERCE_DATA_PLATFORM_TASKS.md, README.md, and the repository structure. Identify the FIRST unchecked task in the active phase, verify dependencies and existing implementation, then complete only that task. Run tests where possible. Update the checkbox only if the acceptance criteria passed, append evidence to Progress Log, and report changes, test results, blockers, and the exact next task. Do not fabricate success or modify unrelated code.
```

### Reusable prompt to review a completed phase

```text
Review Phase [NUMBER] of ECOMMERCE_DATA_PLATFORM_TASKS.md. Compare the implementation against its checklist and acceptance criteria. Look for correctness, data duplication, security, hard-coded paths, missing test coverage, performance issues, and reproducibility. Run available checks. Return PASS/FAIL per criterion with evidence, then suggest prioritized fixes. Do not tick any item without verification.
```

---

> The canonical ongoing tracker is [ECOMMERCE_DATA_PLATFORM_TASKS.md](ECOMMERCE_DATA_PLATFORM_TASKS.md). This roadmap records the initial implementation checkpoint.

## 2. Weekly project tracker

> **Rule:** `[x]` means completed AND verified. `[ ]` means not yet verified. Commit this file as work progresses.

| Week | Phase | Status | Deliverable |
|---|---|---|---|
| 1 | Environment + source profiling | ✅ Complete | Docker/PostgreSQL, CSV and source contract |
| 2 | CSV batch + incremental ingestion | ⬜ Not started | Re-runnable raw ingestion |
| 3 | REST API + SQL Server ingestion | ⬜ Not started | Three integrated sources |
| 4 | Airflow orchestration | ⬜ Not started | Scheduled and recoverable DAG |
| 5 | dbt data warehouse | ⬜ Not started | Tested dimensional models |
| 6 | Reconciliation + data quality | ⬜ Not started | Quality report and failure tests |
| 7 | Automated tests + CI | ⬜ Not started | CI checks and reproducible testing |
| 8 | Performance + observability | ⬜ Not started | Measurements and runbooks |
| 9 | Analytics + recruiter documentation | ⬜ Not started | Demo, diagrams, English README |
| 10 | Final hardening + interview rehearsal | ⬜ Not started | Release-ready portfolio |

**Progress:** 1 / 10 phases complete. Update manually after verifying each phase.

### Phase 1 — Environment, repository, and dataset (Week 1)

- [x] P1.1 Verify WSL2 Ubuntu version, available RAM/disk, Python, Git, Docker Desktop WSL integration or Docker Engine/Compose, and compatibility; confirm Docker daemon reachable from WSL.
- [x] P1.2 Create repository `ecommerce-data-platform` under `~/projects/data-engineering/`; initialize Git and appropriate branch.
- [x] P1.3 Create `README.md`, `.gitignore`, `.env.example`, `Makefile`, and standard folder structure.
- [x] P1.4a Verify existing Python 3.14.4, uv-created venv functionality, pip and Git in WSL Ubuntu.
- [x] P1.4b Create/verify `.venv/` inside project root using `bash scripts/setup_venv.sh` with the existing Python 3.14.4.
- [x] P1.4c Activate using `source .venv/bin/activate`; verify `which python` points to `.venv/bin/python`.
- [x] P1.4d Upgrade pip within `.venv` and install compatible, pinned first-phase dependencies.
- [x] P1.4e Add `.venv/`, `.env`, local data, cache, and secrets patterns to `.gitignore`; check `git status`.
- [x] P1.4f Create verified `requirements.txt` (and optional dev requirements), document setup and exit commands in English README.
- [x] P1.4g Execute a simple Python import test and `python -m pytest` smoke test from activated `.venv`.
- [x] P1.5 Configure PostgreSQL in `docker-compose.yml` with a named volume and healthcheck.
- [x] P1.6 Run `docker compose up -d postgres`; verify container health and `SELECT version()`.
- [x] P1.7 Download Olist CSVs to `data/raw/` (local only); write a reproducible download script/instructions.
- [x] P1.8 Profile CSV schemas, record counts, nulls, duplicates, keys, and business relationships; save profiling notes.
- [x] P1.9 Write `docs/data-contracts.md` and an initial source-to-target mapping.
- [x] P1.10 Commit project skeleton; verify no secrets, credentials, or raw CSV files are tracked.

**Exit criteria:** A fresh developer can set up PostgreSQL, obtain the dataset, run a profiling script, and review the resulting source contracts. Include actual command output in Progress Log.

### Phase 2 — CSV ingestion & incremental safety (Week 2)

- [ ] P2.1 Create modular `src/ingestion/csv_ingestion.py`, common config, and DB connection utilities.
- [ ] P2.2 Define PostgreSQL raw tables with stable business keys and appropriate constraints.
- [ ] P2.3 Implement full-load CSV ingestion with bounded batch sizes and transactional writes.
- [ ] P2.4 Simulate daily incremental CSV arrivals by order date; do not claim live incremental feed.
- [ ] P2.5 Implement checkpoint metadata (`source`, `batch_id`, `watermark`, `status`, timestamps, counts).
- [ ] P2.6 Implement idempotent upserts and document late-arriving/update handling.
- [ ] P2.7 Add rejected-row/error handling with useful logs and no sensitive data in logs.
- [ ] P2.8 Test one full load, one incremental batch, three identical reruns, and a failed/recovered run.
- [ ] P2.9 Record exact input/output row counts and duplicate-key checks.

**Exit criteria:** Replaying the same batch does not change unique business-key counts or valid totals; evidence is recorded.

### Phase 3 — REST API + synthetic SQL Server source (Week 3)

- [ ] P3.1 Choose and document the public FX API, response schema, historic date availability, and rate direction.
- [ ] P3.2 Build API client with timeouts, retry/backoff, error handling, and deterministic test fixtures.
- [ ] P3.3 Create raw FX table and upsert by currency pair + rate date; verify repeated calls are safe.
- [ ] P3.4 Verify whether SQL Server Linux container is supported on available CPU and RAM; document fallback if not.
- [ ] P3.5 Configure SQL Server locally with non-committed credentials and persistent data storage.
- [ ] P3.6 Generate SYNTHETIC inventory and stock movements referencing valid public product IDs.
- [ ] P3.7 Implement SQL Server extraction with incremental watermark/tie-breaker and target upsert.
- [ ] P3.8 Document handling of changed and deleted source records; test update and re-run scenarios.
- [ ] P3.9 Verify all three sources load independently to PostgreSQL and write provenance/run audit records.

**Exit criteria:** CSV, FX API, and synthetic SQL Server sources load into separate raw tables with repeatable tests. If SQL Server cannot run locally, mark related tasks blocked rather than falsely complete.

### Phase 4 — Airflow orchestration (Week 4)

- [ ] P4.1 Pin compatible Airflow version and dependencies; avoid unnecessary resource-heavy services.
- [ ] P4.2 Configure local Airflow and persistence in Docker Compose.
- [ ] P4.3 Create DAG with CSV ingestion, API ingestion, SQL Server ingestion, transform, and quality tasks.
- [ ] P4.4 Add dependencies, retries, execution timeouts, run IDs, and logs.
- [ ] P4.5 Support backfill of historical days without duplication.
- [ ] P4.6 Test success, forced failure, rerun, and recovery; capture UI/log screenshots.

**Exit criteria:** DAG is documented, repeatable, and observable; a simulated failure can be recovered.

### Phase 5 — dbt dimensional warehouse (Week 5)

- [ ] P5.1 Set up dbt Core + PostgreSQL adapter, profiles, targets, and connection testing.
- [ ] P5.2 Build source definitions and staging models for each source with documented grain.
- [ ] P5.3 Build `dim_customer`, `dim_product`, `dim_seller`, and `dim_date`.
- [ ] P5.4 Build `fct_order_items`, `fct_payments`, and `fct_daily_sales` with clear business rules.
- [ ] P5.5 Implement incremental materialization only where it improves the model; test changed records.
- [ ] P5.6 Document how order items and payments are modeled separately to avoid many-to-many multiplication.
- [ ] P5.7 Generate dbt documentation and run `dbt build` successfully.

**Exit criteria:** Models have declared grain and valid key relationships; marts expose correct business metrics.

### Phase 6 — Data quality and reconciliation (Week 6)

- [ ] P6.1 Implement dbt `unique`, `not_null`, `relationships`, and suitable `accepted_values` checks.
- [ ] P6.2 Add custom tests for financial total reconciliation, missing mapping, and referential integrity.
- [ ] P6.3 Define `revenue` explicitly (e.g., item value for delivered orders), separate from payment amount.
- [ ] P6.4 Detect duplicate orders/items/payments and unexpected row-count drift.
- [ ] P6.5 Test null injection, duplicate injection, late update, and missing inventory mapping.
- [ ] P6.6 Produce a quality report with check name, expected, actual, PASS/FAIL, and sample failing keys.
- [ ] P6.7 Confirm expected failures do not silently pass through to published marts.

**Exit criteria:** Known bad input reliably causes relevant tests to fail; valid input passes reconciliation.

### Phase 7 — Automated testing and CI (Week 7)

- [ ] P7.1 Add pytest unit tests for ingestion, parsing, checkpointing, and upsert behavior.
- [ ] P7.2 Add database integration tests with disposable/local test database.
- [ ] P7.3 Add Ruff formatter/linter and a documented code style.
- [ ] P7.4 Create `.github/workflows/ci.yml` running achievable lint/unit tests without cloud credentials.
- [ ] P7.5 Provide reproducible local commands matching CI commands.
- [ ] P7.6 Verify CI success on a test commit and capture result in documentation.

**Exit criteria:** CI runs reliably on public repository; failing a test fails the workflow.

### Phase 8 — Performance, observability, and reliability (Week 8)

- [ ] P8.1 Measure baseline load times and row counts with fixed dataset and environment.
- [ ] P8.2 Compare full load vs incremental load using honest, repeatable measurements.
- [ ] P8.3 Analyze slow SQL with `EXPLAIN (ANALYZE, BUFFERS)` as appropriate.
- [ ] P8.4 Add or adjust indexes with before/after benchmark and trade-off notes.
- [ ] P8.5 Capture pipeline logs, ingestion audit, error counts, and duration per run.
- [ ] P8.6 Document failure recovery, data replay, backup/restore, and resource requirements.

**Exit criteria:** Measured metrics (not invented values) and runbooks exist; rerun and recovery are reliable.

### Phase 9 — Analytics & portfolio storytelling (Week 9)

- [ ] P9.1 Write 5–10 business SQL questions and queries based on validated marts.
- [ ] P9.2 Create a simple analytics dashboard (Metabase optional) or screenshot-worthy SQL result set.
- [ ] P9.3 Create architecture and ERD diagrams in `docs/`.
- [ ] P9.4 Write English README: problem, stack, architecture, dataset rights, setup, commands, screenshots, tests.
- [ ] P9.5 Explain trade-offs: PostgreSQL vs SQL Server, batch vs streaming, full vs incremental, local vs AWS.
- [ ] P9.6 Prepare a 3–5 minute English walkthrough and a short CV/LinkedIn project description.

**Exit criteria:** Recruiter can understand the problem, see real evidence, and reproduce the work.

### Phase 10 — Release verification & interview readiness (Week 10)

- [ ] P10.1 Perform clean-clone setup on a fresh folder; verify README instructions.
- [ ] P10.2 Run end-to-end data ingestion, DAG, dbt build/tests, and CI successfully.
- [ ] P10.3 Verify no secrets, proprietary SQL/data, large CSVs, unnecessary files, or internal identifiers are committed.
- [ ] P10.4 Review SQL performance, idempotence, code quality, and cleanup/stop commands.
- [ ] P10.5 Create a versioned release/tag with a concise changelog.
- [ ] P10.6 Rehearse interview Q&A: duplicates, checkpoints, failure recovery, source-target reconciliation, scaling.
- [ ] P10.7 Pin repository to GitHub profile and include verified outcomes in CV.

**Exit criteria:** Clean setup succeeds, project is demonstrable, and all stated features have evidence.

---

## 3. Folder structure (target)

```text
ecommerce-data-platform/
├── .github/workflows/ci.yml
├── airflow/dags/ecommerce_pipeline.py
├── config/
├── data/
│   ├── raw/             # local files; gitignored
│   ├── processed/       # local files; gitignored
│   └── rejected/        # local files; gitignored
├── dbt/
│   ├── models/{staging,intermediate,marts}/
│   ├── macros/
│   └── tests/
├── docs/
│   ├── architecture.md
│   ├── data-contracts.md
│   ├── data-model.md
│   ├── benchmarks.md
│   ├── runbook.md
│   └── screenshots/
├── scripts/
│   ├── download_dataset.py
│   └── seed_synthetic_inventory.py
├── sql/init/
├── src/
│   ├── ingestion/{csv_ingestion,api_ingestion,sqlserver_ingestion}.py
│   └── common/
├── tests/{unit,integration}/
├── .env.example
├── .gitignore               # ignore .venv/, .env, data/, caches
├── .venv/                   # LOCAL ONLY; never commit
├── docker-compose.yml
├── Dockerfile
├── Makefile
├── README.md
├── requirements.txt
└── ECOMMERCE_DATA_PLATFORM_TASKS.md
```

## 4. Environment setup commands (WSL Ubuntu)

> These are starting commands, **not proof** that anything has been installed or verified. Run them only in WSL Ubuntu, after checking the system. Docker must be available from WSL via Docker Desktop integration or an intentionally configured Docker Engine.

```bash
# Confirm workspace and installed components
pwd
python3 --version
git --version
docker --version
docker compose version
docker info

# Use uv with the existing WSL Python; system ensurepip is not required.

# Work on the Linux filesystem
mkdir -p ~/projects/data-engineering/ecommerce-data-platform
cd ~/projects/data-engineering/ecommerce-data-platform

# Require existing Python 3.14.4; install uv using its official instructions first
uv venv --python /usr/bin/python3.14 --no-python-downloads --seed --allow-existing .venv
source .venv/bin/activate
which python
python --version

# Install verified direct dependency pins
python -m pip install -r requirements.txt
python -m pip check
python -c 'import pandas, sqlalchemy, psycopg, requests, pytest; print("imports OK")'

# Do NOT install pyodbc without verifying OS dependencies/ODBC driver first
# Do NOT install airflow to this venv; Airflow runs inside Docker
# Add dbt-core/dbt-postgres in the dbt phase with verified compatibility

deactivate
```

**Do not** commit `.venv/`. Use `python -m pip` rather than invoking an uncertain global `pip`. Use existing Python 3.14.4; do not download a different interpreter as a fallback.

### Docker service rules

- Use PostgreSQL and SQL Server as Docker containers, each with a **named volume**; native installation of either database in Windows/WSL is not required.
- Start with PostgreSQL only: `docker compose up -d postgres`, then verify health and run a simple query.
- Introduce SQL Server in Phase 3 only after host architecture, RAM and image compatibility checks.
- Airflow is added in Phase 4 and runs within its own containers with isolated Python dependencies.
- `docker compose down` stops/removes project containers but does **not** normally remove named volumes; `docker compose down -v` **can erase database data** and must never be used casually.

## 5. Progress Log (append after every verified task)

| Date | Task ID | Result | Verification evidence | Commit/PR | Next action |
|---|---|---|---|---|---|
| YYYY-MM-DD | P1.1 | ⬜ Pending | — | — | Check environment |

**Entry format (copy/paste):**

```md
### YYYY-MM-DD — Pn.n Task title
- Status: PASS / FAIL / BLOCKED
- Files changed:
- Commands/tests executed:
- Evidence (actual output or screenshots):
- Issues/decisions:
- Commit/PR:
- Next task:
```

### 2026-11-10 — Phase 1 initial implementation and evidence
- Status: PARTIAL / environment BLOCKED. Two of 17 Phase 1 checklist entries verified; 0/10 phases complete.
- Files changed: README.md, .gitignore, .env.example, Makefile, scripts/profile_dataset.py, tests/unit/test_profile_dataset.py, docs/environment.md, docs/source-profile.json, docs/data-contracts.md, and this tracker.
- P1.3 PASS: initial skeleton and required root configuration files created; no database service or dependency installation claimed.
- P1.9 PASS: initial source contracts, observed grains, and proposed source-to-target mapping documented from executed profiling.
- P1.1 BLOCKED: WSL2 x86_64 confirmed; Ubuntu 26.04.1, Python 3.14.4, 11 GiB RAM, 952 GiB free disk. Docker command absent, daemon not verified. Full output summarized in docs/environment.md.
- P1.2/P1.10 BLOCKED: existing workspace retained; .git is empty/read-only, git status reports not a repository. No commit or tracked-secret verification possible.
- P1.4a–g BLOCKED: Python 3.12 and pip unavailable. `python3 -m venv .venv` exited 1 because ensurepip is missing; partial .venv remains ignored. Python 3.14 dependency compatibility not established. No packages installed.
- P1.7 PARTIAL: nine CSVs already present; manual acquisition instructions added, but download provenance/license not verified.
- P1.8 PARTIAL: `python3 scripts/profile_dataset.py --input data/raw --output docs/source-profile.json` exited 0. All nine files profiled, including 99,441 orders, 112,650 items, 103,886 payments, and 1,000,163 geolocation rows. Review candidate key repeats 814 times; two category translations missing. Exact duplicate-row analysis and final keys/types remain open.
- Verification: `python3 -m unittest discover -s tests/unit -v` ran 1 test, OK; `python3 -m compileall -q scripts tests` exited 0. These standard-library checks are not the required venv pytest smoke test. `make profile` failed because make is absent; direct Python profiling succeeded.
- P1.5/P1.6 remain unchecked: no PostgreSQL service started or SQL executed.
- Decisions: preserve current Linux workspace and all existing data; do not install host packages or assume Ubuntu 24.04/Python 3.12. Work limited to Phase 1.
- Commit/PR: none; Git metadata unavailable.
- Next task: finish P1.1 by making Docker available in WSL and verifying `docker info`; then restore writable Git metadata and matching Python venv support. Continue dependency setup before database configuration.

### 2026-11-10 — P1.1 Environment and Docker verification recheck
- Status: BLOCKED; P1.1 remains unchecked. Completion is 2/16 Phase 1 checklist entries and 0/10 phases. The previous log's denominator of 17 was a counting error; no checkbox changed.
- Scope: only the first incomplete task, P1.1. Reviewed checklist, existing Progress Log, project file inventory, README.md, and docs/environment.md. No later task implemented and no completed application checks repeated.
- Files changed: docs/environment.md and ECOMMERCE_DATA_PLATFORM_TASKS.md.
- Commands executed: `cat /etc/os-release`, `uname -rm`, `free -h`, `df -h .`, `python3 --version`; bounded subprocess checks for `python3.12 --version`, `python3 -m pip --version`, `git --version`, `docker --version`, `docker compose version`, and `docker info`; module discovery for venv/ensurepip; checks for the standard Docker socket and Docker Desktop WSL paths.
- Evidence: WSL2 x86_64, Ubuntu 26.04.1, Python 3.14.4 at /usr/bin/python3, Git 2.53.0; 11 GiB RAM with 9.7 GiB available and 952 GiB free disk. Python 3.12 and Docker executables absent; pip check exited 1; venv module present but ensurepip absent. /var/run/docker.sock and /mnt/wsl/docker-desktop absent. Detailed evidence and retry commands recorded in docs/environment.md.
- Validation outcome: OS/resource/Python/Git observations obtained; Docker/Compose and daemon reachability FAILED verification because the executable is unavailable. No application tests run because this task changed documentation only.
- Documentation validation: the initial count assertion exposed the historical denominator error; recount confirmed 2 checked and 14 unchecked items. Corrected this entry's count and reran assertions successfully.
- Issues/decisions: Windows Docker Desktop installation/integration state is inaccessible here. No competing Docker Engine installed and no host configuration changed. Dependency and container compatibility are not claimed.
- Commit/PR: none.
- Next pending task: P1.1 remains first. Establish the host Docker setup, enable the intended WSL integration or Engine, and successfully run `docker --version`, `docker compose version`, and `docker info` from WSL before checking it off. P1.2 follows only after P1.1 is verified.

### 2026-11-10 — P1.1 Docker client available; daemon access denied
- Status: BLOCKED; P1.1 remains unchecked. Completion remains 2/16 Phase 1 entries and 0/10 phases.
- Scope: only P1.1; reviewed current checklist, Progress Log, file inventory, and environment notes. No later task attempted.
- Files changed: docs/environment.md and ECOMMERCE_DATA_PLATFORM_TASKS.md.
- Commands executed: OS/kernel, RAM/disk, Python/Git checks; `docker --version`, `docker compose version`, formatted Docker info probe, plain `docker info`, and read-only `docker info` outside the sandbox; socket/path inspection and pip/Python 3.12 checks.
- Evidence: Docker 29.9.3 and Compose v5.7.0 are now installed. Plain `docker info` exited 1 with permission denied at unix:///var/run/docker.sock, including outside the sandbox. Socket exists with srw-rw---- permissions and nobody/nogroup ownership. WSL2 Ubuntu 26.04.1 x86_64, Python 3.14.4, Git 2.53.0; 9.6 GiB available RAM and 952 GiB free disk. pip and Python 3.12 still unavailable.
- Validation: client/Compose checks passed; daemon reachability failed. Empty server fields from the formatted probe do not verify server capabilities. Documentation assertions verified the unchanged checklist and recorded evidence. No application tests run for documentation-only changes.
- Issues/decisions: no socket permissions, group membership, packages, or containers changed. Docker host/integration administration is needed to restore access; no server compatibility claimed.
- Commit/PR: none.
- Next pending task: P1.1 — restore access to the intended Docker socket and successfully rerun `docker info` in this environment. P1.2 remains the following task.

### 2026-11-10 — P1.1 PASS; Docker access verified outside sandbox
- Status: PASS. Only P1.1 checked off after successful verification; 3/16 Phase 1 entries complete, 0/10 phases complete.
- Files changed: ECOMMERCE_DATA_PLATFORM_TASKS.md, docs/environment.md, README.md (current Docker access note).
- Commands executed: `id`, socket `stat`, `docker --version`, `docker compose version`, bounded `docker info` inside and outside the sandbox; `/proc/self/uid_map`, `/proc/self/gid_map`, process group/security inspection; OS/kernel, RAM/disk, Python/Git version checks.
- Evidence: Docker Engine/client 29.9.3 and Compose v5.7.0; outside-sandbox `docker info` exited 0 and reported a Linux x86_64 server, 16 CPUs, 11.02 GiB memory, overlayfs storage and cgroup v2. Host identity includes docker group 986; socket is root:docker, mode 660. WSL2 Ubuntu 26.04.1, Python 3.14.4, Git 2.53.0; 9.8 GiB available RAM, 952 GiB free disk.
- Diagnosis: sandbox `docker info` exited 1; user/group maps expose only ID 1000, supplementary host groups appear as 65534, and socket ownership appears nobody:nogroup. Successful outside-sandbox access isolates the current failure to the AI sandbox boundary, not the working Docker installation. Earlier outside-sandbox failure entries describe prior observations and are superseded by this successful check.
- Compatibility scope: daemon Linux/x86_64 and Compose availability verified. Python 3.14 differs from the planned 3.12; dependency compatibility and venv setup remain for P1.4. No database image, SQL Server, or Airflow compatibility claimed.
- Validation: Docker access passed outside sandbox without sudo; documentation assertions confirmed only P1.1 changed and completion is 3/16. No application tests run for environment/documentation-only work.
- Changes deliberately limited to evidence and P1.1 checkbox; Docker installation, socket permissions, group membership, and containers unchanged.
- Commit/PR: none.
- Next pending task: P1.2 — verify repository location and initialize Git/appropriate branch where writable; retain the existing workspace decision unless relocation is explicitly needed. No P1.2 work performed.

### 2026-11-10 — P1.2 Git repository initialized on main
- Status: PASS; 4/16 Phase 1 entries complete, 0/10 phases complete. Only P1.2 newly checked.
- Files changed: Git metadata created by `git init --initial-branch=main`; ECOMMERCE_DATA_PLATFORM_TASKS.md and README.md updated with evidence/current Git state.
- Location decision: retained /home/fakhrul/dep/ecommerce-data-platform on the WSL Linux filesystem, following the existing workspace decision in prior Progress Log entries instead of moving files to the suggested ~/projects/data-engineering path.
- Diagnosis: sandbox shows an empty read-only .git placeholder. Outside-sandbox inspection confirmed no existing .git metadata or repository before initialization; no existing Git history was overwritten.
- Commands executed outside sandbox: `git init --initial-branch=main`, `git rev-parse --show-toplevel`, `git symbolic-ref --short HEAD`, `git status --short --branch`, `git ls-files`, `git fsck --full`.
- Evidence: initialization succeeded; repository top-level is /home/fakhrul/dep/ecommerce-data-platform; symbolic branch is main; status says `No commits yet on main` and lists the existing project files as untracked. `git ls-files` returned no tracked files. `git fsck --full` exited 0 with the expected empty-repository notice `No default references`.
- Validation: repository location, branch and metadata integrity verified; checklist assertions confirmed only P1.2 newly completed. No application tests run because application code was unchanged.
- Scope: no files staged, no commit created, no remote configured; skeleton commit remains P1.10. No other task checked off.
- Commit/PR: none; initial commit deferred to P1.10.
- Next pending task: P1.4a — verify Python 3.12 or a documented compatible alternative, venv support, pip and Git. P1.3 is already complete.

### 2026-11-10 — P1.4a Python prerequisites verification
- Status: BLOCKED; P1.4a remains unchecked. Completion remains 4/16 Phase 1 entries, 0/10 phases complete.
- Scope: only P1.4a; reviewed checklist, Progress Log, README and existing project file inventory. No project venv creation or dependency installation attempted.
- Files changed: ECOMMERCE_DATA_PLATFORM_TASKS.md and docs/environment.md.
- Commands executed inside and outside sandbox: `python3 --version`, `python3 -m pip --version`, module discovery for venv/ensurepip; additionally `python3.12 --version`, `git --version`, `dpkg-query` installed-package checks, and host `apt-cache policy` for Python 3.12, venv and pip packages.
- Evidence: Python 3.14.4 and Git 2.53.0 available; Python 3.12 command absent. pip check exits 1 with `No module named pip`. venv module exists but ensurepip does not. Host package checks confirm python3-venv/python3.14-venv are not installed and python3-pip has no installed package. Configured apt metadata offers python3.14-venv 3.14.4-1ubuntu0.2 and python3-pip 25.1.1+dfsg-1ubuntu2; no Python 3.12 candidate was reported.
- Validation: matching host and sandbox results establish missing host prerequisites rather than a sandbox-only visibility issue. Checklist assertions passed with P1.4a still pending. Application tests not run because no application code changed.
- Issues/decisions: Python 3.14 is not yet selected as a compatible replacement for the planned 3.12. Existing standard-library profiler execution does not establish ingestion/dbt dependency compatibility. No project packages installed globally and no apt packages installed.
- Smallest proposed prerequisite fix for the current interpreter: install Ubuntu's matching python3.14-venv and python3-pip packages, then recheck pip and ensurepip availability. Resolve the Python compatibility decision before completing P1.4a; keep dbt/Airflow dependencies in their prescribed phases/environments.
- Commit/PR: none.
- Next pending task: P1.4a — restore Python prerequisites and verify/document the chosen compatible interpreter. P1.4b remains untouched.

### 2026-11-10 — P1.4a PASS; adopt existing Python 3.14.4 with uv
- Status: PASS for P1.4a. Completion is 5/16 Phase 1 entries, 0/10 phases. User explicitly authorized Python migration and uv environment/dependency verification; other task checkboxes remain unchanged.
- Files changed: .python-version, pyproject.toml, requirements.txt, requirements-compatibility.txt, scripts/setup_venv.sh, README.md, docs/python-compatibility.md, and active Python instructions in this tracker. Historical Progress Log entries are preserved.
- Environment: existing /usr/bin/python3.14 is CPython 3.14.4; Git 2.53.0. uv 0.13.7 installed in /tmp only; no Python downloaded, no system interpreter replaced, no Python 3.12 installed.
- Implementation: uv seeded pip 26.3 into the existing partial .venv without deleting it; setup script rerun succeeded. Activated python resolves to project .venv/bin/python; sys.prefix differs from /usr base prefix. System ensurepip is not needed for uv's seeding workflow.
- Dependency evidence: pandas 3.1.1, SQLAlchemy 2.1.8, psycopg/binary 3.3.8, requests 2.34.2, python-dotenv 1.2.4, pytest 9.2.0, Ruff 0.17.4 installed. dbt-core 1.12.6, dbt-postgres 1.11.0 and psycopg2-binary 2.9.13 installed and imported; dbt CLI loads. No previous dependency pins existed to upgrade.
- Commands/results: activated `python -m pip check` reports no broken requirements; `python -m pytest -q` reports 1 passed; import/pandas CSV/SQLAlchemy dialect smoke checks passed; compilation passed. TOML/Python-version configuration validated.
- Airflow: version 3.4.0 installed only into /tmp/ecommerce-airflow-check using its official Python 3.14 constraints; CLI returns 3.4.0 and uv dependency check passes (132 packages). Containers/DAGs remain untested and unimplemented.
- Blockers/limits: pyodbc 5.5.0 wheel installs in a separate temporary environment but import fails due to missing libodbc.so.2; Phase 3 must resolve unixODBC and verify Microsoft ODBC Driver 18. No Python version downgrade proposed. Existing profiler Ruff I001 reported, left unchanged. Database connectivity and dbt build untested. See docs/python-compatibility.md for source links and exact limits.
- CI/setup: no existing CI or setup script to migrate; created Python-only setup script and version metadata, leaving CI implementation to Phase 7. Direct dependencies are pinned, transitive dependencies not fully locked.
- Commit/PR: none.
- Next pending task: P1.4b — review/verify the now uv-created project venv against its task acceptance criteria. No later checkbox marked solely because migration verification overlaps it.

### 2026-11-10 — P1.4b Existing uv virtual environment verified
- Status: PASS; 6/16 Phase 1 entries complete, 0/10 phases complete. Only P1.4b newly checked.
- Files changed: ECOMMERCE_DATA_PLATFORM_TASKS.md only.
- Review: inspected current checklist, Progress Log, project inventory, scripts/setup_venv.sh, pyproject.toml, .python-version, and .venv/pyvenv.cfg. The environment was already created and the setup script executed successfully during the authorized Python migration, so recreation was unnecessary.
- Commands/tests executed: direct `.venv/bin/python` assertions for project-root prefix, executable location, Python version, underlying interpreter, site-package isolation, uv metadata, pip seeding and pip module location; `.venv/bin/python -m pip --version`; `bash -n scripts/setup_venv.sh`.
- Evidence: all assertions passed; executable /home/fakhrul/dep/ecommerce-data-platform/.venv/bin/python, prefix /home/fakhrul/dep/ecommerce-data-platform/.venv, base prefix /usr; Python 3.14.4 resolves to existing /usr/bin/python3.14. Config records uv 0.13.7, seed=true, include-system-site-packages=false. pip 26.3 loads from this venv. Setup script syntax check exited 0.
- Validation: venv verification passed; documentation assertions confirmed 6 checked entries and P1.4c still pending. No application tests repeated because no application or setup code changed.
- Issues/decisions: no blocker for P1.4b; existing environment and packages preserved, no installations, downloads or system Python changes. Activation verification is deliberately left for P1.4c.
- Commit/PR: none.
- Next pending task: P1.4c — activate with `source .venv/bin/activate` and verify `which python` points into project .venv/bin/python.

### 2026-11-10 — P1.4c Virtual environment activation verified
- Status: PASS; 7/16 Phase 1 entries complete, 0/10 phases complete. Only P1.4c newly checked.
- Files changed: ECOMMERCE_DATA_PLATFORM_TASKS.md only. Reviewed checklist, Progress Log, existing file inventory, setup script and Python version pin.
- Commands executed in one shell: `source .venv/bin/activate`, `which python`, `python --version`, `python -m pip --version`, Python activation assertions, and `deactivate`.
- Evidence: `which python` returned /home/fakhrul/dep/ecommerce-data-platform/.venv/bin/python; Python 3.14.4; pip 26.3 from the project venv. Assertions confirmed VIRTUAL_ENV, sys.executable and sys.prefix point to the project .venv and sys.base_prefix is different (/usr). All checks passed; shell exited 0.
- Validation: documentation assertions confirmed only P1.4c newly completed and P1.4d remains pending. No application tests repeated because this task verifies shell activation only.
- Issues/decisions: no blockers, installs, environment recreation or unrelated source changes. Activation applies to the verification shell; future shells and the user's terminal must activate separately.
- Commit/PR: none.
- Next pending task: P1.4d — verify pip and install/verify compatible pinned first-phase dependencies inside the activated venv, preserving existing verified pins.

### 2026-11-10 — P1.4d Pinned initial dependencies verified
- Status: PASS; 8/16 Phase 1 entries complete, 0/10 phases complete. Only P1.4d newly checked.
- Files changed: ECOMMERCE_DATA_PLATFORM_TASKS.md only. Reviewed checklist, Progress Log, README, setup script, pyproject.toml and both requirement manifests.
- Commands executed in activated .venv: `python -m pip --version`, `python -m pip check`, exact installed-version assertions against every requirements.txt pin, `python -m pip install --no-index --no-deps -r requirements.txt`, initial dependency import checks, and `python -m pytest -q`.
- Evidence: pip 26.3 is already seeded in the venv from the verified migration, so no further upgrade was needed. All seven initial direct pins match: pandas 3.1.1, SQLAlchemy 2.1.8, psycopg 3.3.8, requests 2.34.2, python-dotenv 1.2.4, pytest 9.2.0, Ruff 0.17.4. psycopg-binary 3.3.8 also verified. Offline install reports every requirement already satisfied; no broken requirements; imports passed; 1 pytest test passed.
- Issues/decisions: preserved verified versions instead of upgrading blindly. Pip warns that the host cache is inaccessible in the sandbox and disables caching; validation still exits 0. No package downloads, installs, system changes or application changes were necessary. The offline --no-deps check was paired with pip check and explicit binary-extra verification; it does not claim a fresh install test.
- Validation: checklist assertions confirm 8 checked entries and P1.4e remains pending.
- Commit/PR: none.
- Next pending task: P1.4e — verify ignore patterns and Git status. User request contains both all-Phase-1 and one-task scope; clarification requested before proceeding to further tasks.

### 2026-11-10 — P1.4e Ignore rules verified
- Status: PASS. `git check-ignore` confirms .venv, .env, data/raw CSV, caches, bytecode, logs and key files ignored; `git status --short --branch` lists only intended source/config/docs. .env.example remains visible. No ignore changes needed.
- Files changed: tracker only. Next: P1.4f.

### 2026-11-10 — P1.4f Requirements and setup documentation verified
- Status: PASS. Existing direct pins retained. README now documents uv setup, activation, pinned install, pip check, pytest and deactivation. Existing installed versions match requirements; system Python unchanged. Airflow remains isolated; optional dbt compatibility pins remain separate.
- Files changed: README.md and tracker. Verification: reviewed setup script and manifests; activated pip check passed. Next: P1.4g.

### 2026-11-10 — P1.4g Activated import and pytest smoke checks
- Status: PASS. Activated Python imported pandas, sqlalchemy, psycopg, requests, dotenv and pytest; output `imports OK`. `python -m pytest -q` passed (1 existing test at this checkpoint; 3 tests after acquisition work). No global installs.
- Files changed: tracker only. Next: P1.5.

### 2026-11-10 — P1.5 PostgreSQL Compose configuration
- Status: PASS. Added docker-compose.yml with postgres:17.11-bookworm, named postgres_data volume mounted at /var/lib/postgresql/data, localhost port, required password environment interpolation, pg_isready healthcheck, bounded logs and 1 GiB memory limit. `docker compose config --quiet` exited 0.
- Files changed: docker-compose.yml and tracker; ignored local .env created only because absent, with generated password and mode 600. Password not printed or committed. No SQL Server/Airflow service added. Next: P1.6.

### 2026-11-10 — P1.6 PostgreSQL startup and SQL verification
- Status: PASS. `docker compose up -d --wait --wait-timeout 120 postgres` succeeded. Compose reports healthy, bound to 127.0.0.1:5432. `SELECT version()` returned PostgreSQL 17.11 (Debian 17.11-1.pgdg12+2), x86_64. Python 3.14 psycopg connection returned ('ecommerce', 1) for SELECT current_database(), 1.
- Evidence: Docker inspect confirms volume ecommerce-data-platform_postgres_data at /var/lib/postgresql/data. No native database installation, tables loaded, or analytical pipeline claimed. Service left running for local use; README documents stop/down without deleting data. Next: P1.7.

### 2026-11-10 — P1.7 Reproducible Olist acquisition
- Status: PASS. Downloaded public archive from publisher Kaggle endpoint to /tmp/ecommerce-olist.zip. `python scripts/download_dataset.py --archive /tmp/ecommerce-olist.zip --report docs/dataset-manifest.json` verified all 9 CSVs identical to existing data/raw files and preserved them. The script's network path was then executed into fresh /tmp/ecommerce-download-verification/raw and produced identical per-file hashes.
- Files changed: scripts/download_dataset.py, tests/unit/test_download_dataset.py, docs/dataset-manifest.json, README.md and tracker. Requests uses bounded timeouts/retries, archive/expanded size limits, fixed member names and refuses differing existing files. Tests cover replay, mismatch preservation, incomplete archives and ignoring traversal members.
- Provenance: publisher API metadata reports version 2, updated 2021-10-01, CC BY-NC-SA 4.0. README records attribution/license and manual ZIP fallback; no raw data committed. Next: P1.8.

### 2026-11-10 — P1.8 Complete source profiling
- Status: PASS. Extended profiler with exact duplicate-row counts; reran all nine CSVs and wrote docs/source-profile.json. Recorded schemas, per-column empty counts, keys and seven relationships; source-profiling.md documents observations and modeling implications.
- Actual rows: customers/orders 99,441 each; items 112,650; payments 103,886; reviews 99,224; products 32,951; sellers 3,095; translations 71; geolocation 1,000,163. Geolocation has 261,831 exact duplicates. Reviews have 814 repeated review IDs but zero exact duplicate rows. No empty declared candidate keys; six relationships have zero unmatched distinct nonempty keys, product category translation has 2.
- Files changed: scripts/profile_dataset.py, tests/unit/test_profile_dataset.py, docs/source-profile.json, docs/source-profiling.md, docs/data-contracts.md, README.md and tracker. Existing profiler import formatting fixed while editing it; Ruff now passes.
- Validation: 3 pytest tests passed; Ruff and compileall passed; a second profile output matched using cmp. Raw data unchanged; SQL type/load design remains Phase 2.
- Next: P1.10. Phase 1 currently 15/16 verified; initial skeleton commit pending. User clarified authorization to complete all remaining Phase 1 tasks; earlier one-task restriction no longer applies to this turn.

### 2026-11-10 — P1.10 Skeleton committed; Phase 1 complete
- Status: PASS. All 16/16 Phase 1 checklist entries verified; 1/10 phases complete. No Phase 2 task implemented.
- Commit: ec66aa7 — Initialize verified Phase 1 local data platform (21 source/config/docs/test files). Git author explicitly Codex <codex@openai.com> because no user author was configured; no global or repository identity configuration changed.
- Verification: staged-file allowlist excludes .env, data/, CSVs, .venv and caches; every staged blob checked against the generated local database password and private-key header. `git diff --cached --check` passed. No proprietary/company files introduced; project sources are public Olist and new project code.
- Final validation: 3 pytest tests passed, Ruff passed, Python compilation passed, regenerated profiling output identical. Compose configuration validates; PostgreSQL healthy on localhost and SQL/Python connection checks passed. Downloader fresh-directory network execution and existing-file preservation both verified.
- Files changed after skeleton commit: tracker updated with actual commit evidence and verified completion; follow-up documentation commit records this checkpoint.
- Limits: direct dependencies pinned, full transitive lock deferred. Review keys and geolocation aggregation are ingestion design decisions, not fabricated uniqueness guarantees. SQL Server/ODBC, FX, orchestration, transformations and CI remain future-phase work. make is optional and its targets were not executed because make is unavailable.
- Service state: PostgreSQL left running; named volume retained. Stop using `docker compose stop postgres` or `docker compose down` without -v.
- Next pending task: P2.1 — modular CSV ingestion, configuration and DB utilities, in a subsequent phase request.

## 6. Decisions & scope guardrails

- Build locally first; **AWS is not a prerequisite** for completing this repository.
- Use only public or synthetic datasets. Never copy company database contents, scripts, credentials, hostnames, or confidential details.
- The Olist files are historical snapshots: date-sliced arrival is an explicit **simulation**, not genuine live CDC.
- Exchange rates must carry rate date; do not apply today's rate to historical transactions without explaining the business rule.
- SQL Server inventory is synthetic and may not reflect actual Olist stock; avoid misleading business claims.
- Keep separate grains for `fct_order_items` and `fct_payments`; aggregation must be tested.
- Docker and SQL Server can be resource-intensive. Document a safe stop/restart approach and keep SQL Server optional until Phase 3.
- No test passes without execution evidence; no checkbox is complete based only on code being written.
- The weekly schedule is a planning guide, not a deadline. Quality and verified evidence come first.

## 7. Useful links

- [Olist dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
- [Airflow documentation](https://airflow.apache.org/docs/)
- [dbt documentation](https://docs.getdbt.com/)
- [PostgreSQL documentation](https://www.postgresql.org/docs/)
- [Docker Compose documentation](https://docs.docker.com/compose/)
- [Frankfurter API](https://frankfurter.app/)
- [GitHub Actions documentation](https://docs.github.com/en/actions)

- [Python venv documentation](https://docs.python.org/3/library/venv.html)
- [Docker Desktop WSL2 backend](https://docs.docker.com/desktop/features/wsl/)
