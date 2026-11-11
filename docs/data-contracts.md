# Initial Olist source contracts

These contracts describe the locally observed historical snapshot, not a live feed.
Raw values are preserved as strings during profiling; empty fields are counted
separately. Phase 2 retains these strings in JSONB and documents rejection/key rules
in csv-ingestion.md. Typed staging, timezone interpretation and precision rules
remain later-phase decisions. The machine-readable evidence is
`source-profile.json`, including SHA-256 per file and complete column/null counts.

| Source | Observed rows | Intended grain / candidate key | Proposed target |
|---|---:|---|---|
| customers | 99,441 | customer_id; customer_unique_id can repeat | raw.customers |
| orders | 99,441 | order_id | raw.orders |
| order_items | 112,650 | order_id + order_item_id | raw.order_items |
| order_payments | 103,886 | order_id + payment_sequential | raw.order_payments |
| order_reviews | 99,224 | Content-hash versions; review_id alone repeats | raw.order_reviews |
| products | 32,951 | product_id | raw.products |
| sellers | 3,095 | seller_id | raw.sellers |
| category translation | 71 | product_category_name | raw.category_translation |
| geolocation | 1,000,163 | Content hash; exact duplicates collapse in raw | raw.geolocation |

Phase 2 implements these target tables. Source columns map to identically named
string fields within each raw table's `data` JSONB payload. Provenance, hashes,
keys and run metadata are separate columns. See csv-ingestion.md for final raw
grain/preservation rules and source-to-target mapping; typed staging is later work.
Do not use row order as a permanent business key. Do not impose review_id uniqueness:
814 rows repeat that candidate key. Investigate review versions and exact duplicates
and Phase 2 preserves distinct content-addressed versions rather than choosing
an arbitrary winner. Source row count and unique loaded count are reconciled.

Exact-row profiling now confirms zero identical review rows and 261,831 duplicate
geolocation rows beyond the first occurrence. See source-profiling.md and the
per-column empty-field counts in source-profile.json. Dataset hashes match a fresh
publisher download; provenance is recorded in dataset-manifest.json.

All seven measured relationships appear in the JSON report. Orders to customers,
items to orders/products/sellers, payments to orders, and reviews to orders each have
zero unmatched distinct nonempty keys. Products to category translation have two
unmatched distinct nonempty categories. Preserve these products and use an explicit
unknown/untranslated category policy rather than an inner join that drops them.
Empty keys and fields are measured separately from relationship violations.

Order items and payments have different grains. Aggregate each to order before
combining totals. Item price, freight, and payment value remain separate measures;
revenue rules and reconciliation tolerances are not yet defined. Geolocation requires
an explicit postcode aggregation rule before dimension joins to avoid row multiplication.

Phase 3 contracts are now defined in fx-contract.md and sqlserver-source.md.
raw.fx_rates stores dated ECB USD/BRL observations; raw.inventory and
raw.stock_movements contain explicitly synthetic, sequence-versioned stock rows
linked to valid product IDs. No historical Olist CSV is represented as genuine
live CDC or actual inventory.
