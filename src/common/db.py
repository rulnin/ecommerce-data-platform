"""Bounded connection establishment; transactions are never silently replayed."""

import logging
import time
from contextlib import contextmanager

import psycopg

from src.common.config import Settings

LOGGER = logging.getLogger(__name__)


@contextmanager
def connection(settings: Settings):
    handle = None
    for attempt in range(settings.connect_attempts):
        try:
            handle = psycopg.connect(
                host=settings.host,
                port=settings.port,
                dbname=settings.database,
                user=settings.user,
                password=settings.password,
                connect_timeout=settings.connect_timeout,
                options=f"-c statement_timeout={settings.statement_timeout_ms}",
                application_name="ecommerce-ingestion",
            )
            break
        except psycopg.OperationalError:
            if attempt + 1 == settings.connect_attempts:
                raise ConnectionError(
                    "PostgreSQL connection failed after bounded retries"
                ) from None
            LOGGER.warning("database_connect_retry attempt=%d", attempt + 1)
            time.sleep(min(2**attempt, 4))
    # psycopg's context commits on success and rolls back on exception, then closes.
    with handle:
        yield handle
