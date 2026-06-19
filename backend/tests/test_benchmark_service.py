from app.core.benchmark_service import BenchmarkJobRegistry, default_cases_path, load_cases
from app.db.crud import ResultStore
from app.models.schemas_pydantic import GenerationResponse


def test_backend_benchmark_service_loads_default_cases() -> None:
    cases = load_cases(default_cases_path("change_request"))

    assert cases[0].case_id == "change_001"
    assert cases[0].expected["change_type"] == "normal"


def test_benchmark_registry_get_falls_back_to_stored_run(tmp_path) -> None:
    store = ResultStore(tmp_path / "results.db")
    result = GenerationResponse(
        success=True,
        schema_name="incident_report",
        model="mock/incident-json",
        attempts=1,
        output={"title": "Stored run"},
        raw_attempts=[],
        latency_ms=10,
    )
    store.save_generation(input_text="stored", response=result, run_id="stored_run", case_id="case_001")
    registry = BenchmarkJobRegistry(store=store)

    job = registry.get("stored_run")

    assert job is not None
    assert job.status == "completed"
    assert job.completed == 1
    assert job.schemas == ["incident_report"]
    assert job.models == ["mock/incident-json"]
