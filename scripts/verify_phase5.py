"""Verify live warehouse metrics and changed-row behavior in a disposable DB.

Run from the repository root: .venv/bin/python -m scripts.verify_phase5
Never changes the persisted raw dataset; only the uniquely named test DB is dropped.
"""

import json
import uuid
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from importlib.metadata import version
from pathlib import Path

from psycopg import sql

from scripts.dbt import ROOT, run_dbt
from src.common.config import load_settings
from src.common.db import connection


def checked_dbt(*args, extra_env=None):
    if run_dbt(list(args), extra_env=extra_env):
        raise RuntimeError("dbt command failed; evidence not updated")


def snapshot(settings, schema="marts"):
    with connection(settings) as db:
        result = {}
        for model in (
            "dim_customer",
            "dim_product",
            "dim_seller",
            "dim_date",
            "fct_order_items",
            "fct_payments",
            "fct_daily_sales",
        ):
            # Ordered logical content excludes physical tuple ordering.
            result[model] = db.execute(
                sql.SQL(
                    "SELECT count(*), md5(string_agg(row_to_json(t)::text, '' ORDER BY row_to_json(t)::text)) "
                    "FROM {} t"
                ).format(sql.Identifier(schema, model))
            ).fetchone()
        return result


def live_metrics(settings):
    with connection(settings) as db:
        raw = db.execute("""SELECT
            (SELECT count(*) FROM raw.order_items),
            (SELECT sum((data->>'price')::numeric) FROM raw.order_items),
            (SELECT sum((data->>'freight_value')::numeric) FROM raw.order_items),
            (SELECT count(*) FROM raw.order_payments),
            (SELECT sum((data->>'payment_value')::numeric) FROM raw.order_payments)""").fetchone()
        facts = db.execute("""SELECT
            (SELECT count(*) FROM marts.fct_order_items),
            (SELECT sum(item_price_brl) FROM marts.fct_order_items),
            (SELECT sum(freight_value_brl) FROM marts.fct_order_items),
            (SELECT count(*) FROM marts.fct_payments),
            (SELECT sum(payment_value_brl) FROM marts.fct_payments)""").fetchone()
        daily = db.execute("""SELECT sum(item_count), sum(item_value_brl), sum(freight_value_brl),
            sum(payment_count), sum(payment_value_brl) FROM marts.fct_daily_sales""").fetchone()
        assert raw == facts == daily, (raw, facts, daily)
        coverage = db.execute("""SELECT count(*), count(brl_per_usd),
            count(*) FILTER (WHERE brl_per_usd IS NULL AND item_value_usd IS NULL)
            FROM marts.fct_daily_sales""").fetchone()
        return {
            "raw_fact_daily_totals": list(raw),
            "days_fx_covered_uncovered": coverage,
        }


def fixture(db):
    db.execute("CREATE SCHEMA raw")
    contracts = json.loads((ROOT / "src/ingestion/contracts.json").read_text())
    for name in contracts:
        db.execute(
            sql.SQL(
                "CREATE TABLE raw.{} (business_key text PRIMARY KEY, data jsonb, "
                "row_hash text, loaded_at timestamptz)"
            ).format(sql.Identifier(name))
        )
    for name, columns in {
        "fx_rates": "base_currency text, quote_currency text, rate_date date, provider text, rate numeric",
        "fx_requests": "requested_date date, rate_date date",
        "inventory": "product_id text, quantity int, is_deleted boolean, updated_at timestamptz, change_seq bigint, is_synthetic boolean",
        "stock_movements": "movement_id bigint, product_id text, delta int, is_deleted boolean, updated_at timestamptz, change_seq bigint, is_synthetic boolean",
    }.items():
        db.execute(
            sql.SQL("CREATE TABLE raw.{} ({})").format(sql.Identifier(name), sql.SQL(columns))
        )
    rows = {
        "customers": [
            {
                "customer_id": "c",
                "customer_unique_id": "person",
                "customer_zip_code_prefix": "00100",
            }
        ],
        "products": [{"product_id": "p"}],
        "sellers": [{"seller_id": "s"}],
        "orders": [
            {
                "order_id": "o",
                "customer_id": "c",
                "order_status": "delivered",
                "order_purchase_timestamp": "2017-11-25 10:00:00",
            }
        ],
        "order_items": [
            {
                "order_id": "o",
                "order_item_id": str(i),
                "product_id": "p",
                "seller_id": "s",
                "price": str(i * 10),
                "freight_value": "2",
            }
            for i in (1, 2)
        ],
        "order_payments": [
            {
                "order_id": "o",
                "payment_sequential": str(i),
                "payment_type": "credit_card",
                "payment_installments": "1",
                "payment_value": str(i * 10 + 2),
            }
            for i in (1, 2)
        ],
    }
    for name, records in rows.items():
        for i, row in enumerate(records, 1):
            db.execute(
                sql.SQL("INSERT INTO raw.{} VALUES (%s,%s::jsonb,%s,now())").format(
                    sql.Identifier(name)
                ),
                (f"{name}_{i}", json.dumps(row), "fixture"),
            )
    db.execute("INSERT INTO raw.fx_rates VALUES ('USD','BRL','2017-11-24','ECB',2)")
    db.execute("INSERT INTO raw.inventory VALUES ('p',0,true,now(),1,true)")
    db.execute("INSERT INTO raw.stock_movements VALUES (1,'p',-1,true,now(),2,true)")


def changed_rows(original):
    name = "dbt_verify_" + uuid.uuid4().hex
    test_settings = replace(original, database=name)
    env = {"DBT_TEST_DATABASE": name}
    # Target output is isolated so test docs/manifest cannot replace dev artifacts.
    args = [
        "--target",
        "test",
        "--target-path",
        "/tmp/" + name,
        "--vars",
        json.dumps(
            {
                "quality_expected_counts": {
                    "orders": 1,
                    "order_items": 2,
                    "order_payments": 2,
                }
            }
        ),
    ]
    with connection(original) as db:
        db.autocommit = True
        db.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    try:
        with connection(test_settings) as db:
            fixture(db)
        checked_dbt("build", *args, extra_env=env)
        with connection(test_settings) as db:
            assert db.execute(
                "SELECT item_count,payment_count,item_value_brl,payment_value_brl,"
                "item_value_usd,fx_rate_date::text FROM verification_marts.fct_daily_sales"
            ).fetchone() == (2, 2, Decimal(30), Decimal(34), Decimal(15), "2017-11-24")
            # Change a price and the parent day/status without a loaded_at advance.
            db.execute(
                "UPDATE raw.order_items SET data=jsonb_set(data,'{price}', '\"15\"') WHERE business_key='order_items_1'"
            )
            db.execute(
                "UPDATE raw.orders SET data=data || "
                '\'{"order_purchase_timestamp":"2017-11-26 10:00:00","order_status":"canceled"}\'::jsonb'
            )
        checked_dbt("build", *args, extra_env=env)
        with connection(test_settings) as db:
            assert db.execute(
                "SELECT count(*),sum(item_price_brl),min(purchase_date)::text,"
                "min(order_status) FROM verification_marts.fct_order_items"
            ).fetchone() == (2, Decimal(35), "2017-11-26", "canceled")
            assert db.execute(
                "SELECT item_value_brl, payment_value_brl,delivered_item_value_brl "
                "FROM verification_marts.fct_daily_sales"
            ).fetchone() == (Decimal(35), Decimal(34), 0)
            assert db.execute(
                "SELECT is_deleted,is_synthetic FROM verification_staging.stg_inventory"
            ).fetchone() == (True, True)
        with connection(test_settings) as db:
            # A new item with an old source timestamp must still be inserted.
            db.execute(
                "INSERT INTO raw.order_items SELECT 'order_items_3', "
                'data || \'{"order_item_id":"3","price":"5"}\'::jsonb, row_hash, loaded_at '
                "FROM raw.order_items WHERE business_key='order_items_1'"
            )
        # The fixture intentionally adds an item; approve its new test baseline.
        args[-1] = json.dumps(
            {
                "quality_expected_counts": {
                    "orders": 1,
                    "order_items": 3,
                    "order_payments": 2,
                }
            }
        )
        checked_dbt("build", *args, extra_env=env)
        with connection(test_settings) as db:
            assert db.execute(
                "SELECT count(*),sum(item_price_brl) FROM verification_marts.fct_order_items"
            ).fetchone() == (3, Decimal(40))
            assert db.execute(
                "SELECT item_value_brl,payment_value_brl FROM verification_marts.fct_daily_sales"
            ).fetchone() == (Decimal(40), Decimal(34))
            physical = db.execute(
                "SELECT order_item_key,xmin::text,ctid::text FROM "
                "verification_marts.fct_order_items ORDER BY order_item_key"
            ).fetchall()
        first = snapshot(test_settings, "verification_marts")
        checked_dbt("build", *args, extra_env=env)
        assert snapshot(test_settings, "verification_marts") == first
        with connection(test_settings) as db:
            assert (
                db.execute(
                    "SELECT order_item_key,xmin::text,ctid::text FROM "
                    "verification_marts.fct_order_items ORDER BY order_item_key"
                ).fetchall()
                == physical
            )
        checked_dbt("build", "--full-refresh", *args, extra_env=env)
        assert snapshot(test_settings, "verification_marts") == first
        return {
            "late_new_item": "PASS",
            "unchanged_item_rows_not_rewritten": "PASS",
            "price_update": "PASS",
            "parent_date_status_update_without_watermark": "PASS",
            "two_items_two_payments_no_multiplication": "PASS",
            "weekend_fx": "PASS",
            "synthetic_tombstones_preserved": "PASS",
            "replay": "PASS",
            "full_refresh_equivalence": "PASS",
        }
    finally:
        with connection(original) as db:
            db.autocommit = True
            db.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


def main():
    settings = load_settings()
    checked_dbt("debug")
    checked_dbt("build")
    baseline = snapshot(settings)
    metrics = live_metrics(settings)
    checked_dbt("build")
    assert snapshot(settings) == baseline
    build_results = json.loads((ROOT / "dbt/target/run_results.json").read_text())
    statuses = [row["status"] for row in build_results["results"]]
    assert statuses and all(status in ("success", "pass") for status in statuses)
    changed = changed_rows(settings)
    checked_dbt("docs", "generate")
    results = json.loads((ROOT / "dbt/target/run_results.json").read_text())
    manifest = json.loads((ROOT / "dbt/target/manifest.json").read_text())
    model_count = sum(n["resource_type"] == "model" for n in manifest["nodes"].values())
    test_count = sum(n["resource_type"] == "test" for n in manifest["nodes"].values())
    evidence = {
        "status": "PASS",
        "verified_at": datetime.now(UTC).isoformat(),
        "dbt_core": version("dbt-core"),
        "dbt_postgres": version("dbt-postgres"),
        "build_results": {status: statuses.count(status) for status in sorted(set(statuses))},
        "models": model_count,
        "tests": test_count,
        "metrics": metrics,
        "stable_replay": True,
        "warehouse_rows_and_hashes": baseline,
        "disposable_fixture": changed,
        "docs_generated": all(
            (ROOT / "dbt/target" / f).exists()
            for f in ("index.html", "manifest.json", "catalog.json")
        ),
        "last_command_elapsed_seconds": results.get("elapsed_time"),
    }
    assert evidence["docs_generated"]
    Path("docs/phase5-evidence.json").write_text(json.dumps(evidence, indent=2, default=str) + "\n")
    print("Phase 5 verification PASS; docs/phase5-evidence.json written")


if __name__ == "__main__":
    main()
