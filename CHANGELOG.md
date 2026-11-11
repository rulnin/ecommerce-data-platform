# Changelog

## 1.0.0 — 2026-11-11

- Integrate historical Olist CSVs, dated ECB FX and explicitly synthetic SQL Server inventory.
- Add transactional/idempotent ingestion, source audits, committed-sequence updates/deletes and recovery.
- Orchestrate ingestion and operational checks with bounded LocalExecutor Airflow services.
- Model separate item/payment facts in dbt; validate candidates before atomic consumer publication.
- Provide eight business SQL analyses, diagrams, actual screenshots, failure evidence and hosted CI.
- Measure replay/index behavior and verify warehouse backup/restore against all user tables.

Scope: local portfolio, not a production deployment. Dimensional publication runs
explicitly outside the Airflow DAG. Historical FX coverage is partial. Synthetic
inventory is not real Olist stock. Dataset-derived aggregates retain Olist attribution
and CC BY-NC-SA 4.0 data terms. See README and docs/release-verification.md for evidence.
