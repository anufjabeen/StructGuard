import pytest

from benchmark.analysis.failure_analysis import build_failure_breakdown
from benchmark.analysis.generate_tables import generate_tables
from benchmark.analysis.model_comparison import build_model_comparison
from benchmark.analysis.schema_complexity import build_schema_complexity
from benchmark.runner import run_benchmark


@pytest.mark.asyncio
async def test_analysis_tables_from_benchmark_run(tmp_path) -> None:
    db_path = tmp_path / "analysis.db"
    await run_benchmark(
        schema_name="incident_report",
        models=["mock/incident-json", "mock/wrapped-json"],
        cases_path="benchmark/test_cases/incident_report_cases.csv",
        output_path=db_path,
        run_id="analysis_test",
        max_attempts=1,
        use_few_shots=True,
    )

    table1 = build_model_comparison(db_path, run_id="analysis_test")
    table2 = build_failure_breakdown(db_path, run_id="analysis_test")
    table3 = build_schema_complexity(db_path, run_id="analysis_test")
    outputs = generate_tables(db_path, tmp_path / "tables", run_id="analysis_test")

    assert {row["model"] for row in table1} == {"mock/incident-json", "mock/wrapped-json"}
    assert any(row["failure_type"] == "WRAPPED_JSON" for row in table2)
    assert table3[0]["schema"] == "incident_report"
    assert (tmp_path / "tables" / "table1_model_comparison.csv").exists()
    assert outputs["table3_md"].endswith("table3_schema_complexity.md")
