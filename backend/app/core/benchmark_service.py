from __future__ import annotations

import asyncio
import csv
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.guardrails_engine import GuardrailsEngine
from app.db.crud import ResultStore
from app.models.schemas_pydantic import BenchmarkJobResponse, BenchmarkRunRequest

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CASE_DIR = ROOT / "benchmark" / "test_cases"


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    input_text: str
    expected: dict[str, Any]


def default_cases_path(schema_name: str) -> Path:
    return DEFAULT_CASE_DIR / f"{schema_name}_cases.csv"


def load_cases(path: str | Path) -> list[BenchmarkCase]:
    cases_path = Path(path)
    if not cases_path.is_absolute():
        cases_path = ROOT / cases_path

    with cases_path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    cases: list[BenchmarkCase] = []
    for index, row in enumerate(rows, start=1):
        input_text = (row.get("input_text") or "").strip()
        if not input_text:
            continue
        case_id = (row.get("case_id") or f"{cases_path.stem}_{index:03d}").strip()
        expected = {
            key.removeprefix("expected_"): value.strip()
            for key, value in row.items()
            if key.startswith("expected_") and value and value.strip()
        }
        cases.append(BenchmarkCase(case_id=case_id, input_text=input_text, expected=expected))
    return cases


class BenchmarkJobRegistry:
    def __init__(self, store: ResultStore | None = None, engine: GuardrailsEngine | None = None) -> None:
        self.store = store or ResultStore()
        self.engine = engine or GuardrailsEngine()
        self.jobs: dict[str, BenchmarkJobResponse] = {}

    async def start(self, request: BenchmarkRunRequest) -> BenchmarkJobResponse:
        run_id = request.run_id or datetime.now(UTC).strftime("api_run_%Y%m%d_%H%M%S")
        case_counts = {
            schema_name: len(load_cases(request.cases_by_schema.get(schema_name) or default_cases_path(schema_name)))
            for schema_name in request.schema_names
        }
        total = sum(case_counts.values()) * len(request.models)
        job = BenchmarkJobResponse(
            run_id=run_id,
            status="queued",
            schemas=request.schema_names,
            models=request.models,
            total=total,
            completed=0,
        )
        self.jobs[run_id] = job
        asyncio.get_running_loop().create_task(self._run(run_id=run_id, request=request))
        return job

    def list(self) -> list[BenchmarkJobResponse]:
        return sorted(self.jobs.values(), key=lambda job: job.run_id, reverse=True)

    def get(self, run_id: str) -> BenchmarkJobResponse | None:
        job = self.jobs.get(run_id)
        if job is not None:
            return job

        stored_run = self.store.get_run(run_id)
        if stored_run is None:
            return None
        total = int(stored_run["total"] or 0)
        return BenchmarkJobResponse(
            run_id=run_id,
            status="completed",
            schemas=stored_run["schemas"],
            models=stored_run["models"],
            total=total,
            completed=total,
        )

    async def _run(self, run_id: str, request: BenchmarkRunRequest) -> None:
        self._update(run_id, status="running")
        try:
            for schema_name in request.schema_names:
                cases_path = request.cases_by_schema.get(schema_name) or default_cases_path(schema_name)
                cases = load_cases(cases_path)
                for model in request.models:
                    for case in cases:
                        result = await self.engine.generate(
                            input_text=case.input_text,
                            schema_name=schema_name,
                            model=model,
                            use_few_shots=request.use_few_shots,
                            max_attempts=request.max_attempts,
                            expected=case.expected,
                        )
                        self.store.save_generation(
                            input_text=case.input_text,
                            response=result,
                            run_id=run_id,
                            case_id=case.case_id,
                        )
                        self._increment(run_id)
            self._update(run_id, status="completed")
        except Exception as exc:
            self._update(run_id, status="failed", error=str(exc))

    def _increment(self, run_id: str) -> None:
        job = self.jobs[run_id]
        self.jobs[run_id] = job.model_copy(update={"completed": job.completed + 1})

    def _update(self, run_id: str, **updates: Any) -> None:
        job = self.jobs[run_id]
        self.jobs[run_id] = job.model_copy(update=updates)
