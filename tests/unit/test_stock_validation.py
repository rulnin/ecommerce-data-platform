import json
from unittest.mock import MagicMock

import pytest

from src.ingestion.sqlserver_ingestion import StockError, apply_change

PAYLOAD = {
    "product_id": "a" * 32,
    "quantity": 100,
    "is_deleted": False,
    "updated_at": "2026-01-01T00:00:00",
}


def test_unknown_entity_and_missing_mapping_fail_before_writes():
    db = MagicMock()
    with pytest.raises(StockError, match="unknown_source_entity"):
        apply_change(db, "run", 1, "unexpected", "{}")
    db.execute.return_value.fetchone.return_value = None
    with pytest.raises(StockError, match="missing_product_mapping"):
        apply_change(db, "run", 1, "inventory", json.dumps(PAYLOAD))
    assert db.execute.call_count == 1


@pytest.mark.parametrize("quantity", [-1, 1.5, True])
def test_bad_quantity_rejected(quantity):
    db = MagicMock()
    db.execute.return_value.fetchone.return_value = (1,)
    with pytest.raises(StockError, match="invalid_stock_value"):
        apply_change(db, "run", 1, "inventory", json.dumps({**PAYLOAD, "quantity": quantity}))
