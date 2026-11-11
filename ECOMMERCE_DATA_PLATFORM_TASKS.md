# E-Commerce Data Platform — Master Prompt & Task Tracker

> **Goal:** Build a production-minded, reproducible, local-first, end-to-end data engineering portfolio project for international remote Data Engineer applications.
>
> **Level:** Intermediate | **Budget:** Rp0 | **Primary OS:** Windows 11 + WSL2 Ubuntu 24.04 LTS | **Working directory:** `~/projects/data-engineering/ecommerce-data-platform`
>
> **Last updated:** 2026-11-11 | **Revision:** v2 (explicit Python venv + WSL2 Docker setup) | **Status:** Phases 1–6 complete; Phase 7 verification in progress

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
| 2 | CSV batch + incremental ingestion | ✅ Complete | Re-runnable raw ingestion |
| 3 | REST API + SQL Server ingestion | ✅ Complete | Three integrated sources |
| 4 | Airflow orchestration | ✅ Complete | Scheduled and recoverable DAG |
| 5 | dbt data warehouse | ✅ Complete | Tested dimensional models |
| 6 | Reconciliation + data quality | ✅ Complete | Quality report and failure tests |
| 7 | Automated tests + CI | 🔄 In progress | Local checks verified; hosted run pending |
| 8 | Performance + observability | ⬜ Not started | Measurements and runbooks |
| 9 | Analytics + recruiter documentation | ⬜ Not started | Demo, diagrams, English README |
| 10 | Final hardening + interview rehearsal | ⬜ Not started | Release-ready portfolio |

**Progress:** 6 / 10 phases complete. Update manually after verifying each phase.

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

- [x] P2.1 Create modular `src/ingestion/csv_ingestion.py`, common config, and DB connection utilities.
- [x] P2.2 Define PostgreSQL raw tables with stable business keys and appropriate constraints.
- [x] P2.3 Implement full-load CSV ingestion with bounded batch sizes and transactional writes.
- [x] P2.4 Simulate daily incremental CSV arrivals by order date; do not claim live incremental feed.
- [x] P2.5 Implement checkpoint metadata (`source`, `batch_id`, `watermark`, `status`, timestamps, counts).
- [x] P2.6 Implement idempotent upserts and document late-arriving/update handling.
- [x] P2.7 Add rejected-row/error handling with useful logs and no sensitive data in logs.
- [x] P2.8 Test one full load, one incremental batch, three identical reruns, and a failed/recovered run.
- [x] P2.9 Record exact input/output row counts and duplicate-key checks.

**Exit criteria:** Replaying the same batch does not change unique business-key counts or valid totals; evidence is recorded.

### Phase 3 — REST API + synthetic SQL Server source (Week 3)

- [x] P3.1 Choose and document the public FX API, response schema, historic date availability, and rate direction.
- [x] P3.2 Build API client with timeouts, retry/backoff, error handling, and deterministic test fixtures.
- [x] P3.3 Create raw FX table and upsert by currency pair + rate date; verify repeated calls are safe.
- [x] P3.4 Verify whether SQL Server Linux container is supported on available CPU and RAM; document fallback if not.
- [x] P3.5 Configure SQL Server locally with non-committed credentials and persistent data storage.
- [x] P3.6 Generate SYNTHETIC inventory and stock movements referencing valid public product IDs.
- [x] P3.7 Implement SQL Server extraction with incremental watermark/tie-breaker and target upsert.
- [x] P3.8 Document handling of changed and deleted source records; test update and re-run scenarios.
- [x] P3.9 Verify all three sources load independently to PostgreSQL and write provenance/run audit records.

**Exit criteria:** CSV, FX API, and synthetic SQL Server sources load into separate raw tables with repeatable tests. If SQL Server cannot run locally, mark related tasks blocked rather than falsely complete.

### Phase 4 — Airflow orchestration (Week 4)

- [x] P4.1 Pin compatible Airflow version and dependencies; avoid unnecessary resource-heavy services.
- [x] P4.2 Configure local Airflow and persistence in Docker Compose.
- [x] P4.3 Create DAG with CSV ingestion, API ingestion, SQL Server ingestion, transform, and quality tasks.
- [x] P4.4 Add dependencies, retries, execution timeouts, run IDs, and logs.
- [x] P4.5 Support backfill of historical days without duplication.
- [x] P4.6 Test success, forced failure, rerun, and recovery; capture UI/log screenshots.

**Exit criteria:** DAG is documented, repeatable, and observable; a simulated failure can be recovered.

### Phase 5 — dbt dimensional warehouse (Week 5)

- [x] P5.1 Set up dbt Core + PostgreSQL adapter, profiles, targets, and connection testing.
- [x] P5.2 Build source definitions and staging models for each source with documented grain.
- [x] P5.3 Build `dim_customer`, `dim_product`, `dim_seller`, and `dim_date`.
- [x] P5.4 Build `fct_order_items`, `fct_payments`, and `fct_daily_sales` with clear business rules.
- [x] P5.5 Implement incremental materialization only where it improves the model; test changed records.
- [x] P5.6 Document how order items and payments are modeled separately to avoid many-to-many multiplication.
- [x] P5.7 Generate dbt documentation and run `dbt build` successfully.

**Exit criteria:** Models have declared grain and valid key relationships; marts expose correct business metrics.

### Phase 6 — Data quality and reconciliation (Week 6)

- [x] P6.1 Implement dbt `unique`, `not_null`, `relationships`, and suitable `accepted_values` checks.
- [x] P6.2 Add custom tests for financial total reconciliation, missing mapping, and referential integrity.
- [x] P6.3 Define `revenue` explicitly (e.g., item value for delivered orders), separate from payment amount.
- [x] P6.4 Detect duplicate orders/items/payments and unexpected row-count drift.
- [x] P6.5 Test null injection, duplicate injection, late update, and missing inventory mapping.
- [x] P6.6 Produce a quality report with check name, expected, actual, PASS/FAIL, and sample failing keys.
- [x] P6.7 Confirm expected failures do not silently pass through to published marts.

**Exit criteria:** Known bad input reliably causes relevant tests to fail; valid input passes reconciliation.

### Phase 7 — Automated testing and CI (Week 7)

- [x] P7.1 Add pytest unit tests for ingestion, parsing, checkpointing, and upsert behavior.
- [x] P7.2 Add database integration tests with disposable/local test database.
- [x] P7.3 Add Ruff formatter/linter and a documented code style.
- [x] P7.4 Create `.github/workflows/ci.yml` running achievable lint/unit tests without cloud credentials.
- [x] P7.5 Provide reproducible local commands matching CI commands.
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

### 2026-11-10 — P2.1 Modular ingestion foundations
- Status: PASS; 1/9 Phase 2 tasks complete, 1/10 phases complete. Phase 1 unchanged.
- Files changed: src package initializers, src/common/config.py, src/common/db.py, src/ingestion/csv_ingestion.py, tests/unit/test_ingestion_foundations.py, .env.example, README.md and tracker.
- Implementation: immutable environment settings with explicit required credentials, environment-over-dotenv precedence and bounded numeric options. Password omitted from repr. PostgreSQL connection retries limited to establishment with bounded exponential delays and connect/statement timeouts; transaction failures are never automatically replayed and driver connection details are sanitized. CSV iterator handles BOM/quoted newlines, validates headers/field counts and yields bounded batches with record numbers. Inspection CLI outputs counts only; no loading or table creation yet.
- Commands/results: `.venv/bin/python -m pytest -q` reports 11 passed; Ruff checks across src/scripts/tests passed; compileall passed. Inspection of real orders at batch size 1000 reports 99,441 rows in 100 batches. Read-only configured DB connection outside sandbox passed SELECT current_database(), 1 and SHOW statement_timeout (1min).
- Tests cover environment precedence/validation/secret repr, multiline CSV/remainder, duplicate headers/field mismatch, bounded connection retry, sanitized failure and transaction non-retry. Initial Ruff findings in new code corrected and rerun clean.
- Scope: no packages upgraded, raw files altered, schema created or source rows loaded. .env.example documents optional defaults; existing local .env unchanged.
- Commit/PR: none.
- Next task: P2.2 — PostgreSQL raw table keys/constraints. Request contains all-Phase-2 and one-task instructions; clarification requested before further tasks.

### 2026-11-10 — P2.2 Raw tables and preservation keys
- Status: PASS. Added additive sql/init/002_csv_raw.sql and src/ingestion/contracts.json; migration executed on PostgreSQL 17.11. Nine raw tables use JSONB original-string payloads, primary business keys, required key-field/object/hash constraints and run-provenance foreign keys.
- Natural keys: customer/order/product/seller IDs, item order+item ID, payment order+sequence, category name. Review versions and geolocation use canonical content hashes; 261,831 exact geolocation duplicates collapse explicitly, with input counts preserved in audit. No cross-source raw FK or destructive replacement.
- Verification: disposable PostgreSQL tests prove required payload-key checks and unique constraints; real full load succeeded. See docs/csv-ingestion.md for raw mapping and history rules. Next: P2.3.

### 2026-11-10 — P2.3 Transactional full load
- Status: PASS. Added src/ingestion/csv_pipeline.py: bounded Python batches COPY to temporary staging; database merges all nine tables in one data/checkpoint transaction. Configured batch default 1000; no raw data or existing tables deleted. Whole input fingerprints checked before/after loading.
- Executed `.venv/bin/python -m src.ingestion.csv_pipeline --batch-id phase2-full`; successful run 079ff418-27d0-4623-86cc-6c719b262026. Loaded full public snapshot with exact input/output counts recorded in docs/phase2-evidence.json. Next: P2.4.

### 2026-11-10 — P2.4 Simulated date arrivals
- Status: PASS. Inclusive start/exclusive end purchase-date selection determines order/item/payment/review membership. Unchanged reference snapshots skip via fingerprint; changed references reload fully. No live feed or CDC claimed.
- Real 2017-11-24 batch selected 1,176 orders, 1,366 items, 1,214 payments, 1,175 reviews. Disposable-database consecutive-day test proves insertion from one to two orders and associated items. Backfills explicitly replay old windows. Next: P2.5.

### 2026-11-10 — P2.5 Audit and per-source checkpoints
- Status: PASS. metadata.ingestion_runs stores unique attempt UUID, source, batch, mode, status, start/end timestamps, per-source counts, input hashes and sanitized error; metadata.checkpoints stores source/batch/watermark/successful run/time. Watermarks use max simulation boundary, not automatic CDC completeness. Backfill cannot regress them.
- Verified six successful real attempts and one failed attempt, all with timestamps/fingerprints. Failed attempt owns zero checkpoints. Run creation and fingerprints persist separately; success/data/checkpoints commit together. Session lock serializes cooperating writers. Crash/connection-loss running-audit limitations documented. Next: P2.6.

### 2026-11-10 — P2.6 Idempotent upserts and late changes
- Status: PASS. Same hash leaves row/provenance timestamp unchanged; changed natural-key payloads update. Content-hash tables preserve versions. Repeated batch IDs produce separate audit attempts. Deletions are not inferred and old changed snapshots have no source change-sequence ordering; limitations documented.
- Disposable tests verify changed item prices update two existing rows without new business keys, snapshots stay identical across three reruns, and older-date replay leaves watermark at the later boundary. Real-date reruns report zero inserts/updates and stable totals. Next: P2.7.

### 2026-11-10 — P2.7 Rejections and recovery reports
- Status: PASS. metadata.rejections stores source, record/field where known and code only. Invalid nonnegative Decimal amounts, empty keys, bad purchase timestamps, structural errors and duplicate natural keys abort the whole run. No row values, credentials or driver detail logged at the run boundary. Structural field-count failures retain record number.
- Tests inject invalid price, duplicate input keys and simulated mid-run failure; committed target snapshots remain unchanged. First fixture failures were duplicate synthetic translation/geolocation values; corrected fixtures and reran. Late test-module collision and missing constraint-test import corrected; final suite passes. No rejected records silently loaded. Next: P2.8.

### 2026-11-10 — P2.8 Full/incremental/replay/failure evidence
- Status: PASS. Ran `python -m scripts.verify_phase2 --full-run 079ff418-27d0-4623-86cc-6c719b262026`: full baseline, one incremental day, three identical incremental reruns, forced order-item failure and same-batch recovery. Each check compares all row/unique-key counts, independent financial totals and non-regressing watermark values.
- Failure run 2801b170-ee85-4869-abc2-f9ed767cce29 reports simulated_failure and a rejection record, without advancing checkpoints. Success/recovery details in docs/phase2-evidence.json; verification script is reproducible and never deletes warehouse rows.
- Final commands: `RUN_DB_TESTS=1 .venv/bin/python -m pytest -q` reports 21 passed; default suite reports 18 passed/3 integration tests skipped. Ruff, compileall and CLI help passed. Integration tests use uniquely created disposable DBs and clean up only those DBs. Next: P2.9.

### 2026-11-10 — P2.9 Counts and financial baseline
- Status: PASS. Target row and distinct-key counts agree: customers/orders 99,441 each; items 112,650; payments 103,886; reviews 99,224; products 32,951; sellers 3,095; translations 71; geolocation 738,332 from 1,000,163 source rows after 261,831 exact duplicates. Duplicate target keys: zero.
- Independent source Decimal and target numeric sums match: price BRL 13,591,643.70; freight BRL 2,251,909.54; payment BRL 16,008,872.12. No item/payment many-to-many join and no revenue claim. Reruns/failure/recovery preserve these totals.
- Paths: docs/phase2-evidence.json, docs/csv-ingestion.md, updated source contracts/README, ingestion implementation, migration, verification script and tests. Makefile verify now runs pytest/Ruff/compilation so pytest-function tests are not silently omitted; commands run directly because make is unavailable.
- Completion: 9/9 Phase 2 tasks, 2/10 phases. User explicitly clarified all Phase 2 work authorized. Phase 3 untouched; no dependencies upgraded or system configuration changed. No commit created this phase.
- Next task: P3.1 — choose/document public FX provider, response schema, historical availability and rate direction, in the next phase request.

### 2026-11-10 — P3.1 FX provider and historical contract
- Status: PASS. Selected Frankfurter v2's fixed ECB provider endpoint for USD/BRL reference rates; no paid API/key. Added docs/fx-contract.md and docs/fx-api-probes.json with actual responses, schema, rate direction, requested/observed dates and freshness rules.
- Live probes: 2016-09-04 -> 2016-09-02, rate 3.2653; 2017-11-24 -> same date, 3.2314; Saturday 2017-11-25 -> Friday 2017-11-24; 2018-10-17 -> same date, 3.7372. 1999-01-04 and 1998-12-31 return 404 despite provider-wide metadata starting in 1999, so pair coverage is not overstated.
- Commands: read official Frankfurter docs and live provider probes outside the network-restricted sandbox. API client/database work stayed in subsequent Phase 3 tasks after user clarified all Phase 3 tasks authorized. Next: P3.2.

### 2026-11-10 — P3.2 Bounded FX client and deterministic tests
- Status: PASS. Added src/ingestion/api_ingestion.py with Decimal parsing, fixed pair/provider, date/rate validation, 64 KiB response bound, 10/30-second connect/read timeouts, three attempts and 1/2-second backoff. 429/server/network failures retry; permanent statuses fail; no response/transport details logged.
- Tests: deterministic in-code responses cover weekend date retention, invalid/non-finite/negative/wrong-currency/stale/future observations, oversized/malformed JSON, transient retry, timeout exhaustion and permanent 404. No existing pins upgraded. Next: P3.3.

### 2026-11-10 — P3.3 FX raw upsert and caching
- Status: PASS. sql/init/003_external_sources.sql defines raw.fx_rates with pair/date natural key and positive numeric rate, raw.fx_requests for requested/observed date mapping, plus external audit/checkpoints shared by new sources. src/common/external_audit.py records independent attempts and commits data/status together.
- Actual live load for 2017-11-25 inserted one ECB USD/BRL row dated 2017-11-24, rate 3.2314 (run e739b4f8-ad05-4aeb-b78e-3d2db575f2c8). Repeated calls hit cache with no new rate row. Disposable DB test verifies correction refresh, weekend mapping reuse and failed-request audit rollback. Next: P3.4.

### 2026-11-10 — P3.4 SQL Server platform compatibility
- Status: PASS for this local development environment. Verified WSL2 Ubuntu 26.04.1 x86_64, approximately 9 GiB available RAM and x86_64 Docker daemon. Reviewed Microsoft container/ODBC requirements and actual MCR tags; explicit 2022-CU27-GDR1-ubuntu-22.04 image selected, not a moving latest tag.
- Source container later ran successfully and reports SQL Server 16.0.4305.5. 3 GiB container cap, 2048 MiB SQL memory limit. WSL development verification does not claim production host certification. No incompatible architecture/emulation or native SQL Server installation. Next: P3.5.

### 2026-11-10 — P3.5 Local SQL Server, persistence and WSL connector
- Status: PASS. Added optional sqlserver Compose profile, localhost 1433, named volume ecommerce-data-platform_sqlserver_data at /var/opt/mssql, healthcheck, bounded logs and Developer edition/EULA setting. `.env` missing SA/reader passwords generated without printing values; existing credentials preserved. .env.example documents blank placeholders.
- Runtime issue: sudo requires interactive authentication. Used official Ubuntu/Microsoft packages extracted into ignored .local/odbc, without sudo/system package changes or maintainer scripts. Added scripts/setup_odbc.sh, .local ignore rule, requirements-sqlserver.txt and src/common/sqlserver.py. Microsoft package SHA-256 verified; libodbc2/libodbcinst2 2.3.14-1 and missing libltdl7 2.5.4-9 included. pyodbc 5.5.0 installed only in existing .venv.
- Verification: driver discovery reports ODBC Driver 18 for SQL Server; real WSL connection reports 18.07.0001. SQL Server container healthy, volume inspected and port restricted to 127.0.0.1. This is a project-local driver/runtime, not a global dpkg-install claim. Developer/bootstrap and certificate limits documented. Next: P3.6.

### 2026-11-10 — P3.6 Deterministic synthetic inventory
- Status: PASS. Added sql/init/003_synthetic_sqlserver.sql and scripts/seed_synthetic_inventory.py. Source Products uses 100 valid IDs selected deterministically from Phase 2 raw.products. Initial Inventory and StockMovements each contain 100 rows with quantity/delta 100; source FK/product checks enforced.
- Seed preserves existing rows, creates inventory_demo and dedicated inventory_reader login with SELECT only on the outbox/counter. Source and target records explicitly synthetic; no claim this is real Olist stock or a complete stock ledger. Re-seeding can recreate a deleted demo movement, producing a new change event. Next: P3.7.

### 2026-11-10 — P3.7 Committed-sequence extraction
- Status: PASS. Added src/ingestion/sqlserver_ingestion.py: frozen upper-bound outbox extraction, bounded fetchmany, sequence-conditional target upserts and checkpoint/data/audit success in one PostgreSQL transaction. Raw inventory/movements retain UTC updated_at, unique source change sequence, synthetic flag and provenance.
- Source triggers serialize a transactional counter and log inserts/updates/soft/physical deletes. Rollback leaves no counter gap and later transactions cannot commit a higher outbox range ahead of an uncommitted lower counter range. Timestamp ties do not drive extraction. Gaps/reset/incomplete ranges fail explicitly; no outbox purge implemented.
- Initial real ingestion read/upserted 200 events; immediate repeat read 0. Evidence preserved as initial_full_load in docs/phase3-evidence.json. Next: P3.8.

### 2026-11-10 — P3.8 Update/delete/recovery verification
- Status: PASS. scripts/verify_phase3.py performed two updates with identical UTC timestamps, a soft inventory delete, a physical movement delete, forced target failure, recovery and zero-event replay. Source transaction rollback preserved its counter. Recovery processed exactly four events, with two tombstones; failed target attempt changed neither raw state nor checkpoint.
- Real targets contain 100 inventory keys and 100 movement keys, one tombstone each, no missing public product mapping. Latest failed attempt 92447c50-269c-462b-8c04-86a480eb568a records simulated_failure; later recovery succeeds. Replay/upsert guards also tested in disposable PostgreSQL, including ignoring older sequences.
- Verification is repeatable: seed restores demo movement before new deliberate changes. Docs describe reset/retention, tombstone/resurrection, certificate, stale-running-audit and local-runtime limitations. Next: P3.9.

### 2026-11-10 — P3.9 Three independent sources and Phase 3 completion
- Status: PASS. Actual FX, synthetic stock and CSV loads executed independently with auditable run IDs. CSV reread is required here to verify cross-source independence, not to repeat Phase 2 implementation. CSV row counts remain unchanged and stock state is unaffected by FX/CSV runs. Separate external source keys prevent checkpoint collision.
- Evidence: docs/phase3-evidence.json stores initial/repeated/recovered stock counts, failed run, versions, FX cache observation, CSV run ID/counts and audit summary; docs/fx-api-probes.json stores live API coverage. Source contracts, README and source-specific runbooks updated. No source records/credentials/binaries committed.
- Final validation: `RUN_DB_TESTS=1 .venv/bin/python -m pytest -q` reports 38 passed. Default suite reports 33 passed/5 opt-in DB tests skipped. Ruff, compileall, bash syntax, pip check and Compose config validation passed. Named source volume and restricted reader connection verified. No unrelated code/pins changed; no Phase 4 work performed.
- Service handling: SQL Server stopped after verification to release memory; named volume retained. PostgreSQL remains running. Start/wait for source health before next stock extraction. No commit created this phase; changes remain reviewable in workspace.
- Completion: 9/9 Phase 3 tasks verified, 3/10 phases complete. Next: P4.1 — select/pin compatible containerized Airflow and dependencies in a subsequent phase request.

### 2026-11-10 — P4.1 Container-only Airflow pins
- Status: PASS. Airflow 3.4.0 on Python 3.14.4, standard provider 1.21.0, FAB 3.10.2, SQLAlchemy 2.0.55, psycopg/binary 3.3.6, pyodbc 5.3.0, dotenv 1.2.4 and requests 2.34.2 pinned against vendored official Python 3.14 constraints. Metadata driver psycopg2-binary 2.9.13 pinned in Dockerfile. Existing WSL venv pins unchanged.
- Files: airflow/Dockerfile, airflow/requirements.txt, airflow/constraints/constraints-3.14.txt, .dockerignore and docs/airflow-runtime.json. Built a minimal Python 3.14.4 Debian 12 image with its own ODBC 18.7.1.1; pip check passes and actual runtime versions/driver discovery recorded.
- Issues resolved: full official image pull stalled on a 490 MiB layer and BuildKit session-health failure. Switched to smaller constrained custom image. Initial pydantic-core 2.50.2 resolution failed despite published compatible wheel; isolated install probe succeeded and rebuild with pip 26.3 passed without changing constraints. No unrelated dependency upgrades. Next: P4.2.

### 2026-11-10 — P4.2 LocalExecutor services and persistence
- Status: PASS. Added docker-compose.airflow.yml and scripts/airflow.sh setup/start/stop/status/logs. Three services (API, scheduler, DAG processor), no Redis/Celery/triggerer. API 127.0.0.1:8080 with FAB authentication. Limits 1/2/1 GiB; parallelism 2. Separate airflow_meta role/database uses existing PostgreSQL volume; airflow_logs named volume verified. Read-only DAG/CSV mounts; no host venv or Docker socket mount.
- scripts/init_airflow_db.py creates missing metadata secrets/role/database and warehouse orchestration audit schema, preserving existing values. .env.example contains blank placeholders. Passwords/JWT/Fernet values remain ignored. Setup initially found PostgreSQL stopped; started it. Metadata startup found trailing newline in _CMD URL and was corrected with stdout.write. Full setup subsequently passed.
- Verification: API/scheduler/DAG processor/PostgreSQL/SQL Server all healthy. Authenticated API login passed. Restarted all three Airflow services and verified seven successful DAG records and paused state persist. No source data deleted. Next: P4.3.

### 2026-11-10 — P4.3 Real five-task DAG
- Status: PASS. airflow/dags/ecommerce_pipeline.py schedules the historical snapshot period and calls CSV, FX and inventory tasks, then transform and quality. src/orchestration/tasks.py wraps existing loaders and records step provenance. sql/init/004_orchestration.sql provides audit/control tables and staging.daily_ingestion_summary.
- Transform computes day-level order/item/payment counts and separate item/payment values without a multiplying join. Quality checks source attempts, dated FX, product mapping and current-run summary. This operational summary is not Phase 5 dimensional/dbt implementation or full Phase 6 quality/publication gating.
- Verification: zero DAG import errors, successful LocalExecutor DAG execution and authenticated real UI capture. Database regression fixture proves two items/two payments aggregate separately and summary upsert stays one row. Native/manual execution uses explicit date semantics; stock remains latest-source state, not historical stock time travel. Next: P4.4.

### 2026-11-10 — P4.4 Retries, bounded execution and run logs
- Status: PASS. DAG max_active_runs=1/max_active_tasks=2, two retries, 10-second exponential delay capped at 60 seconds, 5-minute task and 20-minute DAG timeouts. metadata.orchestration_steps records run/task/date/attempt/status/start/end and source UUID; bounded hashed loader batch IDs link to source audit. No distributed rollback claimed.
- Real failure run phase4_1794319479_failure failed quality on attempts 1/2/3 after successful sources/transform; releasing the explicit demo control and clearing only failed task recovered on attempt 4. Failed attempt logs captured and sanitized in docs/airflow-evidence/. Unit/database tests verify date fallback and release/audit behavior. Next: P4.5.

### 2026-11-10 — P4.5 Historical backfill and replay
- Status: PASS. Manual batch_date works without a logical date; scheduled/native backfills use data_interval_start. Catchup=false and historical end bound prevent unintended current-date snapshot runs; DAG defaults paused. Executed a same-day rerun, explicit 2017-11-25/26 runs and native `airflow backfill create --from-date 2017-11-25 --to-date 2017-11-26 --reprocess-behavior completed --max-active-runs 1`.
- Both native backfill runs succeeded. Stable CSV metrics: 99,441 orders, 112,650 items, 103,886 payments; price BRL 13,591,643.70 and payments BRL 16,008,872.12. Inventory/movement keys remain 100 each; quantity sum 9918 unchanged. FX natural-key/cache semantics and independent stock cursor prevent duplicate source rows.
- Summary rows: 2017-11-24 = 1176/1366/1214 orders/items/payments; 2017-11-25 = 499/580/538; 2017-11-26 = 391/456/411. See docs/phase4-evidence.json for values and native run IDs. Next: P4.6.

### 2026-11-10 — P4.6 Failed DAG recovery, UI evidence and phase completion
- Status: PASS. scripts/verify_phase4.py verified seven final successful DAG runs (success, failed/recovered, rerun, two explicit days, two native backfills); 35 successful task attempts plus three intentionally failed quality attempts. All five tasks in each final run succeeded. Restart persistence verified afterward.
- Captures: docs/screenshots/phase4-success.png, phase4-failed.png and phase4-recovered.png show the actual authenticated UI; visually inspected. scripts/capture_airflow_ui.py uses an ephemeral digest-pinned Chromium/CDP container and optional websocket-client 1.9.0 in /tmp. A capture-tool context-manager error was corrected using closing(); repeated runtime verification passed. Browser container removed after capture.
- Logs/version evidence: docs/airflow-evidence/phase4-quality-attempt-1.json through -3.json, docs/airflow-runtime.json, docs/phase4-evidence.json. Runbook docs/airflow.md and README document setup, authentication, resource limits, pause/backfill/clear recovery and limits. Makefile verification now includes DAG lint/compilation.
- Final tests: `RUN_DB_TESTS=1 .venv/bin/python -m pytest -q` = 41 passed; default = 34 passed/7 opt-in DB tests skipped. Ruff, compileall, helper shell syntax, Docker build/pip check, Compose config, import-error check, live DAG/API and post-restart state passed. Optional FileType/Graphviz CLI warnings did not affect execution/UI.
- State: API/scheduler/DAG processor/PostgreSQL/SQL Server left healthy; DAG paused and no active verification work. Metadata/log/source volumes retained. No Airflow packages installed in WSL venv. No commit created; changes remain reviewable alongside earlier uncommitted phases.
- Completion: 6/6 Phase 4 tasks, 4/10 phases complete. User clarified all Phase 4 tasks authorized. Phase 5 untouched. Next: P5.1 — dbt Core/PostgreSQL profiles, targets and connection testing, reusing previously verified versions.

### 2026-11-11 — P5.1 dbt runtime, profiles and targets
- Status: PASS. Reused installed dbt Core 1.12.6 / dbt-postgres 1.11.0 / psycopg2-binary 2.9.13 in the existing Python 3.14.4 .venv; no interpreter or dependency upgrades. Added requirements-dbt.txt using the verified pins and clarified the compatibility-probe requirements comment.
- Added dbt/dbt_project.yml, environment-only dbt/profiles.yml and scripts/dbt.py. The wrapper reads .env with exported-variable precedence; credentials never appear in command arguments. Dev uses staging/marts; test uses a separate DBT_TEST_DATABASE and verification-prefixed schemas. Custom schema macro keeps dev canonical and test isolated.
- Docker access succeeded; PostgreSQL was stopped and was started with `docker compose up -d --wait postgres`. Existing named volume/source records preserved; other services left stopped. `python scripts/dbt.py debug` passed all checks; test target connected/built repeatedly in uniquely named disposable databases. `python -m pip check` passed. Next: P5.2.

### 2026-11-11 — P5.2 Source definitions and typed staging
- Status: PASS. Thirteen dbt source definitions and thirteen staging views cover all nine Olist raw tables, FX rates/request dates, and synthetic inventory/movements. CSV JSONB becomes typed SQL values with empty optional fields null, ZIP prefixes text, original raw content preserved. Reviews/geolocation retain content-key grains rather than assume unique review IDs/ZIP prefixes.
- Grain descriptions are in dbt YAML and docs/dbt-warehouse.md. Synthetic flags/tombstones remain explicit; inventory is current state and is not represented as historical Olist stock. Build passed on real source data, with the Phase 4 operational summary retained. Next: P5.3.

### 2026-11-11 — P5.3 Dimensions
- Status: PASS. Added Type 1 dim_customer (99,441), dim_product (32,951), dim_seller (3,095), and continuous dim_date (774 days). Natural business keys are declared/tested. Customer grain is customer_id, not repeated-person customer_unique_id. Optional category translation uses a left join; untranslated/unknown categories do not drop products.
- Unique/not-null and fact-to-dimension relationship checks passed in real and disposable builds; no fabricated dimension history or source updates. Next: P5.4.

### 2026-11-11 — P5.4 Separate-grain facts and daily metrics
- Status: PASS. Added fct_order_items (112,650), fct_payments (103,886) and fct_daily_sales (774). Orders/items/payments aggregate independently by purchase day before joining. All statuses retained; delivered_item_value_brl is separately named. Payment amounts are not claimed to be recognized revenue.
- Live raw/fact/daily totals agree: item price BRL 13,591,643.70; freight 2,251,909.54; payment value 16,008,872.12. USD divides by latest stored BRL-per-USD observation on/before purchase day, at most seven days old, with actual rate_date visible. Only 8/774 days have cached FX coverage; remaining 766 days retain null USD values. No API backfill or current-rate substitution. Next: P5.5.

### 2026-11-11 — P5.5 Incremental correction and replay safety
- Status: PASS. Only the larger item fact is incremental (keyed delete+insert, unique index, fail on schema drift). Null-safe comparison of every projected attribute detects new rows, changed prices and parent-order day/status corrections without a max timestamp assumption. It scans current source/target but avoids rewriting unchanged item tuples; other marts rebuild to remove stale day aggregates.
- `python -m scripts.verify_phase5` created/dropped only its own disposable database. Actual builds verified an existing price correction, parent date/status update with unchanged source loaded_at, late new item, identical replay, physical tuple xmin/ctid preservation on no-op replay, and logical equivalence with full refresh. Raw CSV physical deletes are outside the current ingestion contract; controlled full refresh documented for removals/model changes. No speedup benchmark claimed. Next: P5.6.

### 2026-11-11 — P5.6 Grain and financial-rule documentation
- Status: PASS. docs/dbt-warehouse.md and README explain setup/targets, all grains, Type 1 choices, separate fact joins, financial/status rules, FX coverage, incremental limits and rebuild steps. A live disposable two-item/two-payment fixture yields item value 30 and payment value 34, without multiplying either; correction and insertion scenarios remain independent.
- Documentation links to official dbt incremental guidance. Airflow still executes its Phase 4 operational summary; dimensional dbt runs explicitly in WSL. No Phase 6 reporting/publication gate or DAG integration claimed. Next: P5.7.

### 2026-11-11 — P5.7 Build, generated docs and Phase 5 completion
- Status: PASS. `python -m scripts.verify_phase5` completed dev debug, repeated live builds, five disposable fixture builds (initial/correction/insertion/replay/full-refresh), and `dbt docs generate`. Each build passed 20 models + 44 data tests (64 successful resources, no warnings/errors/skips). Live mart row/content hashes remain identical after replay. Evidence: docs/phase5-evidence.json, including counts/totals, hashes, test status summary, FX coverage and changed-record results.
- Generated index.html/manifest.json/catalog.json exist in ignored dbt/target; dbt logs are ignored. README/runbook provide local docs serve command; generated artifacts are not committed. Secret scan on Phase 5 sources/evidence passed; git diff --check passed.
- Regression commands: `RUN_DB_TESTS=1 .venv/bin/python -m pytest -q` = 41 passed; default pytest = 34 passed, 7 opt-in tests skipped. Ruff for src/scripts/tests/airflow/dags, compileall, pip check passed. No changes to ingestion or Airflow logic; no dependency upgrades. No test failure required a model fix; initial Ruff Decimal-constructor findings in the new verifier were corrected and checks rerun.
- Completion: 7/7 Phase 5 tasks; 5/10 phases complete. Followed the specific request to complete all Phase 5 tasks. PostgreSQL remains healthy; other existing services remain stopped. Source data/volumes retained; changes remain uncommitted alongside prior phases. Phase 6 checklist remains untouched (basic grain/relationship tests establish Phase 5 acceptance; broader quality work is pending).
- Next: P6.1 — complete the dbt unique/not_null/relationships/accepted_values quality checks in the next requested phase.

### 2026-11-11 — P6.1 Complete dbt quality contracts
- Status: PASS. Extended staging natural-key unique/not-null/relationship checks and added composite item/payment/FX grain tests. Accepted values cover Olist order statuses, payment types (including observed not_defined), true synthetic flags, USD/BRL and ECB. Optional categories, repeated review IDs and nonunique ZIP prefixes remain permitted source contracts.
- Files: dbt/models/staging/schema.yml, dbt/macros/unique_grain.sql, dbt/dbt_project.yml. Failure relations are stored locally for diagnosis. Live candidate build passed all 110 data tests and 20 models (130 resources). Existing pinned dependencies unchanged. Next: P6.2.

### 2026-11-11 — P6.2 Custom reconciliation and mapping tests
- Status: PASS. Added dbt/tests/financial_reconciliation.sql, row_count_reconciliation.sql, missing_inventory_mapping.sql, missing_order_mapping.sql, nonnegative_amounts.sql and required_financial_fields.sql. Separate source/item/payment aggregates reconcile at purchase-day grain, including freight and delivered item value; no multiplying item/payment join or assumption that payments equal item prices.
- Both live raw/candidate data pass. Disposable fact-only corruption (payment_value_brl=999) fails financial_reconciliation; published tables remain unchanged. Inventory/movement product mappings include synthetic tombstones. Null financial values and orphan order references fail explicitly. Next: P6.3.

### 2026-11-11 — P6.3 Explicit revenue proxy
- Status: PASS. Added documented revenue_brl to fct_daily_sales and its schema description: delivered-order item prices by original purchase day, excluding freight, refunds, fees and taxes. This is a portfolio sales proxy, not recognized accounting revenue or profit. Existing delivered_item_value_brl is retained; payment_value_brl remains separate.
- Live raw delivered-item sum equals published revenue_brl: BRL 13,221,498.11. Published payment value is independently BRL 16,008,872.12. Historical status/price changes restate purchase-day metrics. FX coverage limitations remain unchanged. Next: P6.4.

### 2026-11-11 — P6.4 Duplicate and count drift detection
- Status: PASS. Natural order IDs and composite order-item/payment keys are tested independently of ingestion business_key. Added source_count_drift.sql and reviewed config/quality-baseline.json (99,441 orders / 112,650 items / 103,886 payments), with failures for more than 5% drift in either direction. Publication supplies this baseline through dbt variables; legitimate snapshot expansion requires explicit baseline review.
- Real source/fact/daily counts reconcile; disposable duplicate order/item/payment injections fail the relevant grain checks. An otherwise valid extra order triggers source_count_drift. Duplicate review IDs/ZIP prefixes are not misclassified. Next: P6.5.

### 2026-11-11 — P6.5 Real injection and correction verification
- Status: PASS. Added scripts/verify_phase6.py using a uniquely created/dropped disposable PostgreSQL database and actual dbt builds. Eight invalid scenarios: null price, duplicate order/item/payment, missing inventory product, unexpected count growth, invalid order status and missing payment-order mapping. Each fails its named relevant test, with failure samples, and preserves all seven published model row/content hashes.
- Valid initial publication, historical price correction with unchanged loaded_at and recovery replay all pass; corrected fixture revenue/item value is 35 versus payment amount 34. A separate fact corruption fails financial reconciliation. Audit counts are three published and eight failed attempts. Normal raw data is never injected/modified.
- New source-count contracts required explicit fixture baselines in the existing Phase 5 verifier, including the intentionally inserted third item. Only fixture configuration changed; ran its changed_rows routine successfully across initial/correction/insertion/replay/full-refresh with all 110 new tests, preserving no-op tuple checks. Next: P6.6.

### 2026-11-11 — P6.6 Structured quality reports and audit
- Status: PASS. src/quality/publication.py writes docs/quality-report.json with run ID, baseline/tolerance, each check name, expected zero violating rows, actual violation count, PASS/FAIL, dbt status and bounded failing-key samples. Skipped/error/missing results have unknown counts and fail closed. Only approved key columns are extracted; raw row bodies/credentials are excluded. metadata.quality_runs (sql/init/006_quality.sql) persists build/publication attempts.
- docs/phase6-evidence.json retains separate reports for all invalid fixtures plus recovery, live revenue and audit counts. docs/data-quality.md and README explain rules, consumer schemas, revenue, baseline, reports, recovery, source locks and local-superuser limits. Secret scan of changed source/report files passed. Next: P6.7.

### 2026-11-11 — P6.7 Publication gate and Phase 6 completion
- Status: PASS. Added candidate target (candidate_staging/candidate_marts) and explicit `python -m src.quality.publication`. Each run uses fresh artifacts, full candidate rebuild and existing CSV/FX/stock advisory locks plus a publication lock. All enabled tests and models must pass; failed/skipped/missing/error results close the gate. All seven published tables plus success audit update in one DELETE/INSERT transaction. Failures preserve the prior publication. Developer marts/candidates are not consumer output; consumers use published.
- `python -m scripts.verify_phase6` completed all injection/correction/replay scenarios and live publication: 20 models + 110 tests passed; eight deliberate bad-input builds and the corruption-only test failed as expected. Live published/candidate hashes agree. No source data, ingestion code, Airflow DAG or dependency pins changed. Publication remains an explicit WSL workflow, not an unimplemented Airflow claim.
- Added seven unit gate checks for complete success and rejection of skipped/error/warn/nonzero-failure/missing-model/missing-test results. Final validation: `RUN_DB_TESTS=1 .venv/bin/python -m pytest -q` = 48 passed; default pytest = 41 passed/7 skipped. Ruff, compileall, pip check and git diff --check passed. Initial Ruff exception/import formatting findings were corrected and rechecked. Existing Phase 5 changed-row verification also passes the expanded tests.
- Completion: 7/7 Phase 6 tasks, 6/10 phases complete. Followed the specific request to complete all Phase 6 tasks. PostgreSQL remains healthy; other services remain stopped. Disposable databases removed, persistent volumes/raw sources retained. No commit created; prior phase changes remain intact. No Phase 7 checkbox changed.
- Next: P7.1 — review/complete ingestion unit test coverage within the automated testing/CI phase, reusing the existing tests rather than repeating completed work.

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
