"""Provision Metabase metadata and a read-only warehouse login without resetting data."""

import secrets
from pathlib import Path

from dotenv import dotenv_values
from psycopg import sql

from src.common.config import load_settings
from src.common.db import connection


def main():
    path = Path(".env")
    config = dotenv_values(path)
    for key in (
        "METABASE_ADMIN_PASSWORD",
        "METABASE_DB_PASSWORD",
        "METABASE_REPORTING_PASSWORD",
        "METABASE_ENCRYPTION_SECRET_KEY",
    ):
        if not config.get(key):
            config[key] = secrets.token_hex(32)
            with path.open("a") as stream:
                stream.write(f"\n{key}={config[key]}\n")
    if not config.get("METABASE_ADMIN_EMAIL"):
        with path.open("a") as stream:
            stream.write("\nMETABASE_ADMIN_EMAIL=admin@ecommerce.local\n")
    path.chmod(0o600)
    settings = load_settings()
    with connection(settings) as db:
        db.autocommit = True
        for role, key in (
            ("metabase_app", "METABASE_DB_PASSWORD"),
            ("metabase_reporting", "METABASE_REPORTING_PASSWORD"),
        ):
            if not db.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (role,)).fetchone():
                db.execute(
                    sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(
                        sql.Identifier(role), sql.Literal(config[key])
                    )
                )
        if not db.execute("SELECT 1 FROM pg_database WHERE datname='metabase_app'").fetchone():
            db.execute("CREATE DATABASE metabase_app OWNER metabase_app")
        db.execute(
            sql.SQL("GRANT CONNECT ON DATABASE {} TO metabase_reporting").format(
                sql.Identifier(settings.database)
            )
        )
        db.execute("CREATE SCHEMA IF NOT EXISTS published")
        db.execute("GRANT USAGE ON SCHEMA published TO metabase_reporting")
        db.execute("GRANT SELECT ON ALL TABLES IN SCHEMA published TO metabase_reporting")
        # Applies to future tables created by the publication role, including first publication.
        db.execute(
            sql.SQL(
                "ALTER DEFAULT PRIVILEGES FOR ROLE {} IN SCHEMA published "
                "GRANT SELECT ON TABLES TO metabase_reporting"
            ).format(sql.Identifier(settings.user))
        )
        db.execute("ALTER ROLE metabase_reporting SET default_transaction_read_only = on")
    print("Metabase databases and reporting access ready; credentials remain in .env")


if __name__ == "__main__":
    main()
