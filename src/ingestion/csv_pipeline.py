"""Transactional snapshot upserts with simulated date arrivals and audit evidence."""

import argparse
import hashlib
import json
import logging
import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from psycopg import sql
from psycopg.types.json import Jsonb

from src.common.config import load_settings
from src.common.db import connection
from src.ingestion.csv_ingestion import CsvStructureError, iter_batches

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = json.loads(Path(__file__).with_name("contracts.json").read_text())
LOGGER = logging.getLogger(__name__)
MONEY = {"price", "freight_value", "payment_value"}


class RejectedRow(ValueError):
    def __init__(self, source, record, field, code):
        self.source, self.record, self.field, self.code = source, record, field, code
        super().__init__(f"{source}: record={record} field={field} code={code}")


def encode(source, record, row):
    spec = CONTRACTS[source]
    for key in spec["keys"]:
        if not row[key]:
            raise RejectedRow(source, record, key, "empty_business_key")
    for field in MONEY & row.keys():
        try:
            value = Decimal(row[field])
            if not value.is_finite() or value < 0:
                raise InvalidOperation
        except InvalidOperation:
            raise RejectedRow(source, record, field, "invalid_nonnegative_amount") from None
    if source == "orders":
        try:
            datetime.fromisoformat(row["order_purchase_timestamp"])
        except ValueError:
            raise RejectedRow(
                source, record, "order_purchase_timestamp", "invalid_timestamp"
            ) from None
    content = json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    digest = hashlib.sha256(content.encode()).hexdigest()
    key = (
        json.dumps([row[k] for k in spec["keys"]], separators=(",", ":"))
        if spec["keys"]
        else digest
    )
    return key, content, digest


def file_hashes(directory):
    result = {}
    for source, spec in CONTRACTS.items():
        with (directory / spec["filename"]).open("rb") as stream:
            result[source] = hashlib.file_digest(stream, "sha256").hexdigest()
    return result


def selected_orders(directory, start, end):
    selected = set()
    maximum = None
    spec = CONTRACTS["orders"]
    for batch in iter_batches(directory / spec["filename"], expected_columns=spec["columns"]):
        for record, row in batch:
            encode("orders", record, row)
            day = datetime.fromisoformat(row["order_purchase_timestamp"]).date()
            maximum = max(maximum, day) if maximum else day
            if start is not None and start <= day < end:
                selected.add(row["order_id"])
    return selected, maximum


def load_source(db, settings, source, spec, run_id, selected, incremental, fail_after):
    db.execute("DROP TABLE IF EXISTS pg_temp.csv_stage")
    db.execute(
        "CREATE TEMP TABLE csv_stage (business_key text, data jsonb, row_hash text, record_number bigint) ON COMMIT DROP"
    )
    scanned = accepted = 0
    for batch in iter_batches(
        settings.raw_dir / spec["filename"], settings.batch_size, spec["columns"]
    ):
        rows = []
        for record, row in batch:
            scanned += 1
            if incremental and "order_id" in row and row["order_id"] not in selected:
                continue
            key, content, digest = encode(source, record, row)
            rows.append((key, content, digest, record))
        with db.cursor().copy("COPY csv_stage FROM STDIN") as copy:
            for row in rows:
                copy.write_row(row)
        accepted += len(rows)
        if fail_after is not None and accepted >= fail_after:
            raise RejectedRow(source, None, None, "simulated_failure")
    if spec["keys"]:
        duplicate = db.execute(
            "SELECT min(record_number) FROM csv_stage GROUP BY business_key HAVING count(*) > 1 LIMIT 1"
        ).fetchone()
        if duplicate:
            raise RejectedRow(source, duplicate[0], None, "duplicate_business_key")
    table = sql.Identifier("raw", source)
    inserted, updated, unchanged = db.execute(
        sql.SQL("""
        SELECT count(*) FILTER (WHERE t.business_key IS NULL),
               count(*) FILTER (WHERE t.business_key IS NOT NULL AND t.row_hash <> s.row_hash),
               count(*) FILTER (WHERE t.row_hash = s.row_hash)
        FROM (SELECT DISTINCT ON (business_key) * FROM csv_stage ORDER BY business_key, record_number) s
        LEFT JOIN {} t USING (business_key)
    """).format(table)
    ).fetchone()
    db.execute(
        sql.SQL("""
        INSERT INTO {} AS target (business_key,data,row_hash,first_run_id,last_run_id)
        SELECT business_key,data,row_hash,%s,%s FROM
          (SELECT DISTINCT ON (business_key) * FROM csv_stage ORDER BY business_key,record_number) s
        ON CONFLICT (business_key) DO UPDATE
        SET data=excluded.data,row_hash=excluded.row_hash,last_run_id=excluded.last_run_id,loaded_at=clock_timestamp()
        WHERE target.row_hash <> excluded.row_hash
    """).format(table),
        (run_id, run_id),
    )
    return {
        "scanned": scanned,
        "accepted": accepted,
        "inserted": inserted,
        "updated": updated,
        "unchanged": unchanged,
        "deduplicated": accepted - inserted - updated - unchanged,
    }


def run(settings, batch_id, start=None, end=None, fail_source=None, fail_after=1):
    if not batch_id or len(batch_id) > 200:
        raise ValueError("batch_id must contain 1 to 200 characters")
    if (start is None) != (end is None) or (start is not None and start >= end):
        raise ValueError("Provide both dates with start < end (end exclusive)")
    if fail_source is not None and fail_source not in CONTRACTS:
        raise ValueError("Unknown failure source")
    run_id = uuid.uuid4()
    counts = {}
    with connection(settings) as db:
        db.execute("SET lock_timeout = '30s'")
        db.execute("SELECT pg_advisory_lock(224902)")
        db.execute((ROOT / "sql/init/002_csv_raw.sql").read_text())
        db.commit()
        # Missing files still receive a failed audit record after run creation.
        db.execute(
            """INSERT INTO metadata.ingestion_runs
            (run_id,source,batch_id,mode,status,input_hashes) VALUES (%s,'olist_csv',%s,%s,'running','{}')""",
            (run_id, batch_id, "incremental" if start else "full"),
        )
        db.commit()
        source = "orders"
        try:
            hashes = file_hashes(settings.raw_dir)
            db.execute(
                "UPDATE metadata.ingestion_runs SET input_hashes=%s WHERE run_id=%s",
                (Jsonb(hashes), run_id),
            )
            db.commit()
            selected, maximum = selected_orders(settings.raw_dir, start, end)
            watermark = date.fromordinal(end.toordinal() - 1) if end else maximum
            db.execute(
                "UPDATE metadata.ingestion_runs SET input_hashes=%s, watermark=%s WHERE run_id=%s",
                (Jsonb(hashes), watermark, run_id),
            )
            for source, spec in CONTRACTS.items():
                previous = db.execute(
                    """SELECT r.input_hashes->>%s FROM metadata.checkpoints c
                    JOIN metadata.ingestion_runs r ON r.run_id=c.run_id
                    WHERE c.source=%s AND r.status='success'""",
                    (source, f"olist_csv:{source}"),
                ).fetchone()
                if (
                    start is not None
                    and "order_id" not in spec["columns"]
                    and previous
                    and previous[0] == hashes[source]
                ):
                    counts[source] = {
                        "scanned": 0,
                        "accepted": 0,
                        "inserted": 0,
                        "updated": 0,
                        "unchanged": 0,
                        "deduplicated": 0,
                        "unchanged_file_skipped": True,
                    }
                else:
                    counts[source] = load_source(
                        db,
                        settings,
                        source,
                        spec,
                        run_id,
                        selected,
                        start is not None,
                        fail_after if source == fail_source else None,
                    )
                db.execute(
                    """INSERT INTO metadata.checkpoints (source,batch_id,watermark,run_id)
                    VALUES (%s,%s,%s,%s) ON CONFLICT(source) DO UPDATE
                    SET batch_id=excluded.batch_id,watermark=greatest(metadata.checkpoints.watermark,excluded.watermark),
                        run_id=excluded.run_id,updated_at=clock_timestamp()""",
                    (f"olist_csv:{source}", batch_id, watermark, run_id),
                )
            if hashes != file_hashes(settings.raw_dir):
                raise RejectedRow("olist_csv", None, None, "input_changed_during_run")
            db.execute(
                """UPDATE metadata.ingestion_runs SET status='success',finished_at=clock_timestamp(),counts=%s
                WHERE run_id=%s""",
                (Jsonb(counts), run_id),
            )
            db.commit()
        except Exception as error:  # noqa: BLE001 -- audit and rollback every failure at the run boundary
            db.rollback()
            code = error.code if isinstance(error, RejectedRow) else type(error).__name__
            db.execute(
                """UPDATE metadata.ingestion_runs SET status='failed',finished_at=clock_timestamp(),
                error_code=%s,counts=%s WHERE run_id=%s""",
                (code, Jsonb(counts), run_id),
            )
            db.execute(
                """INSERT INTO metadata.rejections (run_id,source,record_number,field,error_code)
                VALUES (%s,%s,%s,%s,%s)""",
                (
                    run_id,
                    error.source if isinstance(error, RejectedRow) else source,
                    error.record
                    if isinstance(error, RejectedRow)
                    else (error.record_number if isinstance(error, CsvStructureError) else None),
                    error.field if isinstance(error, RejectedRow) else None,
                    code,
                ),
            )
            db.commit()
            LOGGER.error("csv_run_failed run_id=%s code=%s", run_id, code)
            raise RuntimeError(
                f"CSV run {run_id} failed; code={code}; see metadata.rejections"
            ) from None
        finally:
            db.execute("SELECT pg_advisory_unlock(224902)")
    LOGGER.info("csv_run_success run_id=%s", run_id)
    return {"run_id": str(run_id), "counts": counts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--start", type=date.fromisoformat)
    parser.add_argument("--end", type=date.fromisoformat)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    try:
        result = run(load_settings(), args.batch_id, args.start, args.end)
    except (RuntimeError, ValueError, ConnectionError) as error:
        parser.exit(1, str(error) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
