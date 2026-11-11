from unittest.mock import MagicMock, patch

import psycopg
import pytest

from src.common.config import load_settings
from src.common.db import connection
from src.ingestion.csv_ingestion import CsvStructureError, iter_batches


@pytest.fixture
def settings(tmp_path):
    return load_settings(
        tmp_path / "absent.env",
        {
            "POSTGRES_USER": "test",
            "POSTGRES_DB": "test",
            "POSTGRES_PASSWORD": "secret",
        },
    )


def test_config_precedence_validation_and_secret_redaction(tmp_path):
    env = tmp_path / "config.env"
    env.write_text("POSTGRES_USER=test\nPOSTGRES_DB=test\nPOSTGRES_PASSWORD=private\n")
    config = load_settings(env, {"INGEST_BATCH_SIZE": "7"})
    assert config.batch_size == 7
    assert "private" not in repr(config)
    with pytest.raises(ValueError, match="POSTGRES_PORT"):
        load_settings(env, {"POSTGRES_PORT": "bad-secret-value"})
    with pytest.raises(ValueError, match="POSTGRES_PASSWORD is required"):
        load_settings(tmp_path / "missing", {})


def test_batches_preserve_multiline_fields_and_remainder(tmp_path):
    path = tmp_path / "source.csv"
    path.write_text('\ufeffid,note\n1,"hello\nworld"\n2,\n3,last\n')
    batches = list(iter_batches(path, 2, ["id", "note"]))
    assert [len(batch) for batch in batches] == [2, 1]
    assert batches[0][0] == (1, {"id": "1", "note": "hello\nworld"})
    assert batches[1][0][0] == 3


@pytest.mark.parametrize("content", ["id,id\n1,2\n", "id,note\n1\n", "id\n1,extra\n"])
def test_bad_csv_fails_without_row_values(tmp_path, content):
    path = tmp_path / "source.csv"
    path.write_text(content)
    with pytest.raises(CsvStructureError):
        list(iter_batches(path))


def test_connection_retries_only_establishment(settings):
    handle = MagicMock()
    with (
        patch(
            "src.common.db.psycopg.connect", side_effect=[psycopg.OperationalError(), handle]
        ) as connect,
        patch("src.common.db.time.sleep") as sleep,
    ):
        with connection(settings) as actual:
            assert actual == handle
        assert connect.call_count == 2
        sleep.assert_called_once_with(1)
        assert connect.call_args.kwargs["connect_timeout"] == 5


def test_failed_connection_redacts_driver_detail(settings):
    with (
        patch("src.common.db.psycopg.connect", side_effect=psycopg.OperationalError("secret")),
        patch("src.common.db.time.sleep"),
        pytest.raises(ConnectionError) as error,
        connection(settings),
    ):
        pass
    assert "secret" not in str(error.value)


def test_transaction_error_is_not_retried(settings):
    handle = MagicMock()
    with patch("src.common.db.psycopg.connect", return_value=handle) as connect:
        with pytest.raises(RuntimeError), connection(settings):
            raise RuntimeError("transaction failed")
        connect.assert_called_once()
