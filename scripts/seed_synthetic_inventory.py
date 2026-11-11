"""Seed deterministic simulated stock for valid public product IDs; preserve existing rows."""

import json
import os

from dotenv import dotenv_values

from src.common.config import load_settings
from src.common.db import connection
from src.common.sqlserver import ROOT, sqlserver_connection


def seed():
    with connection(load_settings()) as pg:
        products = [
            row[0]
            for row in pg.execute(
                "SELECT data->>'product_id' FROM raw.products ORDER BY business_key LIMIT 100"
            )
        ]
    if len(products) != 100 or any(len(product) != 32 for product in products):
        raise ValueError("Seed requires at least 100 valid public products from Phase 2")
    with sqlserver_connection(admin=True, master=True) as source:
        source.autocommit = True
        source.execute("IF DB_ID('inventory_demo') IS NULL CREATE DATABASE inventory_demo")
        config = {**dotenv_values(ROOT / ".env"), **os.environ}
        password = config["SQLSERVER_PASSWORD"].replace("'", "''")
        source.execute(
            "IF SUSER_ID('inventory_reader') IS NULL EXEC('CREATE LOGIN inventory_reader WITH PASSWORD = ''"
            + password.replace("'", "''")
            + "''')"
        )
    with sqlserver_connection(admin=True) as source:
        for batch in (ROOT / "sql/init/003_synthetic_sqlserver.sql").read_text().split("\nGO\n"):
            if batch.strip():
                source.execute(batch)
        source.execute(
            "IF USER_ID('inventory_reader') IS NULL CREATE USER inventory_reader FOR LOGIN inventory_reader"
        )
        source.execute("GRANT SELECT ON dbo.ChangeLog TO inventory_reader")
        source.execute("GRANT SELECT ON dbo.ChangeCounter TO inventory_reader")
        for index, product in enumerate(products, start=1):
            source.execute(
                "IF NOT EXISTS(SELECT 1 FROM dbo.Products WHERE product_id=?) INSERT dbo.Products VALUES(?)",
                product,
                product,
            )
            source.execute(
                """IF NOT EXISTS(SELECT 1 FROM dbo.Inventory WHERE product_id=?)
                INSERT dbo.Inventory(product_id,quantity) VALUES(?,100)""",
                product,
                product,
            )
            source.execute(
                """IF NOT EXISTS(SELECT 1 FROM dbo.StockMovements WHERE movement_id=?)
                INSERT dbo.StockMovements(movement_id,product_id,delta) VALUES(?,?,100)""",
                index,
                index,
                product,
            )
        counts = source.execute(
            "SELECT (SELECT count(*) FROM dbo.Inventory),(SELECT count(*) FROM dbo.StockMovements)"
        ).fetchone()
    return {"synthetic": True, "inventory": counts[0], "stock_movements": counts[1]}


if __name__ == "__main__":
    print(json.dumps(seed()))
