# Documentation

[Project overview](../README.md)

## Run and maintain

- [Quick start](quickstart.md): passwords, databases, data loading, and dashboard
- [Detailed setup](setup.md): development and verification commands
- [Deployment](deployment.md): private remote demo and production limitations
- [Airflow](airflow.md): historical runs, scheduling, and recovery
- [Metabase](metabase.md): dashboard setup and refresh
- [Operations](runbook.md): troubleshooting, replay, and backups
- [Testing](testing.md): local checks and CI

## Understand the project

- [Architecture](architecture.md) and [data model](data-model.md)
- [Quality and publication](data-quality.md)
- [Analytics](analytics.md) and [result tables](analytics-results.md)
- [Design trade-offs](trade-offs.md)
- [CSV ingestion](csv-ingestion.md), [FX](fx-contract.md), and [SQL Server](sqlserver-source.md)
- [dbt](dbt-warehouse.md), [source contracts](data-contracts.md), and [profiling](source-profiling.md)
- [Python compatibility](python-compatibility.md)
- [Data attribution](data-rights.md)

Verification commands generate JSON reports locally. These reports, logs, raw
sources, backups, and credentials are excluded from Git.
