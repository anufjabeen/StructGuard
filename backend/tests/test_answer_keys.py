import json
from pathlib import Path

from app.core.schema_loader import SchemaLoader
from benchmark.runner import load_cases


ANSWER_KEYS = {
    "incident_report": Path("benchmark/test_cases/answer_keys/incident_report_answers.json"),
    "bug_template": Path("benchmark/test_cases/answer_keys/bug_template_answers.json"),
    "change_request": Path("benchmark/test_cases/answer_keys/change_request_answers.json"),
}


def test_answer_keys_validate_against_schemas() -> None:
    schema_loader = SchemaLoader()

    for schema_name, answer_path in ANSWER_KEYS.items():
        validator = schema_loader.validator(schema_name)
        answers = json.loads(answer_path.read_text(encoding="utf-8"))

        assert len(answers) == 10
        for answer in answers:
            errors = sorted(
                validator.iter_errors(answer["expected_output"]),
                key=lambda error: list(error.absolute_path),
            )
            assert errors == []


def test_answer_keys_match_csv_case_ids() -> None:
    for schema_name, answer_path in ANSWER_KEYS.items():
        csv_path = Path(f"benchmark/test_cases/{schema_name}_cases.csv")
        csv_case_ids = {case.case_id for case in load_cases(csv_path)}
        answers = json.loads(answer_path.read_text(encoding="utf-8"))
        answer_case_ids = {answer["case_id"] for answer in answers}

        assert answer_case_ids == csv_case_ids
