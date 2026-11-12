# dbt dimensional warehouse

The project uses dbt Core 1.12.6 / dbt-postgres 1.11.0. Host commands use the
Python 3.14.4 `.venv`. Airflow invokes warehouse publication and analytics through
an isolated `/opt/warehouse` Python environment in its image, keeping its own
constrained dependencies separate. See [Airflow](airflow.md) for the automated
workflow and [Metabase](metabase.md) for dashboard setup.

## Setup and commands

From the repository root, after loading the Phase 2/3 raw sources:

```bash
source .venv/bin/activate
python -m pip install -r requirements-dbt.txt
python -m pip check
docker compose up -d --wait postgres
python scripts/dbt.py debug
python scripts/dbt.py build
python scripts/dbt.py docs generate
python scripts/dbt.py docs serve --host 127.0.0.1 --port 8081
```

The wrapper reads `.env` without printing credentials; exported environment
variables take precedence. The checked-in `dbt/profiles.yml` contains only
`env_var` references. It connects to the existing warehouse database using
POSTGRES_HOST/PORT/DB/USER/PASSWORD. `dev` builds in canonical `staging` and
`marts`; `test` requires a separate DBT_TEST_DATABASE (default ecommerce_dbt_test)
and prefixes output schemas with `verification_`. The verification script creates
and removes a uniquely named disposable database; the local developer role needs
CREATEDB. No source database or existing volume is reset.

Generated `dbt/target/index.html`, `manifest.json`, and `catalog.json` are local,
ignored artifacts. Regenerate and serve them to browse lineage, descriptions,
column tests, SQL and catalog. Generated files can contain local database names
and are intentionally not committed. Dependency pins reproduce the tested direct
versions; transitive dependencies are not fully locked. No dbt packages are used.

## Layers and grains

Every raw source has a staging view. JSONB CSV strings become typed values;
empty optional fields become null, ZIP prefixes stay text (leading zeroes matter),
source timestamps remain timezone-naive Brazilian local time, and raw originals
are retained. Invalid casts fail the model instead of silently losing records.
The staging schema also retains the operational Phase 4 summary untouched.

| Model | Grain and rule |
|---|---|
| stg_customers / orders / products / sellers | One original customer_id / order_id / product_id / seller_id |
| stg_order_items | order_id + order_item_id |
| stg_order_payments | order_id + payment_sequential |
| stg_order_reviews | Raw content business key; repeated review_id preserved |
| stg_category_translation | Portuguese category name |
| stg_geolocation | Distinct content key; ZIP prefix is not unique |
| stg_fx_rates | USD/BRL + observed date, fixed ECB provider, BRL per USD |
| stg_fx_requests | Requested day mapping to observed day |
| stg_inventory / stock_movements | Synthetic product_id / movement_id; retain tombstones and synthetic flag |
| dim_customer | customer_id; customer_unique_id is a repeat-person identifier, not unique here |
| dim_product | product_id; optional category translation left joined without dropping products |
| dim_seller | seller_id |
| dim_date | Continuous dates between min/max order purchase day, inclusive |
| fct_order_items | Stable raw item key: order_id + order_item_id |
| fct_payments | Stable raw payment key: order_id + payment_sequential |
| fct_daily_sales | Calendar purchase day, including zero-order days |

Dimensions are Type 1 current attributes with existing natural business keys;
there is no fabricated SCD history or surrogate key requirement. Fact joins to
orders are inner joins; dbt grain/relationship tests and the Phase 5 verifier
confirm current raw records map without losses. Missing category names and
translations remain null. Synthetic inventory is staged as current source state;
it is not joined into historical sales or presented as real Olist stock.

## Financial rules and joining facts

Item price excludes freight. Payment value is a tender amount. All order statuses
are retained in both facts and the default daily metrics; only the explicitly
named delivered_item_value_brl metric filters delivered orders. These measures
are not recognized revenue, profit, refunds, or a claim that payments must equal
item prices. Payment minus items may include freight and other source differences.

Never directly join order items to payment rows before summing: an order with two
items and two payments would create four rows. Aggregate each fact by order or day
first, then join those summaries at that same grain. `fct_daily_sales` aggregates
orders, items and payments separately to day before joining them to dim_date.
For two prices 10/20 and payments 12/22 the result is item value 30 and payment
value 34, not 60 and 68. The verification fixture executes this example.

USD reporting divides BRL by BRL-per-USD. For each purchase day, use the latest
persisted ECB observation on or before that day, at most seven calendar days old.
The actual fx_rate_date and brl_per_usd remain visible. Weekend fallback is
explicit; missing coverage yields null USD values, never today's rate or zero.
The model makes no network calls and does not fetch all historical FX dates.
See [FX contract](fx-contract.md). BRL totals remain complete despite sparse FX.
Do not treat a partial sum of USD values as complete period coverage.

## Incremental choice and changed records

Only fct_order_items is incremental: its larger item grain benefits from avoiding
rewrites of unchanged records. A keyed, null-safe row comparison selects new or
changed derived rows, then PostgreSQL `delete+insert` replaces those keys in a
transaction. This scans source and target but avoids rewriting the entire fact.
It compares all projected attributes, including customer, purchase day and status
from the parent order. It intentionally does not trust max(loaded_at), which can
miss old corrections, equal timestamps or parent-only changes. An unchanged
replay writes zero item rows. A unique index enforces the declared item key.
See dbt's [incremental model behavior](https://docs.getdbt.com/docs/build/incremental-models).

CSV raw contracts retain keys rather than propagate physical deletes. If a raw
item/order is intentionally removed, or the model logic/schema changes, run a
controlled rebuild after reviewing source state:

```bash
python scripts/dbt.py build --full-refresh
```

Schema drift fails rather than silently appending columns. No arbitrary watermark
or incremental stock-history claim is introduced. Smaller dimensions, payments
and daily aggregates rebuild so corrections also remove stale old-day totals.
No performance speedup is claimed without Phase 8 measurement.

## Verification and scope

```bash
python -m scripts.verify_phase5
RUN_DB_TESTS=1 python -m pytest -q
python -m ruff check src scripts tests airflow/dags
```

The verifier runs debug/build, independently compares raw/fact/daily counts and
financial totals, checks identical live replay content, and creates a disposable
DB with two items/two payments. It changes an existing price and the parent day
and status without advancing a load watermark, then checks incremental results,
late new items, unchanged-row physical preservation, replay, tombstones, weekend
FX and equivalence with full refresh. It drops only
its own uniquely named test database and writes docs/phase5-evidence.json only
after successful checks and documentation generation. Normal raw records are
never modified by this script.

The project includes grain, not-null and fact dimension relationship tests needed
for the Phase 5 acceptance criteria. The broader accepted-value checks, custom
reconciliation suite, quarantine/reporting and publication gate belong to Phase 6;
those checklist items are not marked complete by this phase.

Phase 6 now implements the broader checks and explicit publication gate described
in [warehouse quality and publication](data-quality.md). Consumer tables are in
`published`; the developer models in `marts` remain available for iteration.
