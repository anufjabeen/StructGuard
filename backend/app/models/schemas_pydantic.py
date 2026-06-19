from typing import Any

from pydantic import BaseModel, Field

from app.core.failure_taxonomy import FailureType


class GenerateRequest(BaseModel):
    input_text: str = Field(min_length=1)
    schema_name: str = "incident_report"
    model: str = "ollama/llama3.1:8b"
    use_few_shots: bool = True
    max_attempts: int = Field(default=3, ge=1, le=5)
    expected: dict[str, Any] = Field(default_factory=dict)
    persist: bool = True
    run_id: str | None = None
    case_id: str | None = None


class BenchmarkRunRequest(BaseModel):
    schema_names: list[str] = Field(default_factory=lambda: ["incident_report"], min_length=1)
    models: list[str] = Field(default_factory=lambda: ["ollama/llama3.2:3b"], min_length=1)
    run_id: str | None = None
    use_few_shots: bool = True
    max_attempts: int = Field(default=3, ge=1, le=5)
    cases_by_schema: dict[str, str] = Field(default_factory=dict)


class BenchmarkJobResponse(BaseModel):
    run_id: str
    status: str
    schemas: list[str]
    models: list[str]
    total: int
    completed: int
    error: str | None = None


class RawAttempt(BaseModel):
    attempt: int
    raw: str
    extracted: dict[str, Any] | None
    repaired: dict[str, Any] | None
    extraction_strategy: str
    failure: FailureType | None
    fields: list[str] = Field(default_factory=list)
    repairs: list[str] = Field(default_factory=list)
    latency_ms: int
    error: str | None = None


class FailureSummary(BaseModel):
    attempt: int
    failure_type: FailureType
    fields: list[str] = Field(default_factory=list)
    message: str | None = None
    repairs: list[str] = Field(default_factory=list)
    extraction_strategy: str
    latency_ms: int


class GenerationResponse(BaseModel):
    result_id: int | None = None
    success: bool
    schema_name: str
    model: str
    attempts: int
    output: dict[str, Any] | None
    raw_attempts: list[RawAttempt]
    latency_ms: int
    failure_summary: FailureSummary | None = None
