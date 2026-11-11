"""The publication gate must reject incomplete or non-passing dbt artifacts."""

import json

import pytest

from src.quality.publication import MODELS
from src.quality.publication import test_results as read_results


def artifacts(
    directory,
    *,
    test_status="pass",
    failures=0,
    missing_model=False,
    missing_test=False,
):
    nodes = {f"model.{name}": {"name": name, "resource_type": "model"} for name in MODELS}
    nodes["test.grain"] = {"name": "grain", "resource_type": "test"}
    results = [{"unique_id": uid, "status": "success"} for uid in nodes if uid.startswith("model.")]
    if missing_model:
        results.pop()
    if not missing_test:
        results.append({"unique_id": "test.grain", "status": test_status, "failures": failures})
    (directory / "manifest.json").write_text(json.dumps({"nodes": nodes}))
    (directory / "run_results.json").write_text(json.dumps({"results": results}))


def test_complete_success_opens_gate(tmp_path):
    artifacts(tmp_path)
    checks, valid = read_results(None, tmp_path)
    assert valid and checks[0]["status"] == "PASS"


@pytest.mark.parametrize(
    "options",
    [
        {"test_status": "skipped", "failures": None},
        {"test_status": "error", "failures": None},
        {"test_status": "warn", "failures": 1},
        {"test_status": "pass", "failures": 1},
        {"missing_model": True},
        {"missing_test": True},
    ],
)
def test_incomplete_or_nonpassing_result_closes_gate(tmp_path, options):
    artifacts(tmp_path, **options)
    _, valid = read_results(None, tmp_path)
    assert not valid
