# Performance baseline and targeted indexes

Executed on 2026-11-11T10:59:16.467654+00:00. Data fingerprints and all measured samples are in [Phase 8 evidence](phase8-evidence.json).

## Workload and environment

The nine reviewed Olist CSVs total 126,186,995 bytes. All SHA-256 hashes match docs/dataset-manifest.json. Batch size is 1000. Python 3.14.4, x86_64, 16 logical CPUs; existing PostgreSQL 17.11 container limited to 1 GiB. SQL Server/Airflow were stopped. This tests CSV ingestion and one investigation query, not the whole orchestrated multi-source stack.

Use `python -m scripts.verify_phase8` with PostgreSQL healthy and other loaders idle. It creates/drops only its disposable benchmark/restore DBs, retains a private ignored dump, and applies the additive lookup indexes only after measured benefit. Existing warehouse rows are unchanged. Full measurements include source parsing, hashing, deduplication, COPY/upsert and audits; they exclude source download and target validation queries.

## Actual load timings

| Run | Caller wall seconds | DB audit seconds | Status |
|---|---:|---:|---|
| initial-empty-full | 96.835 | 96.717 | success |
| full-replay-1 | 82.572 | 82.507 | success |
| full-replay-2 | 76.163 | 76.112 | success |
| full-replay-3 | 73.421 | 73.358 | success |
| incremental-replay-1 | 4.902 | 4.878 | success |
| incremental-replay-2 | 4.965 | 4.934 | success |
| incremental-replay-3 | 4.994 | 4.959 | success |
| forced-failure | 3.005 | 2.946 | failed |
| recovery | 5.124 | 5.087 | success |

Median existing-target full replay: **76.163 s**; median day replay: **4.965 s** (15.34× wall-time ratio). Initial empty-target full load is a separate observation, not a cold-cache claim.

Incremental slices use 2017-11-24 inclusive to 2017-11-25 exclusive. They reuse unchanged reference hashes but still hash files and scan order-associated CSVs; fewer accepted/written rows do not imply zero scanning. All reruns were against already populated data: this is idempotent replay cost, not new-arrival throughput. Accepted/scanned/unchanged counts are retained per source/run in the JSON.

| Raw table | Rows / distinct business keys |
|---|---:|
| customers | 99,441 / 99,441 |
| orders | 99,441 / 99,441 |
| order_items | 112,650 / 112,650 |
| order_payments | 103,886 / 103,886 |
| order_reviews | 99,224 / 99,224 |
| products | 32,951 / 32,951 |
| sellers | 3,095 / 3,095 |
| category_translation | 71 / 71 |
| geolocation | 738,332 / 738,332 |

Independent totals remain price BRL 13,591,643.70; freight BRL 2,251,909.54; payments BRL 16,008,872.12. Failure/recovery and all six replays preserve these totals and source watermarks.

## Selective SQL before/after

The workload in sql/queries/day_item_total.sql finds Black Friday orders then their items, without joining payments. Five EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) samples follow one explicit warm-up before and after indexes, with the same session/settings/data and refreshed statistics. No planner disabling, cache flushing or server-memory changes.

Before execution samples (ms): [77.511, 83.078, 80.229, 66.877, 71.578]; median **77.511 ms**.
After execution samples (ms): [8.02, 6.317, 8.626, 7.053, 7.389]; median **7.389 ms**.
Observed median ratio: **10.49×** for this query only. Result unchanged: 1366 items / BRL 152653.74.

Before plan nodes:

```json
[
  {
    "Node Type": "Aggregate",
    "Plan Rows": 1,
    "Actual Rows": 1,
    "Actual Loops": 1
  },
  {
    "Node Type": "Gather",
    "Plan Rows": 497,
    "Actual Rows": 1176,
    "Actual Loops": 1
  },
  {
    "Node Type": "Seq Scan",
    "Relation Name": "orders",
    "Plan Rows": 207,
    "Actual Rows": 392,
    "Actual Loops": 3
  },
  {
    "Node Type": "Hash Join",
    "Plan Rows": 279935,
    "Actual Rows": 1366,
    "Actual Loops": 1
  },
  {
    "Node Type": "Seq Scan",
    "Relation Name": "order_items",
    "Plan Rows": 112650,
    "Actual Rows": 112650,
    "Actual Loops": 1
  },
  {
    "Node Type": "Hash",
    "Plan Rows": 497,
    "Actual Rows": 1176,
    "Actual Loops": 1
  },
  {
    "Node Type": "CTE Scan",
    "Plan Rows": 497,
    "Actual Rows": 1176,
    "Actual Loops": 1
  }
]
```

After plan nodes:

```json
[
  {
    "Node Type": "Aggregate",
    "Plan Rows": 1,
    "Actual Rows": 1,
    "Actual Loops": 1
  },
  {
    "Node Type": "Bitmap Heap Scan",
    "Relation Name": "orders",
    "Plan Rows": 994,
    "Actual Rows": 1176,
    "Actual Loops": 1
  },
  {
    "Node Type": "Bitmap Index Scan",
    "Index Name": "orders_purchase_text_idx",
    "Plan Rows": 994,
    "Actual Rows": 1176,
    "Actual Loops": 1
  },
  {
    "Node Type": "Nested Loop",
    "Plan Rows": 1274,
    "Actual Rows": 1366,
    "Actual Loops": 1
  },
  {
    "Node Type": "CTE Scan",
    "Plan Rows": 994,
    "Actual Rows": 1176,
    "Actual Loops": 1
  },
  {
    "Node Type": "Index Scan",
    "Relation Name": "order_items",
    "Index Name": "order_items_order_id_idx",
    "Plan Rows": 1,
    "Actual Rows": 1,
    "Actual Loops": 1176
  }
]
```

Full estimates, actual rows/loops and buffer counts are in [before-plan.json](performance/before-plan.json) and [after-plan.json](performance/after-plan.json). EXPLAIN execution time excludes parsing/planning and client transfer and includes instrumentation overhead; see [PostgreSQL EXPLAIN](https://www.postgresql.org/docs/17/using-explain.html).

## Index costs and scope

sql/init/008_lookup_indexes.sql adds B-trees on raw order purchase timestamp text and raw item order_id text. Combined measured size: 10,084,352 bytes; build statement wall time: 0.394 seconds in the disposable database.
The exact expression predicates must match; text-date range ordering is valid for this reviewed canonical YYYY-MM-DD HH:MM:SS Olist snapshot, not arbitrary timezone/date strings. Timestamp casts and unrelated broad scans may not use these indexes. They add disk, cache pressure and index maintenance for inserts or changed JSONB values. No write-throughput benefit or measured write-penalty percentage is claimed. Original CSV full/incremental timings precede these indexes; these indexes optimize investigation SQL and do not remove CSV scan costs.

Ordinary CREATE INDEX was safe for this idle local warehouse. On an actively written system, plan lock budget/maintenance or an appropriate concurrent migration. Existing PK and item-fact unique indexes are retained; no indexes are dropped.

## Audit, recovery and restore

The deliberate failed batch records error code simulated_failure and 1 rejection. Its subsequent recovery succeeds with no row/checkpoint drift. [Sanitized pipeline log](performance/pipeline.txt) contains run UUIDs and codes; audit durations/counts/errors are in the evidence. Log timestamps use WSL Asia/Bangkok; evidence timestamps are UTC.

Warehouse dump: 181,669,260 bytes; dump 25.354 s; restore 37.328 s. All 153 user tables have identical row counts and canonical row hashes after restoring into a new DB. Original fingerprints also remain unchanged. The dump stays ignored under data/backups; only its hash, size and validation metrics are recorded.

Use the [operations runbook](runbook.md) for replay, failure triage, source cursor cautions, backup/restore and resource handling. PostgreSQL references: [pg_dump](https://www.postgresql.org/docs/17/app-pgdump.html), [pg_restore](https://www.postgresql.org/docs/17/app-pgrestore.html).

## Limits

- Single WSL host; sequential fixed-order trials, no cache reset or statistical confidence interval.
- One empty-target load and three existing-target replays per mode; incremental is a simulated historical day, not live CDC.
- A brief eight-test PostgreSQL regression run overlapped the first full replay; background WSL/autovacuum noise is not controlled.
- Docker samples are not peak memory; Python peak RSS is per process and excludes PostgreSQL.
- Selective-query speedup is not ingestion or end-to-end pipeline speedup.
- Backup/restore verifies the warehouse DB only, not Airflow metadata/SQL Server/role secrets.

Python peak RSS: 48,572 KiB. Docker before/after memory/CPU samples and exact server settings remain in the evidence; they are not peak utilization measurements.
