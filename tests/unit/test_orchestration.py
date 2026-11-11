from datetime import UTC, date, datetime

import pytest

from src.orchestration.tasks import parse_batch_day


def test_scheduled_and_explicit_historical_day():
    interval = datetime(2017, 11, 24, tzinfo=UTC)
    assert parse_batch_day({}, interval) == date(2017, 11, 24)
    assert parse_batch_day({"batch_date": "2017-11-25"}, interval) == date(2017, 11, 25)
    assert parse_batch_day({"batch_date": "2017-11-25"}, None) == date(2017, 11, 25)
    with pytest.raises(ValueError):
        parse_batch_day({"batch_date": "invalid"}, interval)
