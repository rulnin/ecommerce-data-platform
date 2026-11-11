"""SQL Server connection with project-local ODBC runtime support."""

import ctypes
import importlib
import os
from contextlib import contextmanager
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]


def driver_module():
    local = ROOT / ".local/odbc"
    if local.exists():
        for name in ("libltdl.so.7", "libodbcinst.so.2", "libodbc.so.2"):
            ctypes.CDLL(str(local / "usr/lib/x86_64-linux-gnu" / name), mode=ctypes.RTLD_GLOBAL)
        os.environ["ODBCSYSINI"] = str(local / "etc")
    return importlib.import_module("pyodbc")


@contextmanager
def sqlserver_connection(admin=False, master=False):
    config = {**dotenv_values(ROOT / ".env"), **os.environ}
    module = driver_module()
    password = config.get("MSSQL_SA_PASSWORD" if admin else "SQLSERVER_PASSWORD")
    if not password:
        raise ValueError("Missing SQL Server credentials")

    def quote(value):
        return "{" + str(value).replace("}", "}}") + "}"

    fields = {
        "DRIVER": "ODBC Driver 18 for SQL Server",
        "SERVER": config.get("SQLSERVER_HOST", "127.0.0.1")
        + ","
        + config.get("SQLSERVER_PORT", "1433"),
        "DATABASE": "master" if master else "inventory_demo",
        "UID": "sa" if admin else "inventory_reader",
        "PWD": password,
        "Encrypt": "yes",
        "TrustServerCertificate": "yes",
    }
    try:
        handle = module.connect(
            ";".join(f"{key}={quote(value)}" for key, value in fields.items()), timeout=10
        )
    except module.Error:
        raise ConnectionError(
            "SQL Server connection failed; verify local driver and source service"
        ) from None
    handle.timeout = 30
    try:
        yield handle
        handle.commit()
    except Exception:
        handle.rollback()
        raise
    finally:
        handle.close()
