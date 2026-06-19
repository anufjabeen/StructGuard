import pytest

from app.core.failure_taxonomy import FailureType
from app.core.guardrails_engine import GuardrailsEngine
from app.db.crud import ResultStore
from app.models.schemas_pydantic import GenerationResponse, RawAttempt


@pytest.mark.asyncio
async def test_result_store_saves_generation(tmp_path) -> None:
    result = await GuardrailsEngine().generate(
        input_text="Checkout down for 500 users.",
        schema_name="incident_report",
        model="mock/wrapped-json",
    )
    store = ResultStore(tmp_path / "results.db")

    result_id = store.save_generation(
        input_text="Checkout down for 500 users.",
        response=result,
        run_id="test_run",
        case_id="case_001",
    )
    saved = store.get_result(result_id)
    summary = store.summarize(run_id="test_run")

    assert saved is not None
    assert saved["success"] is True
    assert saved["raw_attempts"][0]["failure_type"] == "WRAPPED_JSON"
    assert summary["by_model"][0]["model"] == "mock/wrapped-json"
    assert summary["by_model"][0]["passed"] == 1


@pytest.mark.asyncio
async def test_result_store_lists_runs(tmp_path) -> None:
    result = await GuardrailsEngine().generate(
        input_text="Checkout down for 500 users.",
        schema_name="incident_report",
        model="mock/incident-json",
    )
    store = ResultStore(tmp_path / "results.db")
    store.save_generation(input_text="one", response=result, run_id="run_a", case_id="case_a")
    store.save_generation(input_text="two", response=result, run_id="run_b", case_id="case_b")

    runs = store.list_runs()

    assert {run["run_id"] for run in runs} == {"run_a", "run_b"}


def test_result_store_lists_latest_failure_details(tmp_path) -> None:
    result = GenerationResponse(
        success=False,
        schema_name="incident_report",
        model="test/model",
        attempts=1,
        output=None,
        raw_attempts=[
            RawAttempt(
                attempt=1,
                raw='{"status": "blocked"}',
                extracted={"status": "blocked"},
                repaired={"status": "blocked"},
                extraction_strategy="direct_parse",
                failure=FailureType.INVALID_ENUM,
                fields=["status"],
                repairs=[],
                latency_ms=12,
                error="'blocked' is not one of ['open', 'investigating', 'resolved']",
            )
        ],
        latency_ms=12,
    )
    store = ResultStore(tmp_path / "results.db")
    store.save_generation(input_text="bad status", response=result, run_id="run_failed", case_id="case_failed")

    listed = store.list_results(run_id="run_failed")

    assert listed[0]["failure_type"] == "INVALID_ENUM"
    assert listed[0]["failure_fields"] == ["status"]
    assert "blocked" in listed[0]["failure_message"]
