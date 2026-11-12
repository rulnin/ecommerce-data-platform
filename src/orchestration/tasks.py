"""Observable orchestration around existing loaders and a small operational summary."""

import hashlib
import json
import logging
import os
import subprocess
import sys
import uuid
from datetime import date, timedelta
from pathlib import Path

from src.common.config import load_settings
from src.common.db import connection
from src.ingestion.api_ingestion import ingest as load_fx
from src.ingestion.csv_pipeline import run as load_csv
from src.ingestion.sqlserver_ingestion import ingest as load_inventory

LOGGER = logging.getLogger(__name__)
MIGRATION = Path(__file__).resolve().parents[2] / "sql/init/004_orchestration.sql"


def parse_batch_day(config, interval_start):
    if config.get("batch_date"):
        return date.fromisoformat(config["batch_date"])
    if interval_start is None:
        raise ValueError("Manual runs without a data interval require batch_date")
    return interval_start.date()


def transform(settings, day, run_id):
    with connection(settings) as db:
        db.execute(
            """WITH orders AS (
            SELECT data->>'order_id' AS id FROM raw.orders
            WHERE left(data->>'order_purchase_timestamp',10)=%s
        ), items AS (
            SELECT i.data FROM raw.order_items i JOIN orders o ON o.id=i.data->>'order_id'
        ), payments AS (
            SELECT p.data FROM raw.order_payments p JOIN orders o ON o.id=p.data->>'order_id'
        ) INSERT INTO staging.daily_ingestion_summary
            (batch_date,orders,items,payments,item_value,payment_value,dag_run_id)
        SELECT %s,(SELECT count(*) FROM orders),(SELECT count(*) FROM items),
            (SELECT count(*) FROM payments),(SELECT coalesce(sum((data->>'price')::numeric),0) FROM items),
            (SELECT coalesce(sum((data->>'payment_value')::numeric),0) FROM payments),%s
        ON CONFLICT(batch_date) DO UPDATE SET orders=excluded.orders,items=excluded.items,
            payments=excluded.payments,item_value=excluded.item_value,payment_value=excluded.payment_value,
            dag_run_id=excluded.dag_run_id,computed_at=clock_timestamp()""",
            (str(day), day, run_id),
        )
    return {}


def quality(settings, day, run_id):
    with connection(settings) as db:
        steps = db.execute(
            """SELECT count(DISTINCT task_id) FROM metadata.orchestration_steps
            WHERE dag_run_id=%s AND status='success' AND task_id IN ('csv','fx','inventory')""",
            (run_id,),
        ).fetchone()[0]
        if steps != 3:
            raise ValueError("Source task provenance incomplete")
        fx = db.execute(
            """SELECT r.rate_date,r.rate FROM raw.fx_requests q JOIN raw.fx_rates r
            ON r.rate_date=q.rate_date WHERE q.requested_date=%s""",
            (day,),
        ).fetchone()
        if not fx or not 0 <= (day - fx[0]).days <= 7 or fx[1] <= 0:
            raise ValueError("Dated FX observation missing or stale")
        if db.execute("""SELECT count(*) FROM raw.inventory i WHERE NOT EXISTS
            (SELECT 1 FROM raw.products p WHERE p.data->>'product_id'=i.product_id)""").fetchone()[
            0
        ]:
            raise ValueError("Synthetic product mapping missing")
        summary = db.execute(
            "SELECT orders,items,payments FROM staging.daily_ingestion_summary WHERE batch_date=%s AND dag_run_id=%s",
            (day, run_id),
        ).fetchone()
        if summary is None or any(value < 0 for value in summary):
            raise ValueError("Operational summary missing or invalid")
    return {"checks": 4}


def run_warehouse_module(module):
    """Run warehouse tooling in its own environment; propagate failures to Airflow."""
    subprocess.run(
        [os.environ.get("WAREHOUSE_PYTHON", sys.executable), "-m", module],
        cwd=Path(__file__).resolve().parents[2],
        check=True,
    )
    return {}


def execute_step(task_id, day, dag_run_id, attempt, failure_mode="none"):
    settings = load_settings()
    step_id = uuid.uuid4()
    with connection(settings) as db:
        db.execute(MIGRATION.read_text())
        db.execute(
            """INSERT INTO metadata.orchestration_steps
            (step_id,dag_run_id,task_id,batch_date,attempt,status) VALUES(%s,%s,%s,%s,%s,'running')""",
            (step_id, dag_run_id, task_id, day, attempt),
        )
    batch_id = "airflow:" + hashlib.sha256(dag_run_id.encode()).hexdigest()[:24] + ":" + task_id
    LOGGER.info(
        "pipeline_step_start task=%s run_id=%s attempt=%s date=%s",
        task_id,
        dag_run_id,
        attempt,
        day,
    )
    try:
        if task_id == "quality" and failure_mode != "none":
            with connection(settings) as db:
                db.execute(
                    "INSERT INTO metadata.orchestration_controls VALUES(%s,false) ON CONFLICT DO NOTHING",
                    (dag_run_id,),
                )
                released = db.execute(
                    "SELECT released FROM metadata.orchestration_controls WHERE dag_run_id=%s",
                    (dag_run_id,),
                ).fetchone()[0]
            if not released and (failure_mode == "until_released" or attempt == 1):
                raise RuntimeError(
                    "Simulated quality failure; release control before clearing failed task"
                )
        if task_id == "csv":
            result = load_csv(settings, batch_id, day, day + timedelta(days=1))
        elif task_id == "fx":
            result = load_fx(settings, day, batch_id)
        elif task_id == "inventory":
            result = load_inventory(settings, batch_id)
        elif task_id == "transform":
            result = transform(settings, day, dag_run_id)
        elif task_id == "quality":
            result = quality(settings, day, dag_run_id)
        elif task_id == "publish":
            result = run_warehouse_module("src.quality.publication")
        elif task_id == "analytics":
            result = run_warehouse_module("scripts.verify_phase9")
        else:
            raise ValueError("Unknown orchestration step")
        with connection(settings) as db:
            db.execute(
                """UPDATE metadata.orchestration_steps SET status='success',finished_at=clock_timestamp(),
                source_run_id=%s WHERE step_id=%s""",
                (result.get("run_id"), step_id),
            )
        LOGGER.info(
            "pipeline_step_success task=%s run_id=%s source_run_id=%s",
            task_id,
            dag_run_id,
            result.get("run_id"),
        )
        return {"task_id": task_id, "date": str(day), "source_run_id": result.get("run_id")}
    except Exception as error:  # noqa: BLE001 -- preserve attempt status without logging payloads/credentials
        with connection(settings) as db:
            db.execute(
                """UPDATE metadata.orchestration_steps SET status='failed',finished_at=clock_timestamp(),
                error_code=%s WHERE step_id=%s""",
                (type(error).__name__, step_id),
            )
        LOGGER.error(
            "pipeline_step_failed task=%s run_id=%s code=%s",
            task_id,
            dag_run_id,
            type(error).__name__,
        )
        raise RuntimeError(
            f"Orchestration {task_id} failed; inspect step audit ({type(error).__name__})"
        ) from None


def release(dag_run_id):
    with connection(load_settings()) as db:
        db.execute(
            "UPDATE metadata.orchestration_controls SET released=true WHERE dag_run_id=%s",
            (dag_run_id,),
        )
    print(json.dumps({"released": dag_run_id}))
