"""Build candidates and publish only a complete passing dbt result set.

Publication uses the existing source advisory locks plus a publication lock.
All sanctioned loaders cooperate with these locks. Direct SQL bypasses this
protocol; the local developer superuser is not a production security boundary.
"""

import json
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path

from psycopg import Error, sql
from psycopg.types.json import Jsonb

from scripts.dbt import ROOT, run_dbt
from src.common.config import load_settings
from src.common.db import connection

MODELS = (
    "dim_customer",
    "dim_product",
    "dim_seller",
    "dim_date",
    "fct_order_items",
    "fct_payments",
    "fct_daily_sales",
)
KEY_COLUMNS = {
    "source_key",
    "order_id",
    "order_item_id",
    "payment_sequential",
    "customer_id",
    "product_id",
    "seller_id",
    "purchase_date",
    "date_day",
    "movement_id",
    "rate_date",
    "requested_date",
    "check_name",
    "base_currency",
    "quote_currency",
    "unique_field",
}


def test_results(db, artifacts):
    manifest = json.loads((artifacts / "manifest.json").read_text())
    results = json.loads((artifacts / "run_results.json").read_text())["results"]
    checks = []
    completed = {r["unique_id"]: r for r in results}
    for uid, node in manifest["nodes"].items():
        if node["resource_type"] != "test":
            continue
        result = completed.get(uid, {})
        passing = result.get("status") == "pass" and result.get("failures") == 0
        samples = []
        if result.get("status") == "fail":
            # dbt stores failing records; return key columns only, never row bodies.
            with db.cursor() as cur:
                cur.execute(
                    sql.SQL("SELECT * FROM {} LIMIT 5").format(
                        sql.Identifier(node["schema"], node["alias"])
                    )
                )
                names = [c.name for c in cur.description]
                samples = [
                    {k: str(v) for k, v in zip(names, row, strict=True) if k in KEY_COLUMNS}
                    for row in cur.fetchall()
                ]
        checks.append(
            {
                "check_name": node["name"],
                "expected": 0,
                "actual": result.get("failures"),
                "status": "PASS" if passing else "FAIL",
                "dbt_status": result.get("status", "missing"),
                "sample_failing_keys": samples,
            }
        )
    # Missing results, skipped nodes and runtime errors must also close the gate.
    complete = bool(checks) and all(c["status"] == "PASS" for c in checks)
    complete = complete and all(r["status"] in ("pass", "success") for r in results)
    models = {n["name"] for n in manifest["nodes"].values() if n["resource_type"] == "model"}
    complete = complete and set(MODELS).issubset(models)
    complete = complete and all(
        completed.get(uid, {}).get("status") == "success"
        for uid, node in manifest["nodes"].items()
        if node["resource_type"] == "model"
    )
    return checks, complete


def publish(settings=None, *, baseline=None, report_path=Path("docs/quality-report.json")):
    settings = settings or load_settings()
    baseline = (
        baseline
        if baseline is not None
        else json.loads((ROOT / "config/quality-baseline.json").read_text())
    )
    if set(baseline) != {"orders", "order_items", "order_payments"} or any(
        type(v) is not int or v < 1 for v in baseline.values()
    ):
        raise ValueError("Quality baseline must contain positive counts for all three sources")
    run_id = uuid.uuid4()
    report = {
        "run_id": str(run_id),
        "started_at": datetime.now(UTC).isoformat(),
        "status": "FAIL",
        "published": False,
        "checks": [],
        "count_baseline": baseline,
        "count_tolerance_fraction": 0.05,
    }
    with connection(settings) as guard:
        guard.autocommit = True
        # Fixed ordering avoids deadlocks; busy loaders/publications fail immediately.
        acquired = []
        try:
            for key in (224906, 224902):
                if not guard.execute("SELECT pg_try_advisory_lock(%s)", (key,)).fetchone()[0]:
                    raise RuntimeError("quality_source_or_publication_busy")
                acquired.append(key)
            for source in ("fx_ecb", "synthetic_sqlserver"):
                key = guard.execute("SELECT hashtext(%s)", (source,)).fetchone()[0]
                if not guard.execute("SELECT pg_try_advisory_lock(%s)", (key,)).fetchone()[0]:
                    raise RuntimeError("quality_source_or_publication_busy")
                acquired.append(key)
            guard.execute((ROOT / "sql/init/006_quality.sql").read_text())
            guard.execute(
                "INSERT INTO metadata.quality_runs(run_id,status) VALUES (%s,'running')",
                (run_id,),
            )
            try:
                with tempfile.TemporaryDirectory(prefix="ecommerce-quality-") as directory:
                    artifacts = Path(directory)
                    result = run_dbt(
                        [
                            "build",
                            "--full-refresh",
                            "--target",
                            "candidate",
                            "--target-path",
                            directory,
                            "--vars",
                            json.dumps(
                                {
                                    "quality_expected_counts": baseline,
                                    "quality_count_tolerance": 0.05,
                                }
                            ),
                        ],
                        extra_env={
                            "POSTGRES_HOST": settings.host,
                            "POSTGRES_PORT": str(settings.port),
                            "POSTGRES_DB": settings.database,
                            "POSTGRES_USER": settings.user,
                            "POSTGRES_PASSWORD": settings.password,
                        },
                    )
                    if (artifacts / "manifest.json").exists() and (
                        artifacts / "run_results.json"
                    ).exists():
                        report["checks"], valid = test_results(guard, artifacts)
                    else:
                        valid = False
                    if result == 0 and valid:
                        # DELETE/INSERT, not TRUNCATE: MVCC readers retain the old snapshot.
                        # All seven tables and publication audit commit or roll back together.
                        with guard.transaction():
                            guard.execute("CREATE SCHEMA IF NOT EXISTS published")
                            for name in MODELS:
                                source = sql.Identifier("candidate_marts", name)
                                target = sql.Identifier("published", name)
                                guard.execute(
                                    sql.SQL(
                                        "CREATE TABLE IF NOT EXISTS {} (LIKE {} INCLUDING ALL)"
                                    ).format(target, source)
                                )
                                guard.execute(sql.SQL("DELETE FROM {}").format(target))
                                guard.execute(
                                    sql.SQL("INSERT INTO {} SELECT * FROM {}").format(
                                        target, source
                                    )
                                )
                            report["published"] = True
                            report["status"] = "PASS"
                            report["finished_at"] = datetime.now(UTC).isoformat()
                            guard.execute(
                                "UPDATE metadata.quality_runs SET status='published',finished_at=now(),report=%s WHERE run_id=%s",
                                (Jsonb(report), run_id),
                            )
                    else:
                        report["error_code"] = "dbt_quality_failed"
            except Error, OSError, ValueError, KeyError, TypeError:
                # Driver/subprocess messages can contain configuration: store only a safe code.
                report["published"] = False
                report["status"] = "FAIL"
                report["error_code"] = "quality_execution_failed"
            if not report["published"]:
                report["finished_at"] = datetime.now(UTC).isoformat()
                guard.execute(
                    "UPDATE metadata.quality_runs SET status='failed',finished_at=now(),report=%s WHERE run_id=%s",
                    (Jsonb(report), run_id),
                )
        finally:
            for key in reversed(acquired):
                guard.execute("SELECT pg_advisory_unlock(%s)", (key,))
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    report = publish()
    print(f"Quality {report['status']}; published={report['published']}; docs/quality-report.json")
    return 0 if report["published"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
