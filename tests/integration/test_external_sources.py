import json
import os
import uuid
from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest
from psycopg import sql

from src.common.config import load_settings
from src.common.db import connection
from src.common.external_audit import audited_run
from src.ingestion.api_ingestion import FxError, ingest
from src.ingestion.sqlserver_ingestion import apply_change
from src.orchestration.tasks import MIGRATION, execute_step, quality, release, transform

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_DB_TESTS") != "1", reason="requires local PostgreSQL"
)


@pytest.fixture
def settings():
    original = load_settings()
    name = "external_test_" + uuid.uuid4().hex
    with connection(original) as db:
        db.autocommit = True
        db.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    try:
        yield replace(original, database=name)
    finally:
        with connection(original) as db:
            db.autocommit = True
            db.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


def test_fx_cache_refresh_and_failure_audit(settings, monkeypatch):
    day = date(2017, 11, 24)
    monkeypatch.setattr(
        "src.ingestion.api_ingestion.fetch_rate", lambda *_: (day, Decimal("3.2314"))
    )
    assert ingest(settings, day, "first")["counts"]["inserted"] == 1

    def offline(*_):
        raise FxError("transport_retry_exhausted")

    monkeypatch.setattr("src.ingestion.api_ingestion.fetch_rate", offline)
    assert ingest(settings, day, "cached")["counts"]["cache_hit"]
    with pytest.raises(RuntimeError):
        ingest(settings, day, "failure", refresh=True)
    monkeypatch.setattr("src.ingestion.api_ingestion.fetch_rate", lambda *_: (day, Decimal("3.25")))
    assert ingest(settings, day, "revision", refresh=True)["counts"]["updated"] == 1
    ingest(settings, date(2017, 11, 25), "weekend")
    with connection(settings) as db:
        assert db.execute("SELECT count(*),max(rate) FROM raw.fx_rates").fetchone() == (
            1,
            Decimal("3.25"),
        )
        assert db.execute("SELECT count(*) FROM raw.fx_requests").fetchone()[0] == 2
        assert (
            db.execute(
                "SELECT count(*) FROM metadata.external_runs WHERE status='failed'"
            ).fetchone()[0]
            == 1
        )


def test_stock_upserts_ignore_old_sequences_and_preserve_tombstones(settings):
    product = "a" * 32
    row = {
        "product_id": product,
        "quantity": 100,
        "is_deleted": False,
        "updated_at": "2026-01-01T00:00:00",
    }
    with audited_run(settings, "synthetic_sqlserver", "test") as (db, run_id, _):
        db.execute("CREATE TABLE raw.products(data jsonb NOT NULL)")
        db.execute(
            "INSERT INTO raw.products VALUES(%s::jsonb)", (json.dumps({"product_id": product}),)
        )
        assert apply_change(db, run_id, 1, "inventory", json.dumps(row)) == 1
        assert apply_change(db, run_id, 2, "inventory", json.dumps({**row, "quantity": 110})) == 1
        assert apply_change(db, run_id, 1, "inventory", json.dumps(row)) == 0
        assert db.execute("SELECT quantity FROM raw.inventory").fetchone()[0] == 110
        assert (
            apply_change(db, run_id, 3, "inventory", json.dumps({**row, "is_deleted": True})) == 1
        )
        assert db.execute("SELECT is_deleted FROM raw.inventory").fetchone()[0]


def test_orchestration_failure_control_is_audited_and_releasable(settings, monkeypatch):
    monkeypatch.setattr("src.orchestration.tasks.load_settings", lambda: settings)
    monkeypatch.setattr("src.orchestration.tasks.quality", lambda *_: {"checks": 4})
    with pytest.raises(RuntimeError):
        execute_step("quality", date(2017, 11, 24), "test-run", 1, "until_released")
    release("test-run")
    execute_step("quality", date(2017, 11, 24), "test-run", 2, "until_released")
    with connection(settings) as db:
        assert db.execute(
            "SELECT status FROM metadata.orchestration_steps ORDER BY started_at"
        ).fetchall() == [("failed",), ("success",)]


def test_daily_summary_keeps_items_and_payments_separate(settings):
    from pathlib import Path

    day = date(2017, 11, 24)
    run_id = uuid.uuid4()
    with connection(settings) as db:
        root = Path(__file__).resolve().parents[2]
        db.execute((root / "sql/init/002_csv_raw.sql").read_text())
        db.execute((root / "sql/init/003_external_sources.sql").read_text())
        db.execute(MIGRATION.read_text())
        db.execute(
            """INSERT INTO metadata.ingestion_runs(run_id,source,batch_id,mode,status,input_hashes)
            VALUES(%s,'test','test','full','success','{}')""",
            (run_id,),
        )
        payloads = {
            "orders": [
                {
                    "order_id": "order",
                    "customer_id": "customer",
                    "order_purchase_timestamp": str(day) + " 12:00:00",
                }
            ],
            "order_items": [
                {"order_id": "order", "order_item_id": str(i), "price": str(i * 10)} for i in (1, 2)
            ],
            "order_payments": [
                {"order_id": "order", "payment_sequential": str(i), "payment_value": "15"}
                for i in (1, 2)
            ],
        }
        for table, rows in payloads.items():
            for index, row in enumerate(rows):
                db.execute(
                    sql.SQL(
                        "INSERT INTO {}(business_key,data,row_hash,first_run_id,last_run_id) VALUES(%s,%s::jsonb,%s,%s,%s)"
                    ).format(sql.Identifier("raw", table)),
                    (str(index), json.dumps(row), "a" * 64, run_id, run_id),
                )
        db.execute(
            "INSERT INTO metadata.external_runs(run_id,source,batch_id,status) VALUES(%s,'fx_ecb','test','success')",
            (run_id,),
        )
        db.execute("INSERT INTO raw.fx_rates VALUES('USD','BRL',%s,'ECB',3.2,%s)", (day, run_id))
        db.execute("INSERT INTO raw.fx_requests VALUES(%s,%s,%s)", (day, day, run_id))
        for task_id in ("csv", "fx", "inventory"):
            db.execute(
                """INSERT INTO metadata.orchestration_steps(step_id,dag_run_id,task_id,batch_date,attempt,status)
                VALUES(%s,'test-run',%s,%s,1,'success')""",
                (uuid.uuid4(), task_id, day),
            )
    transform(settings, day, "test-run")
    transform(settings, day, "test-run")
    assert quality(settings, day, "test-run") == {"checks": 4}
    with connection(settings) as db:
        assert db.execute(
            "SELECT orders,items,payments,item_value,payment_value FROM staging.daily_ingestion_summary"
        ).fetchall() == [(1, 2, 2, Decimal(30), Decimal(30))]
