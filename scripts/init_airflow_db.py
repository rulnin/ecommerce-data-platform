"""Provision an isolated metadata role/database, preserving an existing database."""

import base64
import secrets
from pathlib import Path

from dotenv import dotenv_values
from psycopg import sql

from src.common.config import load_settings
from src.common.db import connection


def main():
    path = Path(".env")
    config = dotenv_values(path)
    for key in ("AIRFLOW_DB_PASSWORD", "AIRFLOW_ADMIN_PASSWORD", "AIRFLOW_JWT_SECRET"):
        if not config.get(key):
            value = secrets.token_hex(32)
            with path.open("a") as stream:
                stream.write(f"\n{key}={value}\n")
            config[key] = value
    if not config.get("AIRFLOW_FERNET_KEY"):
        with path.open("a") as stream:
            stream.write(
                "\nAIRFLOW_FERNET_KEY="
                + base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
                + "\n"
            )
    path.chmod(0o600)
    with connection(load_settings()) as db:
        db.autocommit = True
        if not db.execute("SELECT 1 FROM pg_roles WHERE rolname='airflow_meta'").fetchone():
            db.execute(
                sql.SQL("CREATE ROLE airflow_meta LOGIN PASSWORD {}").format(
                    sql.Literal(config["AIRFLOW_DB_PASSWORD"])
                )
            )
        if not db.execute("SELECT 1 FROM pg_database WHERE datname='airflow_meta'").fetchone():
            db.execute("CREATE DATABASE airflow_meta OWNER airflow_meta")
        db.execute(Path("sql/init/004_orchestration.sql").read_text())
    print("Airflow metadata database ready; generated credentials remain in ignored .env")


if __name__ == "__main__":
    main()
