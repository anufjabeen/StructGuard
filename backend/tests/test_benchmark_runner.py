from pathlib import Path

from benchmark.runner import load_cases


def test_load_cases_maps_expected_columns() -> None:
    cases = load_cases(Path("benchmark/test_cases/incident_report_cases.csv"))

    assert cases[0].case_id == "incident_001"
    assert cases[0].expected == {
        "severity": "critical",
        "affected_service": "checkout",
        "status": "investigating",
        "affected_users": "500",
    }


def test_load_cases_for_all_seed_schemas() -> None:
    assert len(load_cases(Path("benchmark/test_cases/incident_report_cases.csv"))) == 10
    assert len(load_cases(Path("benchmark/test_cases/bug_template_cases.csv"))) == 10
    assert len(load_cases(Path("benchmark/test_cases/change_request_cases.csv"))) == 10
