# Phase 2 CSV ingestion

This is a historical-snapshot loader with simulated arrivals, not live CDC. It
creates nine raw tables and metadata; no mart or dimensional-model logic is added.

## Run and verify

From the repository root after Phase 1 setup:

```bash
source .venv/bin/activate
docker compose up -d --wait postgres
python -m src.ingestion.csv_pipeline --batch-id full-olist-v2
python -m src.ingestion.csv_pipeline --batch-id day-2017-11-24 \
  --start 2017-11-24 --end 2017-11-25
python -m pytest -q
RUN_DB_TESTS=1 python -m pytest -q
python -m scripts.verify_phase2
```

Integration tests create uniquely named disposable databases and drop only those
test databases. The real-data verification script never deletes warehouse rows;
unexpected extra keys fail verification instead. `--full-run UUID` can reuse a
successful full load. The report defaults to docs/phase2-evidence.json and contains
aggregates/run IDs rather than row samples.

The additive sql/init/002_csv_raw.sql migration is executed by the loader before
loading, including on existing Docker volumes. It is not an entrypoint mount.
CREATE TABLE IF NOT EXISTS does not migrate incompatible existing definitions;
future structural changes need a new additive migration. No existing tables are
truncated/dropped. Docker/DB access in this AI session needs approved execution
outside the sandbox; a normal WSL terminal can run the commands directly.

## Raw contract and keys

All source fields remain original strings in a JSONB `data` payload. Empty strings
and leading zeroes are retained; timestamp text has no invented timezone. Financial
strings are checked with Decimal for finite, nonnegative values. Typed staging and
warehouse business rules remain later work.

| Raw table | business_key primary key |
|---|---|
| customers | JSON array of customer_id |
| orders | JSON array of order_id |
| order_items | JSON array of order_id, order_item_id |
| order_payments | JSON array of order_id, payment_sequential |
| products | JSON array of product_id |
| sellers | JSON array of seller_id |
| category_translation | JSON array of product_category_name |
| order_reviews | SHA-256 of all canonical source fields |
| geolocation | SHA-256 of all canonical source fields |

Distinct review versions are preserved, because review_id is not unique. Exact
review/geolocation duplicates collapse; original CSVs are unchanged. A changed
review or coordinate becomes a new row rather than replacing prior content.
SHA-256 collision risk is accepted. These raw tables are not unique order-review
facts or postcode dimensions. Natural-key tables reject duplicate input keys,
even if identical, instead of picking an arbitrary winner.

PostgreSQL enforces primary keys, nonempty key fields, JSON object payloads, hash
shape and run-provenance foreign keys. Cross-source foreign keys are intentionally
deferred: independently loaded raw sources and known inconsistencies must remain
inspectable. src/ingestion/contracts.json declares exact headers and key fields.

Each row stores row_hash, first/last run IDs and loaded_at. Unchanged hashes leave
rows/timestamps untouched. Changed natural-key values upsert. Full mode is an
upsert sweep, not replacement: absent keys are not deleted. The source has no
authoritative change sequence, so an older modified snapshot can overwrite a newer
value. Replay only the intended authoritative snapshot; hashes make it auditable.

## Transactions, checkpoints and simulated arrivals

Python buffers at most INGEST_BATCH_SIZE records (1–10,000). COPY streams batches
into a PostgreSQL temporary table; the database sorts/deduplicates/merges there and
may spill to disk. Date filtering also holds an order-ID set, so this is not an
arbitrary-scale constant-memory claim. All source merges, successful run status
and checkpoints commit together. Run creation and input fingerprints commit
separately so failures remain visible. A session advisory lock serializes cooperating
CSV writers, with bounded connection, statement and lock waits. Transaction bodies
are not automatically retried.

Date ranges are start-inclusive/end-exclusive in the original purchase-date text,
without timezone conversion. Both boundaries are required together. Selected orders
determine item/payment/review membership. Changed reference files load fully;
unchanged reference-file hashes skip parsing/writes and report zero scanned/accepted
with an explicit skipped flag. Input hashing still reads the files.

Late order/payment/review changes require replaying the original purchase-date
window or full mode. This is not selection by review creation date or true update
watermark. Replays/backfills are always allowed; checkpoints never suppress them.
Watermarks are maximum processed simulation boundaries, not proof of contiguous
completeness: full uses max observed purchase date, incremental uses end minus one
day. Per-source watermarks never regress; reference dates track the simulation,
not an observed independent reference update timestamp.

metadata.ingestion_runs stores source, batch ID, unique attempt UUID, status,
timestamps, input SHA-256 values, per-source counts and sanitized error code.
metadata.checkpoints stores source, batch ID, watermark, successful run ID and time.
Repeated batch IDs produce new attempts. Counts include scanned, accepted, inserted,
updated, unchanged and deduplicated. Failed-run partial counts describe attempted
work rather than committed rows.

Invalid amounts/keys/purchase timestamps, structural CSV errors and duplicate
natural keys fail the whole run. metadata.rejections records source, record/field
where available and error code without row contents or credentials. Correct the
reported input/configuration and replay the same batch ID. No rejected row silently
enters raw tables. Failure injection is a Python verification hook:
`run(settings, batch_id, start, end, fail_source="order_items")`.

A killed process or lost DB connection can leave a running audit attempt because
the client cannot write failure status. PostgreSQL rolls back uncommitted data;
confirm the old session is gone before starting another attempt. Never treat that
stale audit row as success. External writers that bypass the advisory lock are not
protected. Reference-file skipping assumes no manual raw-table corruption; full
mode can repair changed payloads but never silently removes extra keys.

## Measured evidence

docs/phase2-evidence.json records the real full load, a date batch, three identical
reruns, forced rollback and recovery. Every step preserves counts, unique keys,
watermarks and independent financial totals.

| Source | CSV records | Unique raw rows |
|---|---:|---:|
| customers | 99,441 | 99,441 |
| orders | 99,441 | 99,441 |
| order_items | 112,650 | 112,650 |
| order_payments | 103,886 | 103,886 |
| order_reviews | 99,224 | 99,224 |
| products | 32,951 | 32,951 |
| sellers | 3,095 | 3,095 |
| category_translation | 71 | 71 |
| geolocation | 1,000,163 | 738,332 |

Geolocation collapses 261,831 exact duplicates. Duplicate target keys are zero.
Separate source/target Decimal sums match: item price BRL 13,591,643.70; freight
BRL 2,251,909.54; payments BRL 16,008,872.12. These are snapshot totals, not
delivered-order revenue, and they are never joined at mismatched grains.
2017-11-24 selects 1,176 orders, 1,366 items, 1,214 payments and 1,175 reviews;
all are unchanged after the full load. Disposable-database tests additionally prove
new-day insertion, changed-value upsert, invalid-row rollback, constraints and
checkpoint preservation. No benchmark or orchestration success is claimed.
