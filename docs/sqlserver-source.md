# Synthetic SQL Server inventory — Phase 3

All inventory/stock movements are simulated portfolio data, not Olist inventory.
The seed selects the first 100 valid public product IDs from raw.products, sorted
deterministically, and initializes quantity 100 plus one +100 movement each.
Existing source rows are preserved by seeding. Re-seeding recreates a physically
deleted demo movement with a new source change event; it is not deletion cleanup.
Verification deliberately changes synthetic quantities and tombstones.

## Verified compatibility and setup

WSL2 Ubuntu 26.04.1 on x86_64, approximately 9 GiB available memory before startup;
SQL Server uses a 3 GiB container cap and 2048 MiB SQL memory limit. Microsoft's
[container guidance](https://learn.microsoft.com/en-us/sql/linux/install-upgrade/quickstart-install-docker?view=sql-server-linux-ver16)
requires supported x86-64 Linux and at least 2 GiB memory. This local development
verification does not claim production support or certification of the WSL host.

Pinned image `mcr.microsoft.com/mssql/server:2022-CU27-GDR1-ubuntu-22.04` was verified
in MCR's tag listing and ran successfully. Server reports 16.0.4305.5. Developer
edition is selected for local development, with container ACCEPT_EULA=Y. Source
storage is named volume ecommerce-data-platform_sqlserver_data; only
127.0.0.1:1433 is published. The optional sqlserver Compose profile keeps Phase 1
PostgreSQL startup independent of SQL Server availability/credentials.

Use Phase 1's venv, then create missing local passwords without displaying them:

```bash
source .venv/bin/activate
python - <<'PY'
from pathlib import Path
import secrets
path = Path('.env')
text = path.read_text()
for key in ('MSSQL_SA_PASSWORD', 'SQLSERVER_PASSWORD'):
    lines = text.splitlines()
    matching = [line for line in lines if line.startswith(key + '=')]
    if not matching:
        text += '\n' + key + '=Local9!' + secrets.token_hex(20) + '\n'
    elif matching[-1] == key + '=':
        text = text.replace(key + '=\n', key + '=Local9!' + secrets.token_hex(20) + '\n')
path.write_text(text)
path.chmod(0o600)
PY
bash scripts/setup_odbc.sh
python -m pip install -r requirements-sqlserver.txt
docker compose --profile sqlserver up -d --wait --wait-timeout 240 sqlserver
python -m scripts.seed_synthetic_inventory
python -m src.ingestion.sqlserver_ingestion --batch-id inventory-initial
python -m scripts.verify_phase3
```

SQLSERVER_HOST/PORT default to 127.0.0.1/1433. Credentials are read from .env/process
environment and omitted from logs. sa is used for bootstrap/demo writes; extraction
uses inventory_reader, granted SELECT on ChangeLog and ChangeCounter only.
Changing .env passwords does not rotate existing SQL logins. Local transport is
encrypted with TrustServerCertificate=yes because this development server has a
self-signed certificate; production would require verified certificates.

### WSL ODBC runtime

Microsoft lists [Ubuntu 26.04 support for ODBC 18.7](https://learn.microsoft.com/en-us/sql/connect/odbc/linux-mac/system-requirements).
sudo here requires interactive authentication. Instead of changing system packages,
the verified setup extracts official packages into ignored .local/odbc:

- msodbcsql18 18.7.1.1-1; SHA-256 checked against publisher package metadata.
- Ubuntu libodbc2/libodbcinst2 2.3.14-1 and libltdl7 2.5.4-9, downloaded using apt.
- pyodbc 5.5.0 in the existing Python 3.14.4 venv.

No maintainer scripts run and no system driver registration is changed. The connector
preloads the local runtime and uses process-local ODBCSYSINI. Driver discovery
reports ODBC Driver 18 for SQL Server; real connections report 18.07.0001.
The local package license is .local/odbc/usr/share/doc/msodbcsql18/LICENSE.txt.
This is a verified project-local runtime, not a claim that dpkg installed the driver
globally. The setup script intentionally targets Ubuntu 26.04 x86_64 and exact
package versions; if repositories change, review supported versions before changing
pins. Normal system-driver installations can be used when the local directory is
absent; see Microsoft's [installation instructions](https://learn.microsoft.com/en-us/sql/connect/odbc/linux/installing-the-microsoft-odbc-driver-for-sql-server-on-linux).

## Change sequence and deletion contract

sql/init/003_synthetic_sqlserver.sql creates Products, Inventory, StockMovements,
ChangeCounter, immutable-by-contract ChangeLog, and DML triggers. The counter is
updated under a transaction-held UPDLOCK/HOLDLOCK. Each trigger allocates a contiguous
range and writes one outbox row per changed business key. The same transaction
commits source mutations, counter and outbox together; rollback leaves no gap.
Counter serialization prevents a later committed event overtaking an uncommitted
lower sequence, an issue a bare identity/high-water mark can have. Business-table
concurrency can still deadlock; the failing writer must retry its source transaction.

Extraction freezes a committed upper bound, then reads `(saved_sequence, upper]`
ordered by unique change_seq in bounded fetchmany batches. Timestamps are UTC
metadata, not the cursor, so identical timestamps are safe. Retention gaps, source
resets and incomplete intervals fail rather than skipping records. Do not truncate,
rewrite or purge outbox/counter history without a planned target rebootstrap.
The source reader cannot perform those mutations; a source administrator still can.

Updates upsert by product_id or movement_id only when sequence advances. Soft
deletes and physical DELETE triggers both produce is_deleted=true tombstones;
target keys remain for audit/history. Resurrection with a newer sequence is allowed.
Raw inventory and movements are separate grains; seeded movements and later demo
quantity changes are not a complete financial inventory ledger and must not be
presented as real stock reconciliation.

Source SQL types are product varchar(32), quantity/delta int, movement bigint,
is_deleted bit, updated_at UTC datetime2(6), change_seq bigint. PostgreSQL raw tables
use text/int/bigint/boolean/timestamptz equivalents, source sequence and run UUID,
with mandatory is_synthetic=true. Each product must map to loaded raw.products.
metadata.external_runs records counts/provenance and sanitized failures;
metadata.external_checkpoints advances with target data in the same transaction.
The source outbox is immutable by contract, so no distributed transaction is needed.
After failure, rerun the same batch ID: it creates a new attempt and resumes the
last committed sequence. Crash/lost-connection audits can remain running; confirm
the old session is gone before recovery. No automatic outbox retention is implemented.

## Executed evidence and resource handling

docs/phase3-evidence.json preserves the initial 200-event load, zero-event replay,
same-timestamp updates, soft inventory delete, physical movement delete, forced
target rollback and successful four-event recovery. Source transaction rollback
also preserved its counter. Targets contain 100 inventory and 100 movement keys,
with one tombstone each and zero missing product mappings. Replays read no new
events. The verification script is repeatable; it restores the demo movement,
deliberately adds two quantity changes, and preserves the first full-load evidence.

It also executes FX and CSV independently and confirms unchanged CSV counts and
stock state across those other loads. SQL Server is optional and can be stopped
when not testing ingestion to save memory:

```bash
docker compose --profile sqlserver stop sqlserver
docker compose --profile sqlserver start sqlserver
docker compose --profile sqlserver logs --tail 50 sqlserver
```

Keep the named volume; do not use down -v as routine cleanup. Stop/start before
ingestion requires waiting for health again. Phase 4 orchestration is not implemented.
