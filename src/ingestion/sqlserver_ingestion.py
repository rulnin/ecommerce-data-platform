"""Extract the transactional synthetic outbox; commit targets and cursor atomically."""

import argparse
import json
from datetime import UTC, datetime

from psycopg import sql

from src.common.config import load_settings
from src.common.external_audit import audited_run
from src.common.sqlserver import sqlserver_connection


class StockError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def apply_change(db, run_id, sequence, entity, body):
    if entity not in ("inventory", "stock_movements"):
        raise StockError("unknown_source_entity")
    row = json.loads(body)
    key = "product_id" if entity == "inventory" else "movement_id"
    product = row["product_id"]
    if not db.execute(
        "SELECT 1 FROM raw.products WHERE data->>'product_id'=%s", (product,)
    ).fetchone():
        raise StockError("missing_product_mapping")
    timestamp = datetime.fromisoformat(row["updated_at"]).replace(tzinfo=UTC)
    if not isinstance(row["is_deleted"], bool):
        raise TypeError("Invalid tombstone")
    value = row["quantity"] if entity == "inventory" else row["delta"]
    if type(value) is not int or (entity == "inventory" and value < 0):
        raise StockError("invalid_stock_value")
    columns = (
        ["product_id", "quantity"]
        if entity == "inventory"
        else ["movement_id", "product_id", "delta"]
    )
    values = [product, value] if entity == "inventory" else [row[key], product, value]
    columns += ["is_deleted", "updated_at", "change_seq", "run_id"]
    values += [row["is_deleted"], timestamp, sequence, run_id]
    statement = sql.SQL("""INSERT INTO {} AS target ({}) VALUES ({}) ON CONFLICT({}) DO UPDATE
        SET {} WHERE target.change_seq < excluded.change_seq""").format(
        sql.Identifier("raw", entity),
        sql.SQL(",").join(map(sql.Identifier, columns)),
        sql.SQL(",").join(sql.Placeholder() for _ in values),
        sql.Identifier(key),
        sql.SQL(",").join(
            sql.SQL("{}=excluded.{}").format(sql.Identifier(c), sql.Identifier(c))
            for c in columns
            if c != key
        ),
    )
    return db.execute(statement, values).rowcount


def ingest(settings, batch_id, fail_after=None):
    with audited_run(settings, "synthetic_sqlserver", batch_id) as (db, run_id, result):
        saved = db.execute(
            "SELECT watermark FROM metadata.external_checkpoints WHERE source='synthetic_sqlserver'"
        ).fetchone()
        cursor = saved[0] if saved else 0
        count = changed = deleted = 0
        result["provenance"] = {
            "synthetic": True,
            "database": "inventory_demo",
            "start_sequence": cursor,
        }
        with sqlserver_connection() as source:
            upper = source.execute("SELECT last_seq FROM dbo.ChangeCounter WHERE id=1").fetchone()[
                0
            ]
            if upper < cursor:
                raise StockError("source_sequence_reset")
            reader = source.cursor()
            reader.execute(
                """SELECT change_seq,entity,payload FROM dbo.ChangeLog
                WHERE change_seq>? AND change_seq<=? ORDER BY change_seq""",
                cursor,
                upper,
            )
            last = cursor
            while rows := reader.fetchmany(settings.batch_size):
                for sequence, entity, payload in rows:
                    result["provenance"].update(event_sequence=sequence, entity=entity)
                    if sequence != last + 1:
                        raise StockError("outbox_gap")
                    changed += apply_change(db, run_id, sequence, entity, payload)
                    deleted += bool(json.loads(payload)["is_deleted"])
                    count += 1
                    result["counts"] = {"read": count, "upserted": changed, "tombstones": deleted}
                    last = sequence
                    if fail_after is not None and count >= fail_after:
                        raise StockError("simulated_failure")
            if last != upper:
                raise StockError("incomplete_outbox_interval")
        db.execute(
            """INSERT INTO metadata.external_checkpoints(source,watermark,run_id)
            VALUES('synthetic_sqlserver',%s,%s) ON CONFLICT(source) DO UPDATE
            SET watermark=excluded.watermark,run_id=excluded.run_id,updated_at=clock_timestamp()""",
            (upper, run_id),
        )
        result["counts"] = {"read": count, "upserted": changed, "tombstones": deleted}
        result["provenance"]["end_sequence"] = upper
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-id", required=True)
    args = parser.parse_args()
    print(json.dumps(ingest(load_settings(), args.batch_id), indent=2))


if __name__ == "__main__":
    main()
