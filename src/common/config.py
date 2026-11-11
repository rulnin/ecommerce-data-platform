"""Read configuration without mutating process environment or exposing secrets."""

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    database: str
    user: str
    password: str = field(repr=False)
    raw_dir: Path = Path("data/raw")
    batch_size: int = 1000
    connect_timeout: int = 5
    statement_timeout_ms: int = 60000
    connect_attempts: int = 3


def load_settings(env_file=Path(".env"), environ: Mapping[str, str] | None = None):
    values = {**dotenv_values(env_file), **(os.environ if environ is None else environ)}

    def positive_integer(name, default, maximum):
        try:
            value = int(values.get(name, default))
        except TypeError, ValueError:
            raise ValueError(f"{name} must be a positive integer") from None
        if not 1 <= value <= maximum:
            raise ValueError(f"{name} must be between 1 and {maximum}")
        return value

    for name in ("POSTGRES_PASSWORD", "POSTGRES_USER", "POSTGRES_DB"):
        if not values.get(name):
            raise ValueError(f"{name} is required")
    return Settings(
        host=values.get("POSTGRES_HOST") or "127.0.0.1",
        port=positive_integer("POSTGRES_PORT", 5432, 65535),
        database=values["POSTGRES_DB"],
        user=values["POSTGRES_USER"],
        password=values["POSTGRES_PASSWORD"],
        raw_dir=Path(values.get("RAW_DATA_DIR") or "data/raw"),
        batch_size=positive_integer("INGEST_BATCH_SIZE", 1000, 10000),
        connect_timeout=positive_integer("DB_CONNECT_TIMEOUT", 5, 60),
        statement_timeout_ms=positive_integer("DB_STATEMENT_TIMEOUT_MS", 60000, 600000),
        connect_attempts=positive_integer("DB_CONNECT_ATTEMPTS", 3, 5),
    )
