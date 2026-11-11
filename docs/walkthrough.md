# Four-minute portfolio walkthrough

Target: approximately four minutes at 120–140 words per minute. This script is
about 480 spoken words; timing is estimated, not a recorded rehearsal. Open the
README, analytics-results.md, data-model.md, the Airflow screenshots, and the
hosted CI run before presenting. A live pipeline run is not needed during the
short presentation; source ingestion takes longer than the walkthrough.

## 0:00–0:35 — Business problem and sources

“I built a local e-commerce data platform to answer business questions without
silently double counting money. It combines the public Olist order snapshot,
dated ECB reference rates through a REST API, and synthetic inventory in SQL
Server. The inventory is generated demo data, and the CSV dates simulate batch
arrivals. I do not present either as a real live business feed.”

## 0:35–1:20 — Data flow and operational safety

“Python loaders persist original source values and run audit metadata in
PostgreSQL. CSV batches use stable keys and transactional writes. The FX client
uses bounded retries, validates the rate direction and retains the actual rate
date. SQL Server changes use a commit-ordered sequence, including deletion
tombstones, so identical update timestamps do not lose changes.

Airflow schedules those loaders, records task attempts and supports historical
backfill and recovery. Its current transform is an operational summary. The
dimensional dbt build and publication are explicit WSL commands, outside that
DAG. I keep Airflow's constrained dependencies separate from the host venv.”

## 1:20–2:10 — Model and quality gate

“Here is the grain of the warehouse: customers, products, sellers and dates are
dimensions; items and payments are separate facts. An order with two items and
two payments would produce four rows in a naive join. I aggregate each fact
before combining metrics.

Revenue here is a clearly labeled proxy: delivered-order item prices by purchase
day, excluding freight and refunds. Payment value is a different measure. dbt
tests keys, mappings, accepted values, count drift and financial reconciliation.
Only a fully passing candidate can replace the seven published tables in one
transaction. The previous publication remains available when a candidate fails.”

## 2:10–2:55 — Business results

“Across the historical snapshot, there are 99,441 orders and BRL 13.22 million in
delivered item value. Health and beauty contributes the most delivered item
value among categories, and credit cards represent 78.34 percent of payment
value. Repeat buyers account for 3 percent of people with delivered orders in
this snapshot; that is not a cohort-retention claim.

The FX cache covers only 8 of 774 calendar days, or 3.73 percent of orders.
I expose missing coverage instead of inventing a complete USD total. Every table
in this report links to the SQL that produced it.”

## 2:55–3:45 — Evidence and trade-offs

“The repository includes actual failed and recovered Airflow screenshots, eight
bad-input publication scenarios, and a successful hosted GitHub Actions run.
The lightweight suite has 54 tests and does not require cloud credentials.
I also measured CSV replays: median full replay was 76.2 seconds and daily replay
5.0 seconds on this WSL host. Those are different workloads, not streaming
throughput. A targeted lookup query improved with two measured indexes.

I verified a warehouse dump and restore by matching all 153 user tables.
The runbook explains which other services need separate backups. Local Docker
keeps the project affordable and reproducible; cloud deployment, production
hardening and automatic dimensional orchestration remain separate work.”

## Optional live demonstration after the presentation

```bash
source .venv/bin/activate
python -m scripts.verify_phase9
# Inspect docs/analytics-results.md and the SQL files.
```

This is read-only and needs an already validated publication. For an empty
checkout, follow the README source-loading/publication steps first. Do not run
the full benchmark or deliberately corrupt data during the short presentation.

## CV project entry

**E-Commerce Data Platform — Python, PostgreSQL, SQL Server, Airflow, dbt, Docker**

Built a local analytics pipeline for 99,441 historical Olist orders, dated ECB FX
and synthetic SQL Server inventory. Implemented transactional idempotent ingestion,
sequence-based updates/deletes, separate item/payment facts and a tested atomic
publication gate; verified 54 automated tests and hosted GitHub Actions. Published
eight reproducible business SQL analyses and verified warehouse backup/restore.

## LinkedIn project description

A local-first data engineering portfolio combining public Olist e-commerce data,
historical ECB exchange rates and synthetic SQL Server inventory. Python loaders,
PostgreSQL, Airflow and dbt demonstrate repeatable ingestion, correction/deletion
handling, quality-gated publication and business analytics without item/payment
double counting. Includes actual failure/recovery evidence, hosted CI and measured
local benchmarks. Inventory is simulated; dimensional publication runs explicitly
outside the current Airflow DAG. Repository: https://github.com/rulnin/ecommerce-data-platform

These are draft descriptions for the user's CV/profile, not claims of employment,
production deployment, company ownership, AWS experience or commercial results.
No external profile was edited or message sent.
