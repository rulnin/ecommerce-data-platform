"""Independent run audit for external sources; preserve failed attempts."""

import uuid
from contextlib import contextmanager
from pathlib import Path

from psycopg.types.json import Jsonb

from src.common.db import connection


@contextmanager
def audited_run(settings, source, batch_id):
    if not batch_id or len(batch_id) > 200:
        raise ValueError("batch_id must contain 1 to 200 characters")
    run_id = uuid.uuid4()
    result = {"run_id": str(run_id), "counts": {}, "provenance": {}}
    with connection(settings) as db:
        db.execute("SET lock_timeout='30s'")
        db.execute("SELECT pg_advisory_lock(hashtext(%s))", (source,))
        db.execute(
            (Path(__file__).resolve().parents[2] / "sql/init/003_external_sources.sql").read_text()
        )
        db.execute(
            "INSERT INTO metadata.external_runs(run_id,source,batch_id,status) VALUES(%s,%s,%s,'running')",
            (run_id, source, batch_id),
        )
        db.commit()
        try:
            yield db, run_id, result
            db.execute(
                """UPDATE metadata.external_runs SET status='success',finished_at=clock_timestamp(),
                counts=%s,provenance=%s WHERE run_id=%s""",
                (Jsonb(result["counts"]), Jsonb(result["provenance"]), run_id),
            )
            db.commit()
        except Exception as error:  # noqa: BLE001 -- sanitize all errors at the audit boundary
            db.rollback()
            code = getattr(error, "code", type(error).__name__)
            db.execute(
                """UPDATE metadata.external_runs SET status='failed',finished_at=clock_timestamp(),
                error_code=%s,counts=%s,provenance=%s WHERE run_id=%s""",
                (code, Jsonb(result["counts"]), Jsonb(result["provenance"]), run_id),
            )
            db.commit()
            raise RuntimeError(f"{source} run {run_id} failed ({code}); inspect audit") from None
        finally:
            db.execute("SELECT pg_advisory_unlock(hashtext(%s))", (source,))
