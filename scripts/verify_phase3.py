"""Exercise real source updates/deletes, reruns and cross-source independence."""

import json
from datetime import date
from pathlib import Path

from psycopg import sql

from scripts.seed_synthetic_inventory import seed
from src.common.config import load_settings
from src.common.db import connection
from src.common.sqlserver import driver_module, sqlserver_connection
from src.ingestion.api_ingestion import ingest as fx_ingest
from src.ingestion.csv_pipeline import CONTRACTS
from src.ingestion.csv_pipeline import run as csv_run
from src.ingestion.sqlserver_ingestion import ingest as stock_ingest


def stock_state(settings):
    with connection(settings) as db:
        records = {}
        for table, key in [("inventory", "product_id"), ("stock_movements", "movement_id")]:
            records[table] = db.execute(
                sql.SQL("SELECT * FROM {} ORDER BY {}").format(
                    sql.Identifier("raw", table), sql.Identifier(key)
                )
            ).fetchall()
        records["cursor"] = db.execute(
            "SELECT watermark FROM metadata.external_checkpoints WHERE source='synthetic_sqlserver'"
        ).fetchone()
    return records


def main():
    settings = load_settings()
    evidence_path = Path("docs/phase3-evidence.json")
    previous = json.loads(evidence_path.read_text()) if evidence_path.exists() else {}
    seed()  # Restore the demo movement if a previous verification physically deleted it.
    first = stock_ingest(settings, "phase3-stock-first")
    state = stock_state(settings)
    repeated = stock_ingest(settings, "phase3-stock-repeat")
    assert repeated["counts"]["read"] == 0 and stock_state(settings) == state
    with sqlserver_connection(admin=True) as source:
        products = [
            row[0]
            for row in source.execute(
                "SELECT TOP(2) product_id FROM dbo.Inventory ORDER BY product_id"
            )
        ]
        prior = source.execute(
            "SELECT quantity FROM dbo.Inventory WHERE product_id=?", products[0]
        ).fetchone()[0]
        before_sequence = source.execute(
            "SELECT last_seq FROM dbo.ChangeCounter WHERE id=1"
        ).fetchone()[0]
        source.execute(
            "UPDATE dbo.Inventory SET quantity=quantity+1 WHERE product_id=?", products[0]
        )
        source.rollback()
        assert (
            source.execute("SELECT last_seq FROM dbo.ChangeCounter WHERE id=1").fetchone()[0]
            == before_sequence
        )
        # Two changes with the same timestamp still have distinct ordered outbox sequences.
        for value in (prior + 7, prior + 9):
            source.execute(
                "UPDATE dbo.Inventory SET quantity=?,updated_at='2026-01-01T00:00:00' WHERE product_id=?",
                value,
                products[0],
            )
        source.execute(
            "UPDATE dbo.Inventory SET is_deleted=1,quantity=0 WHERE product_id=?", products[1]
        )
        source.execute("DELETE dbo.StockMovements WHERE movement_id=100")
        version = source.execute(
            "SELECT CONVERT(varchar(50),SERVERPROPERTY('ProductVersion'))"
        ).fetchone()[0]
        driver = source.getinfo(driver_module().SQL_DRIVER_VER)
    try:
        stock_ingest(settings, "phase3-stock-recovery", fail_after=1)
    except RuntimeError:
        pass
    else:
        raise AssertionError("Expected failure did not occur")
    assert stock_state(settings) == state
    recovered = stock_ingest(settings, "phase3-stock-recovery")
    assert recovered["counts"]["read"] == 4
    with connection(settings) as db:
        assert (
            db.execute(
                "SELECT quantity FROM raw.inventory WHERE product_id=%s", (products[0],)
            ).fetchone()[0]
            == prior + 9
        )
        assert db.execute(
            "SELECT is_deleted FROM raw.inventory WHERE product_id=%s", (products[1],)
        ).fetchone()[0]
        assert db.execute(
            "SELECT is_deleted FROM raw.stock_movements WHERE movement_id=100"
        ).fetchone()[0]
        assert (
            db.execute("""SELECT count(*) FROM raw.inventory i WHERE NOT EXISTS
            (SELECT 1 FROM raw.products p WHERE p.data->>'product_id'=i.product_id)""").fetchone()[
                0
            ]
            == 0
        )
    final = stock_state(settings)
    assert stock_ingest(settings, "phase3-stock-final-repeat")["counts"]["read"] == 0
    assert stock_state(settings) == final
    fx = fx_ingest(settings, date(2017, 11, 25), "phase3-fx-independent")
    assert stock_state(settings) == final
    with connection(settings) as db:
        csv_before = {
            name: db.execute(
                sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier("raw", name))
            ).fetchone()[0]
            for name in CONTRACTS
        }
    csv_result = csv_run(settings, "phase3-csv-independent", date(2017, 11, 24), date(2017, 11, 25))
    assert stock_state(settings) == final
    with connection(settings) as db:
        csv_after = {
            name: db.execute(
                sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier("raw", name))
            ).fetchone()[0]
            for name in CONTRACTS
        }
        assert csv_before == csv_after
        assert db.execute("SELECT count(*) FROM raw.fx_rates").fetchone()[0] == 1
        failed = db.execute("""SELECT run_id,error_code FROM metadata.external_runs
            WHERE batch_id='phase3-stock-recovery' AND status='failed' ORDER BY started_at DESC LIMIT 1""").fetchone()
        counts = {
            table: db.execute(
                sql.SQL("SELECT count(*),count(*) FILTER(WHERE is_deleted) FROM {}").format(
                    sql.Identifier("raw", table)
                )
            ).fetchone()
            for table in ("inventory", "stock_movements")
        }
        provenance = db.execute(
            "SELECT source,status,count(*) FROM metadata.external_runs GROUP BY source,status ORDER BY source,status"
        ).fetchall()
    output = {
        "result": "PASS",
        "sqlserver_version": version,
        "odbc_version": driver,
        "initial_full_load": previous.get("initial_full_load", previous.get("first", first)),
        "synthetic": True,
        "first": first,
        "repeat": repeated,
        "recovered": recovered,
        "failed": {"run_id": str(failed[0]), "error_code": failed[1]},
        "raw_counts_and_tombstones": counts,
        "fx": fx,
        "csv_run_id": csv_result["run_id"],
        "csv_counts_unchanged": csv_after,
        "external_audit_summary": provenance,
    }
    evidence_path.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
