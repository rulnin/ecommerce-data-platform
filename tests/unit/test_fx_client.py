import json
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
import requests

from src.ingestion.api_ingestion import FxError, fetch_rate, parse_rate

BODY = {"date": "2017-11-24", "base": "USD", "quote": "BRL", "rate": "3.2314"}


def response(status=200, content=None):
    handle = MagicMock()
    handle.__enter__.return_value = handle
    handle.status_code = status
    handle.iter_content.return_value = [content or json.dumps(BODY).encode()]
    return handle


def test_weekend_retains_provider_date_and_decimal():
    assert parse_rate(BODY, date(2017, 11, 25)) == (date(2017, 11, 24), Decimal("3.2314"))


@pytest.mark.parametrize(
    "change",
    [
        {"rate": "NaN"},
        {"rate": "-1"},
        {"rate": "1e40"},
        {"quote": "USD"},
        {"date": "2017-11-26"},
        {"date": "2017-10-01"},
    ],
)
def test_bad_rate_contract(change):
    with pytest.raises(FxError, match="invalid_rate_contract"):
        parse_rate({**BODY, **change}, date(2017, 11, 25))


def test_transient_retry_then_success():
    session = MagicMock()
    session.get.side_effect = [response(429), response()]
    sleeps = []
    assert fetch_rate(date(2017, 11, 25), session, sleeps.append)[1] == Decimal("3.2314")
    assert sleeps == [1]
    assert session.get.call_args.kwargs["timeout"] == (10, 30)


def test_bounded_timeouts_and_permanent_http_errors():
    session = MagicMock()
    session.get.side_effect = requests.Timeout("do not log transport details")
    sleeps = []
    with pytest.raises(FxError, match="transport_retry_exhausted"):
        fetch_rate(date(2017, 11, 25), session, sleeps.append)
    assert session.get.call_count == 3 and sleeps == [1, 2]
    session = MagicMock()
    session.get.return_value = response(404)
    with pytest.raises(FxError, match="http_404"):
        fetch_rate(date(2017, 11, 25), session, sleeps.append)
    assert session.get.call_count == 1


@pytest.mark.parametrize(
    "content,code", [(b"not json", "invalid_json"), (b"a" * 65537, "oversized_response")]
)
def test_bad_payload(content, code):
    session = MagicMock()
    session.get.return_value = response(content=content)
    with pytest.raises(FxError, match=code):
        fetch_rate(date(2017, 11, 25), session)
