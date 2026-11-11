"""Measure real-snapshot replay and recovery without deleting warehouse rows."""

import argparse
import csv
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from psycopg import sql

from src.common.config import load_settings
from src.common.db import connection
from src.ingestion.csv_pipeline import CONTRACTS, run


def metrics(settings):
    with connection(settings) as db:
        tables = {}
        for source in CONTRACTS:
            tables[source] = db.execute(
                sql.SQL("SELECT count(*),count(DISTINCT business_key) FROM {}").format(
                    sql.Identifier("raw", source)
                )
            ).fetchone()
        totals = {}
        for source, field in [
            ("order_items", "price"),
            ("order_items", "freight_value"),
            ("order_payments", "payment_value"),
        ]:
            totals[field] = str(
                db.execute(
                    sql.SQL("SELECT sum((data->>%s)::numeric) FROM {}").format(
                        sql.Identifier("raw", source)
                    ),
                    (field,),
                ).fetchone()[0]
            )
        checkpoints = db.execute(
            "SELECT source,watermark FROM metadata.checkpoints ORDER BY source"
        ).fetchall()
    return {
        "tables": tables,
        "totals": totals,
        "checkpoints": [(s, str(w)) for s, w in checkpoints],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full-run", help="Reuse a successfully executed full-run UUID")
    parser.add_argument("--output", type=Path, default=Path("docs/phase2-evidence.json"))
    args = parser.parse_args()
    settings = load_settings()
    if args.full_run:
        with connection(settings) as db:
            saved = db.execute(
                "SELECT counts,status,mode FROM metadata.ingestion_runs WHERE run_id=%s",
                (args.full_run,),
            ).fetchone()
        assert saved and saved[1:] == ("success", "full")
        full = {"run_id": args.full_run, "counts": saved[0]}
    else:
        full = run(settings, "verification-full")
    baseline = metrics(settings)
    for source, counts in full["counts"].items():
        expected = counts["accepted"] - counts["deduplicated"]
        assert baseline["tables"][source] == (expected, expected), source
    # Compare financial totals at their own grains, never via a multiplying join.
    for source, field in [
        ("order_items", "price"),
        ("order_items", "freight_value"),
        ("order_payments", "payment_value"),
    ]:
        with (settings.raw_dir / CONTRACTS[source]["filename"]).open(newline="") as stream:
            expected = sum((Decimal(row[field]) for row in csv.DictReader(stream)), Decimal(0))
        assert Decimal(baseline["totals"][field]) == expected, field
    first = run(settings, "verification-day", date(2017, 11, 24), date(2017, 11, 25))
    assert first["counts"]["orders"]["accepted"] > 0
    assert metrics(settings) == baseline
    reruns = []
    for _ in range(3):
        reruns.append(run(settings, "verification-day", date(2017, 11, 24), date(2017, 11, 25)))
        assert metrics(settings) == baseline
    try:
        run(
            settings,
            "verification-recovery",
            date(2017, 11, 24),
            date(2017, 11, 25),
            fail_source="order_items",
        )
    except RuntimeError as error:
        assert "simulated_failure" in str(error)
    else:
        raise AssertionError("Expected failure did not fail")
    assert metrics(settings) == baseline
    recovered = run(settings, "verification-recovery", date(2017, 11, 24), date(2017, 11, 25))
    assert metrics(settings) == baseline
    with connection(settings) as db:
        failed = db.execute("""SELECT run_id,error_code FROM metadata.ingestion_runs
            WHERE batch_id='verification-recovery' AND status='failed' ORDER BY started_at DESC LIMIT 1""").fetchone()
    evidence = {
        "full": full,
        "incremental": first,
        "reruns": reruns,
        "failed": {"run_id": str(failed[0]), "code": failed[1]},
        "recovered": recovered,
        "stable_metrics": baseline,
        "result": "PASS",
    }
    args.output.write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps({"result": "PASS", "metrics": baseline}, indent=2))


if __name__ == "__main__":
    main()
