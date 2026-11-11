"""Opt-in disposable PostgreSQL test: RUN_DB_TESTS=1 python -m pytest tests/integration."""

import csv
import os
import uuid
from dataclasses import replace
from datetime import date

import psycopg
import pytest
from psycopg import sql

from src.common.config import load_settings
from src.common.db import connection
from src.ingestion.csv_pipeline import CONTRACTS, run

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_DB_TESTS") != "1", reason="requires local PostgreSQL"
)


@pytest.fixture
def database(tmp_path):
    original = load_settings()
    name = "csv_test_" + uuid.uuid4().hex
    with connection(original) as admin:
        admin.autocommit = True
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    settings = replace(original, database=name, raw_dir=tmp_path, batch_size=1)
    try:
        yield settings
    finally:
        with connection(original) as admin:
            admin.autocommit = True
            admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


def write_sources(directory, amount="10", invalid=False):
    for source, spec in CONTRACTS.items():
        with (directory / spec["filename"]).open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=spec["columns"])
            writer.writeheader()
            for number in (1, 2):
                row = dict.fromkeys(spec["columns"], "test")
                for key in spec["keys"]:
                    row[key] = str(number)
                if source == "geolocation":
                    row["geolocation_zip_code_prefix"] = str(number)
                for field in row:
                    if field.endswith("_id"):
                        row[field] = str(number) * 32
                for field in ("price", "freight_value", "payment_value"):
                    if field in row:
                        row[field] = amount if field != "freight_value" else "0"
                if source == "orders":
                    row["order_purchase_timestamp"] = f"2017-01-0{number} 12:00:00"
                if source == "order_items" and invalid and number == 1:
                    row["price"] = "private-invalid-input"
                writer.writerow(row)
                if source == "geolocation":
                    writer.writerow(row)


def snapshot(settings):
    with connection(settings) as db:
        return {
            source: db.execute(
                sql.SQL("SELECT business_key,row_hash FROM {} ORDER BY business_key").format(
                    sql.Identifier("raw", source)
                )
            ).fetchall()
            for source in CONTRACTS
        }


def test_atomic_replay_updates_rejections_backfill_and_recovery(database):
    write_sources(database.raw_dir)
    first = run(database, "full")
    assert first["counts"]["geolocation"]["deduplicated"] == 2
    initial = snapshot(database)
    for _ in range(3):
        replay = run(database, "day-1", date(2017, 1, 1), date(2017, 1, 2))
        assert replay["counts"]["orders"]["accepted"] == 1
        assert snapshot(database) == initial
    write_sources(database.raw_dir, amount="20")
    with pytest.raises(RuntimeError, match="simulated_failure"):
        run(database, "recover", fail_source="order_items")
    assert snapshot(database) == initial
    recovered = run(database, "recover")
    assert recovered["counts"]["order_items"]["updated"] == 2
    updated = snapshot(database)
    write_sources(database.raw_dir, invalid=True)
    with pytest.raises(RuntimeError, match="invalid_nonnegative_amount") as error:
        run(database, "bad")
    assert "private-invalid-input" not in str(error.value)
    assert snapshot(database) == updated
    with connection(database) as db:
        assert (
            db.execute(
                "SELECT count(*) FROM metadata.ingestion_runs WHERE status='failed'"
            ).fetchone()[0]
            == 2
        )
        assert (
            db.execute("SELECT count(*) FROM metadata.rejections WHERE field='price'").fetchone()[0]
            == 1
        )
        assert (
            db.execute(
                "SELECT count(*) FROM metadata.checkpoints WHERE batch_id='recover'"
            ).fetchone()[0]
            == 9
        )
        assert (
            db.execute("SELECT sum((data->>'price')::numeric) FROM raw.order_items").fetchone()[0]
            == 40
        )
    # Replaying an earlier date must not move the high-water mark backward.
    write_sources(database.raw_dir, amount="20")
    run(database, "backfill", date(2017, 1, 1), date(2017, 1, 2))
    with connection(database) as db:
        assert db.execute("SELECT min(watermark) FROM metadata.checkpoints").fetchone()[0] == date(
            2017, 1, 2
        )


def test_incremental_arrivals_and_duplicate_key_failure(database):
    write_sources(database.raw_dir)
    run(database, "first-day", date(2017, 1, 1), date(2017, 1, 2))
    with connection(database) as db:
        assert db.execute("SELECT count(*) FROM raw.orders").fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM raw.order_items").fetchone()[0] == 1
    run(database, "second-day", date(2017, 1, 2), date(2017, 1, 3))
    with connection(database) as db:
        assert db.execute("SELECT count(*) FROM raw.orders").fetchone()[0] == 2
    original = snapshot(database)
    spec = CONTRACTS["orders"]
    path = database.raw_dir / spec["filename"]
    with path.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    with path.open("a", newline="") as stream:
        csv.DictWriter(stream, fieldnames=spec["columns"]).writerow(rows[0])
    with pytest.raises(RuntimeError, match="duplicate_business_key"):
        run(database, "duplicate-key")
    assert snapshot(database) == original
    with connection(database) as db:
        assert (
            db.execute(
                "SELECT count(*) FROM metadata.checkpoints WHERE batch_id='second-day'"
            ).fetchone()[0]
            == 9
        )


def test_raw_constraints_are_enforced_by_postgres(database):
    write_sources(database.raw_dir)
    result = run(database, "constraints")
    with connection(database) as db:
        with pytest.raises(psycopg.errors.CheckViolation), db.transaction():
            db.execute(
                """INSERT INTO raw.orders (business_key,data,row_hash,first_run_id,last_run_id)
                VALUES ('bad','{}',%s,%s,%s)""",
                ("a" * 64, result["run_id"], result["run_id"]),
            )
        with pytest.raises(psycopg.errors.UniqueViolation), db.transaction():
            db.execute("INSERT INTO raw.orders SELECT * FROM raw.orders LIMIT 1")


def test_mid_run_input_change_rolls_back_data_and_checkpoints(database, monkeypatch):
    from src.ingestion import csv_pipeline

    write_sources(database.raw_dir)
    run(database, "baseline")
    original_rows = snapshot(database)
    with connection(database) as db:
        original_checkpoints = db.execute(
            "SELECT source,batch_id,watermark,run_id FROM metadata.checkpoints ORDER BY source"
        ).fetchall()
    real_hashes = csv_pipeline.file_hashes
    calls = 0

    def changed_fingerprint(directory):
        nonlocal calls
        hashes = real_hashes(directory)
        calls += 1
        if calls == 2:
            hashes["orders"] = "0" * 64
        return hashes

    write_sources(database.raw_dir, amount="20")
    monkeypatch.setattr(csv_pipeline, "file_hashes", changed_fingerprint)
    with pytest.raises(RuntimeError, match="input_changed_during_run"):
        run(database, "changed-in-flight")
    assert snapshot(database) == original_rows
    with connection(database) as db:
        assert (
            db.execute(
                "SELECT source,batch_id,watermark,run_id FROM metadata.checkpoints ORDER BY source"
            ).fetchall()
            == original_checkpoints
        )
        assert db.execute(
            "SELECT status,error_code FROM metadata.ingestion_runs WHERE batch_id='changed-in-flight'"
        ).fetchone() == ("failed", "input_changed_during_run")
