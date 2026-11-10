# Phase 1 source profiling — 2026-11-10

The nine local CSV hashes match a fresh publisher archive download and a second
end-to-end script download into a fresh directory. No existing file was replaced.
Publisher API metadata identifies `olistbr/brazilian-ecommerce`, version 2, last
updated 2021-10-01, license CC BY-NC-SA 4.0. See the publisher page linked in README
and docs/dataset-manifest.json for provenance hashes.

Executed command:

```bash
python scripts/profile_dataset.py --input data/raw --output docs/source-profile.json
```

| Source | Rows | Exact duplicate rows | Repeated candidate key rows |
|---|---:|---:|---:|
| customers | 99,441 | 0 | 0 |
| orders | 99,441 | 0 | 0 |
| items | 112,650 | 0 | 0 |
| payments | 103,886 | 0 | 0 |
| reviews | 99,224 | 0 | 814 |
| products | 32,951 | 0 | 0 |
| sellers | 3,095 | 0 | 0 |
| category translations | 71 | 0 | 0 |
| geolocation | 1,000,163 | 261,831 | No candidate key asserted |

No empty candidate keys were observed in the eight tables with declared candidate
keys. All per-column empty-field counts and headers are in source-profile.json;
empty review comments and order delivery timestamps are retained rather than
treated as parsing failures. Exact duplicates count occurrences after the first,
using SHA-256 of the ordered parsed field values. Collision risk is negligible,
but this is a hash-based measurement rather than storing full rows in memory.

Six measured relationships have zero unmatched distinct nonempty values:
orders-to-customers; items-to-orders/products/sellers; payments-to-orders; and
reviews-to-orders. Products-to-category-translations has two unmatched values.
The relationship metric counts distinct values, not failing row occurrences.

Design implications: preserve reviews until a defensible version/key rule is
chosen; geolocation needs deduplication and postcode aggregation before joins;
use an explicit untranslated-category policy. None of these issues was silently
cleaned in raw data. Product categories may be empty, and missing actual delivery
dates can be legitimate for unfinished or canceled orders. These source observations
are not warehouse acceptance rules. Final types, revenue definitions and load
metadata are Phase 2/5/6 work.
