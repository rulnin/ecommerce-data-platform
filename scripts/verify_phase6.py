"""Exercise real dbt rejection/publication using isolated synthetic injections."""

import json
import tempfile
import uuid
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from psycopg import sql

from scripts.dbt import ROOT
from scripts.verify_phase5 import fixture, snapshot
from src.common.config import load_settings
from src.common.db import connection
from src.quality.publication import publish


def verify_injections(original):
    name = "quality_verify_" + uuid.uuid4().hex
    settings = replace(original, database=name)
    baseline = {"orders": 1, "order_items": 2, "order_payments": 2}
    evidence = {}
    with connection(original) as db:
        db.autocommit = True
        db.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    try:
        with connection(settings) as db:
            fixture(db)
        with tempfile.TemporaryDirectory(prefix="phase6-reports-") as directory:

            def run(case):
                report = publish(
                    settings,
                    baseline=baseline,
                    report_path=Path(directory) / (case + ".json"),
                )
                # Keep failed reports as inspectable, non-sensitive project evidence.
                evidence[case] = report
                return report

            assert run("valid_initial")["published"]
            saved = snapshot(settings, "published")
            cases = [
                (
                    "null_injection",
                    "UPDATE raw.order_items SET data=jsonb_set(data,'{price}','null') WHERE business_key='order_items_1'",
                    "UPDATE raw.order_items SET data=jsonb_set(data,'{price}','\"10\"') WHERE business_key='order_items_1'",
                    "required_financial_fields",
                ),
                (
                    "duplicate_order",
                    "INSERT INTO raw.orders SELECT 'duplicate_order',data,row_hash,loaded_at FROM raw.orders",
                    "DELETE FROM raw.orders WHERE business_key='duplicate_order'",
                    "unique_stg_orders_order_id",
                ),
                (
                    "duplicate_item",
                    "INSERT INTO raw.order_items SELECT 'duplicate_item',data,row_hash,loaded_at FROM raw.order_items WHERE business_key='order_items_1'",
                    "DELETE FROM raw.order_items WHERE business_key='duplicate_item'",
                    "unique_grain_stg_order_items",
                ),
                (
                    "duplicate_payment",
                    "INSERT INTO raw.order_payments SELECT 'duplicate_payment',data,row_hash,loaded_at FROM raw.order_payments WHERE business_key='order_payments_1'",
                    "DELETE FROM raw.order_payments WHERE business_key='duplicate_payment'",
                    "unique_grain_stg_order_payments",
                ),
                (
                    "missing_inventory_mapping",
                    "UPDATE raw.inventory SET product_id='missing-product'",
                    "UPDATE raw.inventory SET product_id='p'",
                    "missing_inventory_mapping",
                ),
                (
                    "row_count_drift",
                    'INSERT INTO raw.orders VALUES (\'late-order\',\'{"order_id":"late-order","customer_id":"c","order_status":"delivered","order_purchase_timestamp":"2017-11-25 11:00:00"}\', \'fixture\',now())',
                    "DELETE FROM raw.orders WHERE business_key='late-order'",
                    "source_count_drift",
                ),
                (
                    "invalid_status",
                    "UPDATE raw.orders SET data=jsonb_set(data,'{order_status}','\"invalid\"')",
                    "UPDATE raw.orders SET data=jsonb_set(data,'{order_status}','\"delivered\"')",
                    "accepted_values_stg_orders_order_status",
                ),
                (
                    "missing_order_mapping",
                    "UPDATE raw.order_payments SET data=jsonb_set(data,'{order_id}','\"missing-order\"') WHERE business_key='order_payments_1'",
                    "UPDATE raw.order_payments SET data=jsonb_set(data,'{order_id}','\"o\"') WHERE business_key='order_payments_1'",
                    "missing_order_mapping",
                ),
            ]
            for case, inject, restore, expected in cases:
                with connection(settings) as db:
                    db.execute(inject)
                report = run(case)
                assert not report["published"] and report["status"] == "FAIL", case
                relevant = [
                    c
                    for c in report["checks"]
                    if expected in c["check_name"] and c["dbt_status"] == "fail"
                ]
                assert relevant and any(c["sample_failing_keys"] for c in relevant), (
                    case,
                    report,
                )
                assert snapshot(settings, "published") == saved, case
                with connection(settings) as db:
                    db.execute(restore)
            # A historical correction is legitimate, even without advancing loaded_at.
            with connection(settings) as db:
                db.execute(
                    "UPDATE raw.order_items SET data=jsonb_set(data,'{price}','\"15\"') WHERE business_key='order_items_1'"
                )
            assert run("late_update")["published"]
            with connection(settings) as db:
                assert db.execute(
                    "SELECT item_value_brl,revenue_brl,payment_value_brl FROM published.fct_daily_sales"
                ).fetchone() == (Decimal(35), Decimal(35), Decimal(34))
            corrected = snapshot(settings, "published")
            assert corrected != saved
            assert run("recovery_replay")["published"]
            assert snapshot(settings, "published") == corrected
            # Verify the reconciliation test itself detects a fact-only corruption.
            with connection(settings) as db:
                db.execute("UPDATE candidate_marts.fct_payments SET payment_value_brl=999")
            from scripts.dbt import run_dbt

            result = run_dbt(
                [
                    "test",
                    "--select",
                    "financial_reconciliation",
                    "--target",
                    "candidate",
                    "--target-path",
                    str(Path(directory) / "corruption"),
                ],
                extra_env={
                    "POSTGRES_DB": name,
                    "POSTGRES_HOST": settings.host,
                    "POSTGRES_PORT": str(settings.port),
                    "POSTGRES_USER": settings.user,
                    "POSTGRES_PASSWORD": settings.password,
                },
            )
            assert result != 0
            artifact = json.loads((Path(directory) / "corruption/run_results.json").read_text())
            assert artifact["results"][0]["status"] == "fail"
            assert snapshot(settings, "published") == corrected
            evidence["fact_corruption"] = {
                "status": "EXPECTED_FAIL",
                "published_unchanged": True,
            }
            with connection(settings) as db:
                states = dict(
                    db.execute(
                        "SELECT status,count(*) FROM metadata.quality_runs GROUP BY status"
                    ).fetchall()
                )
            assert states == {"published": 3, "failed": 8}, states
            return {
                "scenarios": evidence,
                "audit_counts": states,
                "published_unchanged_on_all_failures": True,
            }
    finally:
        with connection(original) as db:
            db.autocommit = True
            db.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


def main():
    settings = load_settings()
    fixtures = verify_injections(settings)
    live = publish(settings)
    assert live["published"]
    with connection(settings) as db:
        revenue = db.execute(
            "SELECT sum(revenue_brl),sum(payment_value_brl) FROM published.fct_daily_sales"
        ).fetchone()
        raw_revenue = db.execute(
            "SELECT sum((i.data->>'price')::numeric) FROM raw.order_items i JOIN raw.orders o "
            "ON i.data->>'order_id'=o.data->>'order_id' WHERE o.data->>'order_status'='delivered'"
        ).fetchone()[0]
        assert raw_revenue == revenue[0]
        assert snapshot(settings, "published") == snapshot(settings, "candidate_marts")
    report = {
        "status": "PASS",
        "verified_at": datetime.now(UTC).isoformat(),
        "live_run_id": live["run_id"],
        "live_test_count": len(live["checks"]),
        "raw_and_published_delivered_item_value_brl": str(raw_revenue),
        "published_payment_value_brl": str(revenue[1]),
        "fixtures": fixtures,
    }
    (ROOT / "docs/phase6-evidence.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Phase 6 verification PASS; docs/phase6-evidence.json written")


if __name__ == "__main__":
    main()
