# Warehouse quality and publication

Run from the repository root with the existing `.venv` and populated raw sources:

```bash
source .venv/bin/activate
python -m src.quality.publication
# Nonzero exit status means nothing was published.
python -m scripts.verify_phase6
```

The publication command is the supported path to consumer tables under
`published`. The existing `marts` schema is developer output, and
`candidate_marts` is build output that may be incomplete after a failure.
Consumers must not read either as validated results. The Phase 4 Airflow DAG
continues to run operational ingestion checks; it does not publish dimensional
models. Quality publication is an explicit WSL command in this phase.

## Rules

- Staging natural keys and model grains have unique/not-null checks. Item/payment
  grains use composite uniqueness as well as the raw content/business key.
- Customer/order/product/seller references and synthetic inventory/movement
  product mappings must exist, including tombstones. Unknown category translations
  are permitted source findings; geolocation ZIP and review IDs are not unique.
- Order status uses Olist's created/approved/invoiced/processing/shipped/delivered/
  unavailable/canceled vocabulary. Payment types include credit_card, boleto,
  voucher, debit_card, and not_defined (observed in the public snapshot).
  Synthetic flags must be true and FX currencies/provider fixed to USD/BRL/ECB.
- Required financial fields may not be null; item price, freight and payment
  values may not be negative. Zero is allowed, consistent with the source.
- Raw source counts must reconcile to fact and daily counts. Financial values
  reconcile separately for items, freight and payments at purchase-day grain,
  with exact numeric equality. There is no item-to-payment many-to-many join
  and no assertion that payment value equals item price.
- Expected snapshot counts live in `config/quality-baseline.json`. Drift exceeding
  5% in either direction fails. The checked-in baseline is 99,441 orders,
  112,650 items, and 103,886 payments. A legitimate expanded snapshot needs an
  explicitly reviewed baseline change, rather than automatically accepting the
  latest counts. Disposable fixtures supply their own baseline. Standalone dbt
  tests use the same default counts; the publication command passes the canonical
  config file through dbt variables. No external dbt package is required.

## Revenue definition

`revenue_brl` is the sum of item prices for orders whose current status is
`delivered`, grouped by original purchase date. It excludes freight, refunds,
marketplace fees and taxes; it is a portfolio sales proxy, not accounting
recognized revenue or profit. It equals the existing explicitly named
`delivered_item_value_brl`. Late status/price corrections restate the purchase
day. Payments remain independent tender amounts and are not revenue. The custom
financial test compares the published candidate proxy with raw delivered items.
Historical FX limitations from the warehouse contract remain: USD metrics are
null without a stored observation at most seven days old, and they are not a
complete reporting-currency revenue measure.

## Publication protocol

`src/quality/publication.py` obtains a publication advisory lock plus the existing
CSV, FX and synthetic-stock loader locks. Busy sources fail immediately, and
cooperating loaders cannot change raw data during candidate build/test/copy.
It uses a unique temporary artifact directory so stale run_results cannot open
the gate. The fixed candidate target builds separate staging/mart schemas in the
same configured PostgreSQL database. Every run uses full refresh here to make
publication reflect deletions as well as corrections; the developer incremental
model and its Phase 5 behavior remain available outside this command.

A successful dbt process, every enabled test passing, and every model completing
successfully are all required. Failed/skipped/missing/error results keep the gate
closed. Failing test relations are retained in `candidate_dbt_test__audit` for
local diagnosis. A failed candidate never replaces the last good published data.

On success, all seven consumer tables and a `metadata.quality_runs` success audit
are updated in one PostgreSQL transaction. Transactional DELETE/INSERT preserves
MVCC snapshots, unlike TRUNCATE. A copy/schema error rolls back every table and
records failure separately. Existing table structure is retained; schema changes
require an explicit reviewed migration and fail rather than silently changing
consumer columns. Readers needing consistency across several queries should use
a repeatable-read transaction. A report file is written after the database audit;
the database record is authoritative if local artifact writing is interrupted.

This is a cooperative local workflow, not an access-control boundary against the
local PostgreSQL superuser or direct manual SQL. Keep ad hoc dbt builds/SQL idle
during publication; only the publication command owns candidate schemas. No
production RBAC or automatic Airflow integration is claimed.

## Reports and recovery

`docs/quality-report.json` contains run ID, baseline/tolerance, overall status,
published flag, and each check's name, expected zero violating rows, actual count,
PASS/FAIL, underlying dbt status and up to five failing keys. Null actual counts
mean an error, skipped or missing result, never a pass. Only approved key columns
are copied from failure tables; raw row bodies and credentials are excluded.
`metadata.quality_runs` retains all attempts that reach candidate build rather
than overwriting the last failure. A busy-source preflight aborts before this
audit and leaves the previous report file in place; its command exits nonzero. The latest file represents one attempt; the verification evidence keeps
separate reports for each deliberately invalid fixture.

To recover, inspect the report and local failure relations, correct the source
through its normal ingestion path, and rerun publication. Do not alter published
tables or weaken tests to hide an invalid candidate.

The Phase 6 verifier creates a uniquely named disposable database and uses real
dbt builds. It tests valid initial publication; null values; duplicate order,
item and payment business keys; a missing synthetic product mapping; unexpected
row-count growth; invalid status; missing order mapping; a valid historical price
correction and replay. Every bad input must fail its relevant test and leave all
seven published table hashes unchanged. A separate fact-only corruption must
fail the financial test. Only the verifier's disposable database is dropped.
Real source records and existing volumes are not modified.
