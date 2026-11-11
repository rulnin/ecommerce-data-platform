# v1.0.0 release verification

## Scope and clean checkout

Verification date: 2026-11-11. A release candidate was committed/pushed, then cloned from GitHub into a new directory. The test started with a clean Git status, a fresh uv-created Python 3.14.4 environment, freshly downloaded source files and a separate Compose project with new PostgreSQL/SQL Server/Airflow-log volumes and nonconflicting localhost ports. Working warehouse data and checkpoints were rechecked unchanged.

Clean candidate commit: `b2390cecde76366552a3221ce833351bbc27b7e4` on `release/v1.0.0`. [Candidate hosted CI](https://github.com/rulnin/ecommerce-data-platform/actions/runs/43014478035) passed. Final publication/tag and CI details are captured in [phase10-evidence.json](phase10-evidence.json). The final code differs only by the targeted statistics fix below plus release documentation; that fix was validated independently against both DBs.

## Commands actually exercised

| Clean-clone step | Exit | Seconds |
|---|---:|---:|
| uv-created Python 3.14.4 venv | 0 | 1.068 |
| install pinned dbt runtime | 0 | 18.478 |
| pip dependency consistency | 0 | 0.215 |
| new PostgreSQL volume | 0 | 6.094 |
| fresh publisher dataset download | 0 | 64.798 |
| CSV source profile | 0 | 8.443 |
| fresh CSV full ingestion | 0 | 60.081 |
| fresh historical FX ingestion | 0 | 0.868 |
| install pinned SQL Server connector | 0 | 1.621 |
| native ODBC clean setup | 0 | 7.698 |
| new SQL Server volume | 0 | 12.607 |
| seed independent synthetic source | 0 | 0.967 |
| fresh SQL Server extraction | 0 | 1.720 |
| dbt connection | 0 | 1.619 |
| dbt build and tests | 0 | 12.805 |
| dbt generated docs | 0 | 2.773 |
| quality-gated publication | 0 | 14.160 |
| read-only business queries | 0 | 1.318 |
| Airflow fresh metadata/build/start | 1 | 7.088 |
| Airflow setup retry with corrected harness environment | 0 | 33.691 |
| Airflow success failure recovery and backfill | 0 | 98.371 |
| all lightweight tests lint formatting unit | 0 | 0.616 |
| all lightweight DB integration checks | 0 | 2.722 |
| stop independent heavy services | 0 | 10.703 |

The initial Airflow invocation failed because the external verification harness exported empty AIRFLOW secret placeholders over secrets newly written to .env. The README does not export these blanks. Removing those harness overrides let the unchanged setup script complete. This failure/retry is retained rather than hidden or misrepresented as a first-attempt success. No working Docker installation, socket permissions or system interpreter was altered.

## End-to-end results

- Fresh publisher archive produced all nine reviewed CSV SHA-256 hashes.
- CSV, live historical FX and native-ODBC SQL Server extraction succeeded on independent source state.
- Warehouse contains 99,441 orders, 112,650 items and 103,886 payment entries; delivered item value BRL 13,221,498.11 and tender value BRL 16,008,872.12.
- New synthetic source has 100 mapped inventory products and committed cursor 200, distinct from the working demo source. It is not real stock.
- dbt debug/build/docs succeeded: 20 models and 110 tests. [Fresh quality report](release-evidence/quality-report.json) confirms publication.
- Eight read-only business analyses reconciled to source/daily totals.
- Fresh Airflow metadata/services ran seven final successful DAG scenarios, including deliberate failure/recovery and native historical backfill. DAG paused afterward; [fresh DAG evidence](release-evidence/airflow.json).
- Shared scripts passed 46 unit and 8 disposable-PostgreSQL integration tests, with lint/format/compile checks.
- Source-only loaders, explicit dbt publication and operational Airflow remain separate documented execution boundaries. No automatic dimensional DAG, complete FX coverage, production HA or AWS deployment is claimed.

## Review and targeted fix

The installed expression indexes originally had no expression statistics in the persistent warehouse. The planner estimated 279,935 joined rows versus 1,366 actual and used an item-table scan. sql/init/008_lookup_indexes.sql now runs ANALYZE on the two source tables after index creation. The same 1,366-item / BRL 152,653.74 result uses both indexes; a concurrent-stack smoke test took 6.788 ms. This is a review check, not a replacement benchmark. Phase 8 samples remain their original measured observations; future migration timing also includes statistics collection. The revised migration was also applied successfully in the clean warehouse.

Existing transactional replay, source sequence guards, safe failure reports, candidate gate and stop/recovery paths were reviewed against tests/runbooks. Full benchmarks, old source mutation scenarios and earlier screenshots were not needlessly regenerated. The new functional run uses independent source state instead of editing working stock.

## Source and artifact hygiene

The release snapshot is checked for actual local .env secret values, private-key/PAT patterns, disallowed local files and oversized artifacts; tracked Git history is reviewed as well. No CSV, dump, ZIP, local venv/ODBC runtime, real .env or keys are included. Public Olist aggregates, synthetic fixtures and project-local audit UUIDs are intentional evidence; they are not employer/company data or private internal endpoints. Dataset attribution/data terms remain in data-rights.md. This records the checks performed, not an assertion that a regex can certify arbitrary third-party content.

Only the new review project containers/network were removed after stopping heavier services. Named review volumes were retained. The working PostgreSQL container remains healthy; its original CSV metrics/checkpoints and synthetic quantity remain unchanged. No down -v, force push, database reset or destructive cleanup was used. Temporary verification tooling remains outside the repository.

## Interview/profile completion

The [interview Q&A dry run](interview-qa.md) covers duplication, crash/checkpoint boundaries, sequence ordering, deletes, financial grain, publication, FX, performance, recovery and scaling, checked against the executed implementation/evidence. This is an agent-led technical rehearsal; no human spoken interview is claimed. The repository pin was confirmed through GitHub after the user pinned it. The user explicitly waived the CV update; no CV/profile text was edited.

## Reproduce

Use the README from the released source. For parallel review, select a distinct COMPOSE_PROJECT_NAME and POSTGRES_PORT/SQLSERVER_PORT/AIRFLOW_PORT in the review .env, and use fresh credentials/volumes. Do not export empty generated AIRFLOW secrets; let setup read its updated .env. Load sources, run dbt/publication, generate business results, then run airflow.sh setup and scripts.verify_phase4. Stop/down only the review project and preserve working volumes. Lightweight CI uses the shared check script and ephemeral DB; full-stack verification is recorded separately.

## Publication confirmation

[v1.0.0 release](https://github.com/rulnin/ecommerce-data-platform/releases/tag/v1.0.0)
is published, not a draft/prerelease. Annotated tag resolves to
`2d9327c8fa8d0f96dabc701be8ac62170ab8a206`, which passed
[final code CI](https://github.com/rulnin/ecommerce-data-platform/actions/runs/43016218630).
The repository default is now main. The tag freezes that tested implementation;
main also carries post-publication confirmation/checklist evidence. No tag was
moved and no existing history was rewritten. All ten phases are complete under
the user-approved scope; the CV update was waived and the project pin verified.
