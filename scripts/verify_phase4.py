"""Verify the running LocalExecutor DAG, failed-run recovery and historical replays."""

import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path

import requests
from dotenv import dotenv_values

from src.common.config import load_settings
from src.common.db import connection
from src.orchestration.tasks import release


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--screenshots", action="store_true")
    args = parser.parse_args()
    config = dotenv_values(".env")
    base = "http://127.0.0.1:" + config.get("AIRFLOW_PORT", "8080")
    session = requests.Session()

    def authenticate():
        token = requests.post(
            base + "/auth/token",
            json={"username": "admin", "password": config["AIRFLOW_ADMIN_PASSWORD"]},
            timeout=30,
        )
        token.raise_for_status()
        session.headers["Authorization"] = "Bearer " + token.json()["access_token"]

    def call(method, path, **kwargs):
        response = session.request(method, base + path, timeout=30, **kwargs)
        if response.status_code == 401:
            authenticate()
            response = session.request(method, base + path, timeout=30, **kwargs)
        response.raise_for_status()
        return response.json()

    dag = "/api/v2/dags/ecommerce_pipeline"
    authenticate()
    call("PATCH", dag, json={"is_paused": False})
    prefix = "phase4_" + str(int(time.time()))
    runs, screenshots, log_files = [], [], []

    def wait(run_id, expected):
        previous = None
        for _ in range(1200):
            state = call("GET", dag + "/dagRuns/" + run_id)["state"]
            if state != previous:
                print(run_id, state, flush=True)
                previous = state
            if state in ("success", "failed"):
                if state != expected:
                    raise AssertionError(f"Unexpected DAG outcome: {run_id} {state}")
                return
            time.sleep(2)
        raise TimeoutError("DAG did not reach expected final state")

    def trigger(label, day, failure="none"):
        run_id = prefix + "_" + label
        call(
            "POST",
            dag + "/dagRuns",
            json={
                "dag_run_id": run_id,
                "logical_date": None,
                "conf": {"batch_date": day, "failure_mode": failure},
            },
        )
        runs.append({"run_id": run_id, "date": day})
        return run_id

    def snapshot():
        with connection(load_settings()) as db:
            return db.execute("""SELECT (SELECT count(*) FROM raw.orders),
                (SELECT count(*) FROM raw.order_items),(SELECT count(*) FROM raw.order_payments),
                (SELECT sum((data->>'price')::numeric) FROM raw.order_items),
                (SELECT sum((data->>'payment_value')::numeric) FROM raw.order_payments),
                (SELECT count(*) FROM raw.inventory),(SELECT count(*) FROM raw.stock_movements),
                (SELECT sum(quantity) FROM raw.inventory)""").fetchone()

    baseline = snapshot()
    success = trigger("success", "2017-11-24")
    wait(success, "success")
    if args.screenshots:
        from scripts.capture_airflow_ui import capture

        screenshots.append(capture("phase4-success"))
    failed = trigger("failure", "2017-11-24", "until_released")
    wait(failed, "failed")
    failed_tasks = call("GET", dag + "/dagRuns/" + failed + "/taskInstances")["task_instances"]
    quality_attempt = next(
        task["try_number"] for task in failed_tasks if task["task_id"] == "quality"
    )
    for attempt in range(1, quality_attempt + 1):
        payload = call(
            "GET",
            dag + "/dagRuns/" + failed + "/taskInstances/quality/logs/" + str(attempt),
            params={"full_content": True},
        )
        text = json.dumps(payload, indent=2)
        for key in (
            "POSTGRES_PASSWORD",
            "SQLSERVER_PASSWORD",
            "AIRFLOW_DB_PASSWORD",
            "AIRFLOW_ADMIN_PASSWORD",
            "AIRFLOW_JWT_SECRET",
            "AIRFLOW_FERNET_KEY",
        ):
            if config.get(key):
                text = text.replace(config[key], "[redacted]")
        path = Path("docs/airflow-evidence") / f"phase4-quality-attempt-{attempt}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n")
        log_files.append(str(path))
    if args.screenshots:
        screenshots.append(capture("phase4-failed"))
    release(failed)
    call(
        "POST",
        dag + "/clearTaskInstances",
        json={"dag_run_id": failed, "only_failed": True, "reset_dag_runs": True, "dry_run": False},
    )
    wait(failed, "success")
    if args.screenshots:
        screenshots.append(capture("phase4-recovered"))
    rerun = trigger("rerun", "2017-11-24")
    wait(rerun, "success")
    for day in ("2017-11-25", "2017-11-26"):
        wait(trigger("backfill_" + day, day), "success")
    existing = {
        r["dag_run_id"] for r in call("GET", dag + "/dagRuns", params={"limit": 100})["dag_runs"]
    }
    subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            "docker-compose.yml",
            "-f",
            "docker-compose.airflow.yml",
            "--profile",
            "airflow",
            "exec",
            "-T",
            "airflow-scheduler",
            "airflow",
            "backfill",
            "create",
            "--dag-id",
            "ecommerce_pipeline",
            "--from-date",
            "2017-11-25",
            "--to-date",
            "2017-11-26",
            "--reprocess-behavior",
            "completed",
            "--max-active-runs",
            "1",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    native = []
    for _ in range(60):
        native = [
            r
            for r in call("GET", dag + "/dagRuns", params={"limit": 100})["dag_runs"]
            if r["dag_run_id"] not in existing and r.get("run_type") == "backfill"
        ]
        if len(native) >= 2:
            break
        time.sleep(2)
    assert len(native) == 2
    for run in native:
        wait(run["dag_run_id"], "success")
        runs.append(
            {
                "run_id": run["dag_run_id"],
                "date": run.get("data_interval_start"),
                "native_backfill": True,
            }
        )
    assert snapshot() == baseline
    task_states = {}
    for run in runs:
        run_id = run["run_id"]
        instances = call("GET", dag + "/dagRuns/" + run_id + "/taskInstances")["task_instances"]
        task_states[run_id] = [
            {key: task.get(key) for key in ("task_id", "state", "try_number")} for task in instances
        ]
        assert {task["task_id"] for task in instances} == {
            "csv",
            "fx",
            "inventory",
            "transform",
            "quality",
            "publish",
            "analytics",
        }
        assert all(task["state"] == "success" for task in instances)
    with connection(load_settings()) as db:
        audits = db.execute(
            """SELECT dag_run_id,task_id,attempt,status,source_run_id,error_code
            FROM metadata.orchestration_steps WHERE dag_run_id=ANY(%s) ORDER BY started_at""",
            ([run["run_id"] for run in runs],),
        ).fetchall()
        assert any(row[3] == "failed" for row in audits)
        summaries = db.execute(
            "SELECT batch_date,orders,items,payments,item_value,payment_value FROM staging.daily_ingestion_summary ORDER BY batch_date"
        ).fetchall()
    call("PATCH", dag, json={"is_paused": True})
    output = {
        "result": "PASS",
        "runs": runs,
        "tasks": task_states,
        "attempt_audit": audits,
        "stable_csv_metrics": list(map(str, baseline)),
        "summaries": [[str(x) for x in row] for row in summaries],
        "screenshots": screenshots,
        "log_files": log_files,
        "constraints_sha256": hashlib.sha256(
            Path("airflow/constraints/constraints-3.14.txt").read_bytes()
        ).hexdigest(),
    }
    Path("docs/phase4-evidence.json").write_text(json.dumps(output, indent=2) + "\n")
    print(
        "PASS: success, failed-run recovery, rerun and two historical days; DAG paused", flush=True
    )


if __name__ == "__main__":
    main()
