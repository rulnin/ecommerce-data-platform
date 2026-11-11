"""Measure the fixed snapshot in disposable DBs and verify a real warehouse restore.

Run: python -m scripts.verify_phase8. Existing warehouse rows are never changed.
An additive index migration is applied only if the measured query median improves.
"""

import hashlib
import json
import logging
import os
import platform
import resource
import statistics
import subprocess
import time
import uuid
from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path

from psycopg import sql

from scripts.dbt import ROOT
from scripts.verify_phase2 import metrics
from src.common.config import load_settings
from src.common.db import connection
from src.ingestion.csv_pipeline import CONTRACTS, run

DAY, END = date(2017, 11, 24), date(2017, 11, 25)


def create_database(original, name):
    with connection(original) as db:
        db.autocommit = True
        db.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))


def drop_database(original, name):
    with connection(original) as db:
        db.autocommit = True
        db.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


def fingerprint(settings):
    """Table row counts and order-independent canonical row hashes; no row bodies."""
    with connection(settings) as db:
        tables = db.execute("""SELECT schemaname,tablename FROM pg_tables
            WHERE schemaname NOT IN ('pg_catalog','information_schema')
            ORDER BY schemaname,tablename""").fetchall()
        return {
            f"{schema}.{table}": db.execute(
                sql.SQL(
                    "SELECT count(*),md5(string_agg(md5(to_jsonb(t)::text),'' ORDER BY md5(to_jsonb(t)::text))) FROM {} t"
                ).format(sql.Identifier(schema, table))
            ).fetchone()
            for schema, table in tables
        }


def plans(db, query):
    db.execute(query).fetchone()  # Explicit warm-up; no cache flushing claims.
    results = []
    for _ in range(5):
        results.append(
            db.execute("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + query).fetchone()[0][0]
        )
    return {
        "execution_ms": [p["Execution Time"] for p in results],
        "median_ms": statistics.median(p["Execution Time"] for p in results),
        "plans": results,
    }


def index_benchmark(settings):
    query = (ROOT / "sql/queries/day_item_total.sql").read_text()
    with connection(settings) as db:
        db.execute("ANALYZE raw.orders")
        db.execute("ANALYZE raw.order_items")
        expected = db.execute(query).fetchone()
        before = plans(db, query)
        started = time.perf_counter()
        db.execute((ROOT / "sql/init/008_lookup_indexes.sql").read_text())
        build_seconds = time.perf_counter() - started
        db.execute("ANALYZE raw.orders")
        db.execute("ANALYZE raw.order_items")
        after = plans(db, query)
        assert db.execute(query).fetchone() == expected
        sizes = dict(
            db.execute("""SELECT indexrelname,pg_relation_size(indexrelid) FROM pg_stat_user_indexes
            WHERE indexrelname IN ('orders_purchase_text_idx','order_items_order_id_idx')""").fetchall()
        )
    return {
        "query_result": [str(x) for x in expected],
        "before": before,
        "after": after,
        "index_build_seconds": build_seconds,
        "index_bytes": sizes,
        "median_ratio_before_over_after": before["median_ms"] / after["median_ms"],
    }


def backup_restore(settings):
    name = "restore_verify_" + uuid.uuid4().hex
    directory = ROOT / "data/backups"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (
        "warehouse-"
        + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        + "-"
        + uuid.uuid4().hex[:8]
        + ".dump"
    )
    baseline = fingerprint(settings)
    started = time.perf_counter()
    # Native client lives in the existing Postgres container; no host install required.
    with path.open("xb") as stream:
        path.chmod(0o600)
        subprocess.run(
            [
                "docker",
                "compose",
                "exec",
                "-T",
                "postgres",
                "pg_dump",
                "-U",
                settings.user,
                "-d",
                settings.database,
                "--format=custom",
                "--no-owner",
                "--no-privileges",
            ],
            stdout=stream,
            check=True,
            timeout=600,
        )
    dump_seconds = time.perf_counter() - started
    create_database(settings, name)
    try:
        started = time.perf_counter()
        with path.open("rb") as stream:
            subprocess.run(
                [
                    "docker",
                    "compose",
                    "exec",
                    "-T",
                    "postgres",
                    "pg_restore",
                    "-U",
                    settings.user,
                    "--dbname",
                    name,
                    "--no-owner",
                    "--no-privileges",
                    "--exit-on-error",
                ],
                stdin=stream,
                check=True,
                timeout=600,
            )
        restore_seconds = time.perf_counter() - started
        restored = fingerprint(replace(settings, database=name))
        assert baseline == restored
        assert fingerprint(settings) == baseline
        with path.open("rb") as stream:
            dump_sha256 = hashlib.file_digest(stream, "sha256").hexdigest()
        return {
            "status": "PASS",
            "dump_seconds": dump_seconds,
            "restore_seconds": restore_seconds,
            "dump_bytes": path.stat().st_size,
            "dump_sha256": dump_sha256,
            "local_ignored_path": str(path.relative_to(ROOT)),
            "tables": baseline,
            "source_unchanged": True,
            "all_table_counts_and_hashes_match": True,
            "scope": "warehouse only; SQL Server and Airflow metadata require separate backups",
        }
    finally:
        drop_database(settings, name)


def main():
    original = load_settings()
    name = "benchmark_verify_" + uuid.uuid4().hex
    settings = replace(original, database=name)
    expected = json.loads((ROOT / "docs/dataset-manifest.json").read_text())["files_sha256"]
    hashes = {}
    byte_count = 0
    for spec in CONTRACTS.values():
        path = settings.raw_dir / spec["filename"]
        with path.open("rb") as stream:
            hashes[path.name] = hashlib.file_digest(stream, "sha256").hexdigest()
        byte_count += path.stat().st_size
    assert hashes == expected, "Snapshot differs from the reviewed dataset manifest"
    evidence = {
        "status": "RUNNING",
        "started_at": datetime.now(UTC).isoformat(),
        "dataset_sha256": hashes,
        "dataset_bytes": byte_count,
        "batch_size": settings.batch_size,
        "environment": {
            "python": platform.python_version(),
            "kernel": platform.release(),
            "machine": platform.machine(),
            "logical_cpus": os.cpu_count(),
            "meminfo": Path("/proc/meminfo").read_text().splitlines()[:3],
        },
        "runs": [],
    }
    with connection(original) as db:
        evidence["environment"]["postgres_version"] = db.execute("SELECT version()").fetchone()[0]
        evidence["environment"]["pg_settings"] = dict(
            db.execute(
                "SELECT name,setting FROM pg_settings WHERE name IN ('shared_buffers','work_mem','jit','max_parallel_workers_per_gather')"
            ).fetchall()
        )
    evidence["environment"]["docker_stats_before"] = subprocess.check_output(
        ["docker", "stats", "--no-stream", "--format", "{{json .}}"], text=True
    ).splitlines()
    artifact_dir = ROOT / "docs/performance"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(artifact_dir / "pipeline.txt", mode="w")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)
    create_database(original, name)
    try:

        def measured(label, incremental=False, fail=False):
            started = time.perf_counter()
            try:
                result = run(
                    settings,
                    "phase8-" + label,
                    DAY if incremental else None,
                    END if incremental else None,
                    fail_source="order_items" if fail else None,
                    fail_after=1 if fail else None,
                )
                assert not fail, "Forced failure did not occur"
                run_id = result["run_id"]
            except RuntimeError:
                if not fail:
                    raise
                with connection(settings) as db:
                    run_id = str(
                        db.execute(
                            "SELECT run_id FROM metadata.ingestion_runs WHERE batch_id=%s ORDER BY started_at DESC LIMIT 1",
                            ("phase8-" + label,),
                        ).fetchone()[0]
                    )
            elapsed = time.perf_counter() - started
            with connection(settings) as db:
                row = db.execute(
                    """SELECT status,extract(epoch FROM finished_at-started_at),
                    counts,error_code,(SELECT count(*) FROM metadata.rejections x WHERE x.run_id=r.run_id)
                    FROM metadata.ingestion_runs r WHERE run_id=%s""",
                    (run_id,),
                ).fetchone()
            record = {
                "label": label,
                "run_id": str(run_id),
                "wall_seconds": elapsed,
                "database_duration_seconds": str(row[1]),
                "status": row[0],
                "counts": row[2],
                "error_code": row[3],
                "rejection_count": row[4],
            }
            assert row[0] == ("failed" if fail else "success")
            evidence["runs"].append(record)
            print(f"{label}: {row[0]} {elapsed:.3f}s", flush=True)
            return record

        measured("initial-empty-full")
        baseline = metrics(settings)
        evidence["baseline"] = baseline
        for mode in ("full-replay", "incremental-replay"):
            for trial in range(1, 4):
                measured(f"{mode}-{trial}", incremental=mode.startswith("incremental"))
                assert metrics(settings) == baseline
        measured("forced-failure", incremental=True, fail=True)
        assert metrics(settings) == baseline
        measured("recovery", incremental=True)
        assert metrics(settings) == baseline
        evidence["sql"] = index_benchmark(settings)
        # Apply only a measured useful, additive index set to the persistent warehouse.
        assert evidence["sql"]["after"]["median_ms"] < evidence["sql"]["before"]["median_ms"]
        before = metrics(original)
        with connection(original) as db:
            db.execute((ROOT / "sql/init/008_lookup_indexes.sql").read_text())
        assert metrics(original) == before
        evidence["warehouse_indexes_applied"] = True
        evidence["stable_replay_and_recovery"] = True
        evidence["environment"]["python_peak_rss_kib"] = resource.getrusage(
            resource.RUSAGE_SELF
        ).ru_maxrss
    finally:
        drop_database(original, name)
        logging.getLogger().removeHandler(handler)
        handler.close()
    evidence["backup_restore"] = backup_restore(original)
    evidence["environment"]["docker_stats_after"] = subprocess.check_output(
        ["docker", "stats", "--no-stream", "--format", "{{json .}}"], text=True
    ).splitlines()
    evidence["median_wall_seconds"] = {
        mode: statistics.median(
            row["wall_seconds"] for row in evidence["runs"] if row["label"].startswith(mode + "-")
        )
        for mode in ("full-replay", "incremental-replay")
    }
    evidence["full_over_incremental_wall_ratio"] = (
        evidence["median_wall_seconds"]["full-replay"]
        / evidence["median_wall_seconds"]["incremental-replay"]
    )
    evidence["pipeline_log"] = "docs/performance/pipeline.txt"
    evidence["measurement_limits"] = [
        "Single host, sequential fixed-order trials, no cache reset or confidence interval.",
        "Daily replay is a simulated date slice, not live CDC or new-arrival throughput.",
        "Docker memory samples are not peaks; Python RSS excludes PostgreSQL.",
        "Query speedup is not ingestion or end-to-end pipeline speedup.",
        "Warehouse restore excludes Airflow metadata, SQL Server and role secrets.",
    ]
    evidence["status"] = "PASS"
    evidence["finished_at"] = datetime.now(UTC).isoformat()
    (ROOT / "docs/phase8-evidence.json").write_text(
        json.dumps(evidence, indent=2, default=str) + "\n"
    )
    print("Phase 8 verification PASS; docs/phase8-evidence.json written", flush=True)


if __name__ == "__main__":
    main()
