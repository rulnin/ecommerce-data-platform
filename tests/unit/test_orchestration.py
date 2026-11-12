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


def test_warehouse_subprocess_failure_is_not_reported_as_success(monkeypatch, tmp_path):
    import subprocess

    from src.orchestration.tasks import run_warehouse_module

    executable = tmp_path / "warehouse-python"
    executable.write_text("#!/bin/sh\nexit 7\n")
    executable.chmod(0o700)
    monkeypatch.setenv("WAREHOUSE_PYTHON", str(executable))
    with pytest.raises(subprocess.CalledProcessError) as error:
        run_warehouse_module("src.quality.publication")
    assert error.value.returncode == 7
