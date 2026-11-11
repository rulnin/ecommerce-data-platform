# Design choices and limits

| Choice | Why it fits this project | Cost and next step if requirements change |
|---|---|---|
| PostgreSQL analytical target | Local numeric/JSONB support, transactional writes/publication and existing dbt Postgres adapter | One-node storage/concurrency envelope; measure actual workload before choosing partitioning, columnar storage or a managed warehouse |
| SQL Server as a separate source | Demonstrates heterogeneous extraction, native ODBC and commit-ordered incremental changes using skills transferable from SQL Server | Optional 3 GiB container/native driver burden; synthetic demo outbox is not a claim of enterprise CDC deployment |
| Batch instead of streaming | The Olist input is a historical immutable snapshot, FX is dated reference data, and synthetic inventory changes are generated for tests | Simulated day slices still hash/scan files; genuine events would need durable offsets, event-time semantics, replay and delete contracts |
| Full load then idempotent updates | Full load establishes a known baseline; keyed hashes/sequences make reruns and corrections explicit | Re-reading a CSV snapshot is expensive even when zero rows change; the measured replay comparison is not new-arrival throughput |
| Incremental item fact only | Null-safe keyed comparison avoids rewriting unchanged rows and catches parent status/day corrections | Still scans source/target and needs controlled full refresh for physical deletions/schema changes; smaller marts rebuild |
| Full candidate rebuild for publication | A complete candidate catches stale/deleted rows and keeps publication independent of developer incremental state | More CPU/I/O and duplicate storage; larger workloads may need versioned partitions or incremental publication with equally strong tests |
| Separate item/payment facts | Preserves different grains and prevents financial double counting | Analysts must aggregate before joining and distinguish tender amounts from delivered sales proxy |
| Raw JSONB plus typed staging | Keeps original source strings and source fingerprints while making transformations reviewable | JSONB expression/cast cost and specific expression indexes; a stable larger source contract may justify typed raw columns |
| Local Docker instead of AWS | Zero required cloud spend, reviewable persistent state and deterministic local tests | Manual single-host operation, no demonstrated cloud IAM/HA/scaling; a future AWS deployment is separate work requiring cost/security/operational design |
| Airflow and dbt dependencies isolated | Container constraints remain separate from Python 3.14 WSL tooling | Explicit WSL publication step is still outside the current DAG; do not market this as fully automated dimensional orchestration |
| Existing LocalExecutor | Three Airflow services with bounded concurrency suffice for the local demo | Not a distributed worker/HA deployment; scale only after measuring queueing and resource contention |

Correctness gates take priority over a fast-looking dashboard: missing mappings,
duplicate natural keys, null required money, count drift or reconciliation failures
block publication. Optional untranslated categories remain visible. FX missingness
remains visible instead of manufacturing a complete USD total.

Performance evidence is workload-specific: median existing-target full replay
76.163 s vs one-day replay 4.965 s; one selective query 77.511 ms vs 7.389 ms after
approximately 9.6 MiB of added indexes. Trials used one WSL host and warm/reused
caches, with disclosed background activity. No generic throughput SLA, cloud
performance comparison or ingestion speedup from those lookup indexes is claimed.
See [samples and limits](benchmarks.md).

Before a production deployment, design least-privilege identities and secret
rotation, coordinated source/target recovery, concurrency/HA, retention, dataset
usage rights, monitoring and cost controls for the actual requirements. The local
superuser and cooperative advisory locks are not a production security boundary.
These are scope boundaries, not claims of completed AWS or production hardening.
