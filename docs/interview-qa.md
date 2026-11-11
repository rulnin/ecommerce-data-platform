# Interview Q&A dry run

This is an agent-led technical rehearsal against the implemented source contracts,
tests, measured evidence and clean-release exercise. It is not a recording or a
claim that the user completed a spoken interview. The separate short presentation
script is in walkthrough.md; the user waived CV updates during Phase 10.

## 1. What prevents duplicate data when a batch is retried?

CSV business keys are stable, with hash-conditional upserts inside a whole-run
transaction. A duplicate natural key within one file aborts the batch; exact
geolocation content duplicates intentionally collapse. Review IDs can repeat, so
distinct content versions remain distinct. A successful unchanged replay changes
neither row counts nor financial totals. Evidence: CSV unit/integration tests,
phase2-evidence.json and phase8-evidence.json.

Follow-up: deduplication is a source contract, not “drop all duplicate IDs.” A
review key and a payment sequential key have different semantics.

## 2. What happens if the process dies around a checkpoint?

Target updates and successful checkpoints commit together. A failure before commit
rolls them back; a failure after commit but before the caller receives success can
be safely replayed through idempotent writes. The started audit is committed
separately so a killed process may leave a running attempt; inspect committed
checkpoints and actual target state rather than changing its status to success.
Connections alone retry automatically; partially executed transactions do not.
Evidence: CSV rollback/backfill and external-source integration tests.

## 3. Why not use an identity column or updated_at alone for SQL Server?

Timestamps can tie, and a larger identity can commit before an earlier transaction.
The synthetic source serializes a transactional change counter under locking and
writes its outbox in that same transaction. Extraction freezes an upper committed
sequence and requires a contiguous interval. Rollback does not leave a counter
gap. This is the demo source's explicit contract, not a claim that arbitrary
production identity values provide commit ordering. Evidence: Phase 3 outbox
verification and unit gap/reset/incomplete-interval tests.

## 4. How are deletes and late corrections handled?

SQL Server soft/physical deletes become retained tombstones with higher sequences;
older events cannot overwrite newer state. Timestamp ties are harmless. CSV raw
keeps snapshot keys; intentional physical removal or changed model logic needs a
reviewed full refresh. Item-fact comparison detects changed parent status/day as
well as price, without trusting a max-loaded-at watermark. Current dimensions are
Type 1; the project does not fabricate historical SCD state. Evidence: source
runbook, Phase 5 correction/full-refresh checks and Phase 6 late-update scenario.

## 5. Why do payment totals differ from revenue?

They represent different measures and grains. Delivered item prices by original
purchase day define this project's sales proxy; freight, refunds, taxes and fees
are outside that definition. All-status tender amounts are separate payment rows.
Two items joined to two payments would create four rows, so aggregate each fact
independently before combining. The raw/fact/daily tests reconcile each measure
against its own source, not against an unjustified equality between tenders and
revenue. Evidence: financial_reconciliation.sql and the two-item/two-payment fixture.

## 6. Can a bad candidate replace the last good dashboard data?

The supported publisher requires every enabled model/test to succeed in fresh
artifacts. Error, skip, warning or missing results close the gate. On success,
all seven consumer tables and the success audit update in one DB transaction.
Cooperating source/publication advisory locks prevent loader interference. This
is not a distributed transaction across sources, and direct superuser SQL can
bypass the protocol. Eight invalid-source scenarios preserve publication hashes.
Evidence: Phase 6 report, gate unit tests and publication source.

## 7. Can you report complete USD sales or current inventory?

No. USD conversion uses actual persisted ECB observation dates with a seven-day
backward limit. Only a small subset of this historical snapshot has cached rates;
missing conversions stay null and partial totals carry coverage. Inventory is
synthetic current state, not Olist's real or historical stock. Showing a complete
USD total or joining today's synthetic quantity to historical sales would mislead.
Evidence: FX contract and query 08_fx_coverage.sql.

## 8. What does your performance comparison prove?

It measures one WSL host's existing-target full replay and historical day replay,
not equal-volume new-arrival throughput. The smaller slice skips unchanged
references but still hashes/scans source files. A selective SQL query benefited
from two expression indexes, with measured storage/build cost; that is not an
end-to-end ingestion speedup. Cache, ordering and brief background activity are
disclosed. Next decisions should follow representative production workload
measurements, rather than assuming these ratios scale linearly.

## 9. What exactly did you back up and restore?

The warehouse DB was dumped and restored into a new database; all 153 user tables'
counts and logical row hashes matched, and the original stayed unchanged. The
archive has a recorded SHA-256 and remains ignored/private. SQL Server, Airflow's
separate metadata DB, roles/secrets and source counter history need their own
coordinated recovery. A named volume is persistence, not a complete disaster
recovery plan. Evidence: Phase 8 backup report and operations runbook.

## 10. How would you scale or move this to AWS?

First identify the limiting resource: repeated CSV parsing/hashing, DB writes,
query patterns, storage or scheduler concurrency. Possible later changes include
immutable source manifests, typed/partitioned storage and true CDC with durable
retention/deletion contracts. A cloud version would require an explicit storage,
compute, IAM, secret, recovery, observability and cost design. None is deployed
here. The current heterogeneous local stack demonstrates correctness and
operational reasoning; it is not a production HA or cloud experience claim.

## Practical rehearsal checklist

- Trace one run ID through source audit, checkpoint, Airflow attempt and quality report.
- Explain the two-item/two-payment multiplication example without SQL jargon.
- Point to a real failed/recovered run and the unchanged publication evidence.
- Reproduce the read-only business report and disclose its FX/revenue definitions.
- Explain why clean-clone verification uses fresh isolated volumes instead of resetting a working DB.
- Describe cleanup commands that stop/remove only review containers and retain named volumes.

The release exercise runs those implemented components again on a clean clone;
its actual results, CI commit and release links are recorded in release-verification.md.
