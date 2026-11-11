"""Source boundaries and failure behavior without a live SQL Server or network."""

import csv
import json
from contextlib import nullcontext
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from src.common.config import load_settings
from src.ingestion.csv_pipeline import CONTRACTS, selected_orders
from src.ingestion.sqlserver_ingestion import StockError, ingest


def test_simulated_date_slice_is_start_inclusive_end_exclusive(tmp_path):
    spec = CONTRACTS["orders"]
    with (tmp_path / spec["filename"]).open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=spec["columns"])
        writer.writeheader()
        for key, timestamp in [
            ("before", "2017-01-01 23:59:59"),
            ("start", "2017-01-02 00:00:00"),
            ("last", "2017-01-02 23:59:59"),
            ("end", "2017-01-03 00:00:00"),
        ]:
            row = dict.fromkeys(spec["columns"], "")
            row.update(order_id=key, customer_id="customer", order_purchase_timestamp=timestamp)
            writer.writerow(row)
    selected, latest = selected_orders(tmp_path, date(2017, 1, 2), date(2017, 1, 3))
    assert selected == {"start", "last"}
    assert latest == date(2017, 1, 3)


def stock_context(tmp_path, upper, sequences):
    settings = load_settings(
        tmp_path / "absent",
        {"POSTGRES_USER": "test", "POSTGRES_DB": "test", "POSTGRES_PASSWORD": "test"},
    )
    db, source = MagicMock(), MagicMock()
    db.execute.return_value.fetchone.return_value = (5,)
    source.execute.return_value.fetchone.return_value = (upper,)
    payload = json.dumps({"is_deleted": False})
    source.cursor.return_value.fetchmany.side_effect = [
        [(sequence, "inventory", payload)] for sequence in sequences
    ] + [[]]
    result = {}
    return settings, db, source, result


def test_stock_advances_only_to_the_frozen_complete_interval(tmp_path):
    settings, db, source, result = stock_context(tmp_path, 7, [6, 7])
    with (
        patch(
            "src.ingestion.sqlserver_ingestion.audited_run",
            return_value=nullcontext((db, "run", result)),
        ),
        patch(
            "src.ingestion.sqlserver_ingestion.sqlserver_connection",
            return_value=nullcontext(source),
        ),
        patch("src.ingestion.sqlserver_ingestion.apply_change", return_value=1) as apply,
    ):
        assert ingest(settings, "batch") is result
    assert [call.args[2] for call in apply.call_args_list] == [6, 7]
    assert source.cursor.return_value.execute.call_args.args[1:] == (5, 7)
    assert db.execute.call_args.args[1] == (7, "run")
    assert result["provenance"]["start_sequence"] == 5
    assert result["provenance"]["end_sequence"] == 7


@pytest.mark.parametrize(
    ("upper", "sequences", "error"),
    [
        (4, [], "source_sequence_reset"),
        (7, [7], "outbox_gap"),
        (7, [6], "incomplete_outbox_interval"),
    ],
)
def test_invalid_stock_interval_never_writes_checkpoint(tmp_path, upper, sequences, error):
    settings, db, source, result = stock_context(tmp_path, upper, sequences)
    with (
        patch(
            "src.ingestion.sqlserver_ingestion.audited_run",
            return_value=nullcontext((db, "run", result)),
        ),
        patch(
            "src.ingestion.sqlserver_ingestion.sqlserver_connection",
            return_value=nullcontext(source),
        ),
        patch("src.ingestion.sqlserver_ingestion.apply_change", return_value=1),
        pytest.raises(StockError, match=error),
    ):
        ingest(settings, "batch")
    # Only the initial checkpoint read is allowed; no advancement on a bad range.
    assert db.execute.call_count == 1
