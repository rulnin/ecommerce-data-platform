# Architecture and execution boundaries

This is a local portfolio implementation. Its heterogeneous sources, retries,
quality gate and operational evidence run locally; there is no deployed AWS
infrastructure or streaming source. PostgreSQL stores analytical data and a separate
Airflow metadata database. Source datasets and secrets stay outside Git.

```mermaid
flowchart LR
    CSV["Historical Olist CSV snapshot"] --> C["CSV loader: bounded batches and hashes"]
    FX["Frankfurter API: dated ECB USD/BRL"] --> F["FX loader: retry and cache"]
    SQL["SQL Server: synthetic inventory outbox"] --> S["Stock loader: committed sequence"]
    C --> R["PostgreSQL raw and ingestion audit"]
    F --> R
    S --> R
    R --> ST["dbt typed staging views"]
    ST --> M["Developer marts"]
    ST --> CM["Candidate marts: full build"]
    CM --> Q{"All models and quality tests pass?"}
    Q -->|yes| P["Atomic publication: seven tables"]
    Q -->|no| OLD["Keep previous published tables"]
    P --> A["Read-only business SQL and aggregate report"]
    R --> O["Airflow operational day summary and checks"]
    AF["Airflow scheduler, API and DAG processor"] -. orchestrates .-> C
    AF -. orchestrates .-> F
    AF -. orchestrates .-> S
    AF -. orchestrates .-> O
```

The Airflow DAG implements ingestion → operational transform → operational quality,
with source tasks preceding transform/quality. It does **not** run dimensional dbt
or publish consumer marts. The explicit WSL `python -m src.quality.publication`
command builds candidates, tests every enabled model/test and publishes all seven
tables in one transaction. A failed candidate leaves the last good publication.
The architecture shows these actual boundaries rather than an unimplemented
end-to-end dbt operator.

```mermaid
flowchart TB
    subgraph WSL["WSL Ubuntu: Linux filesystem"]
        ENV["Python 3.14.4 uv-created .venv: ingestion, dbt, pytest"]
        FILES["Ignored data/raw, data/backups and .env"]
        CLI["Explicit dbt publication and report commands"]
    end
    subgraph DOCKER["Docker Compose: local services"]
        PG["PostgreSQL 17: warehouse plus separate airflow_meta DB"]
        MSSQL["Optional SQL Server 2022 source"]
        AIR["Airflow 3.4: own Python and constrained dependencies"]
        PV["Named PostgreSQL, SQL Server and Airflow-log volumes"]
    end
    ENV --> PG
    ENV --> MSSQL
    CLI --> ENV
    FILES --> ENV
    FILES -. read-only CSV mount .-> AIR
    AIR --> PG
    AIR --> MSSQL
    PG --- PV
    MSSQL --- PV
    AIR --- PV
```

Published tables and model grains: [data model](data-model.md). Source contracts:
[CSV](csv-ingestion.md), [FX](fx-contract.md), [SQL Server](sqlserver-source.md).
Recovery/resource/backup procedures: [runbook](runbook.md). The PostgreSQL warehouse
restore exercise covers neither SQL Server nor Airflow's separate metadata DB.
CI runs lightweight unit and disposable PostgreSQL integration tests; it does not
start the full Airflow stack or fetch public data.

Portable rendered copies: [data flow](diagrams/architecture-1.svg) and
[runtime boundaries](diagrams/architecture-2.svg). The same Mermaid definitions
were syntax-checked and rendered with Mermaid 11.4.1; see
[render evidence](phase9-render-evidence.json).
