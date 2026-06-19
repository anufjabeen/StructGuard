import pytest

from app.core.failure_taxonomy import FailureType
from app.core.guardrails_engine import GuardrailsEngine


class TriagedIncidentRouter:
    async def generate(self, prompt: str, model: str, max_tokens: int = 1000) -> str:
        return """{
  "title": "Inventory page shows negative stock",
  "severity": "high",
  "affected_service": "inventory",
  "reported_at": "2026-06-16T14:10:00Z",
  "affected_users": 0,
  "description": "Inventory page shows negative stock values in production.",
  "status": "triaged"
}"""


class InvalidIncidentStatusRouter:
    async def generate(self, prompt: str, model: str, max_tokens: int = 1000) -> str:
        return """{
  "title": "Inventory page shows negative stock",
  "severity": "high",
  "affected_service": "inventory",
  "reported_at": "2026-06-16T14:10:00Z",
  "description": "Inventory page shows negative stock values in production.",
  "status": "blocked"
}"""


@pytest.mark.asyncio
async def test_engine_accepts_mock_json() -> None:
    result = await GuardrailsEngine().generate(
        input_text="Checkout down for 500 users.",
        schema_name="incident_report",
        model="mock/incident-json",
    )

    assert result.success is True
    assert result.output is not None
    assert result.output["severity"] == "critical"


@pytest.mark.asyncio
async def test_engine_repairs_common_enum_and_date_issues() -> None:
    result = await GuardrailsEngine().generate(
        input_text="Checkout down for 500 users.",
        schema_name="incident_report",
        model="mock/bad-enum",
    )

    assert result.success is True
    assert result.output is not None
    assert result.output["affected_users"] == 500
    assert "DATE_NORMALIZED:reported_at" in result.raw_attempts[0].repairs


@pytest.mark.asyncio
async def test_engine_repairs_cross_schema_status_alias() -> None:
    result = await GuardrailsEngine(llm_router=TriagedIncidentRouter()).generate(
        input_text="Production inventory page shows negative stock values. Status triaged.",
        schema_name="incident_report",
        model="test/router",
        max_attempts=1,
    )

    assert result.success is True
    assert result.output is not None
    assert result.output["status"] == "investigating"
    assert "REPAIRED_ENUM:status" in result.raw_attempts[0].repairs


@pytest.mark.asyncio
async def test_engine_returns_failure_summary_for_failed_generation() -> None:
    result = await GuardrailsEngine(llm_router=InvalidIncidentStatusRouter()).generate(
        input_text="Production inventory page shows negative stock values. Status blocked.",
        schema_name="incident_report",
        model="test/router",
        max_attempts=1,
    )

    assert result.success is False
    assert result.failure_summary is not None
    assert result.failure_summary.failure_type == FailureType.INVALID_ENUM
    assert result.failure_summary.fields == ["status"]
    assert result.failure_summary.message is not None
    assert "is not one of" in result.failure_summary.message


@pytest.mark.asyncio
async def test_engine_logs_wrapped_json() -> None:
    result = await GuardrailsEngine().generate(
        input_text="Checkout down for 500 users.",
        schema_name="incident_report",
        model="mock/wrapped-json",
    )

    assert result.success is True
    assert result.raw_attempts[0].failure == FailureType.WRAPPED_JSON


@pytest.mark.asyncio
@pytest.mark.parametrize("schema_name", ["incident_report", "bug_template", "change_request"])
async def test_schema_aware_mock_supports_all_schemas(schema_name: str) -> None:
    result = await GuardrailsEngine().generate(
        input_text="Create a structured record from this operational note.",
        schema_name=schema_name,
        model="mock/incident-json",
    )

    assert result.success is True
    assert result.output is not None
