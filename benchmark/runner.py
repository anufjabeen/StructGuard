from __future__ import annotations

import argparse
import asyncio
import csv
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.guardrails_engine import GuardrailsEngine
from app.db.crud import ResultStore


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    input_text: str
    expected: dict[str, Any]
    notes: str | None = None


def load_cases(path: str | Path) -> list[BenchmarkCase]:
    cases_path = Path(path)
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
        cases.append(
            BenchmarkCase(
                case_id=case_id,
                input_text=input_text,
                expected=expected,
                notes=(row.get("notes") or "").strip() or None,
            )
        )
    return cases


async def run_benchmark(
    *,
    schema_name: str,
    models: list[str],
    cases_path: str | Path,
    output_path: str | Path,
    run_id: str,
    max_attempts: int,
    use_few_shots: bool,
) -> dict[str, Any]:
    cases = load_cases(cases_path)
    engine = GuardrailsEngine()
    store = ResultStore(output_path)
    total = len(models) * len(cases)
    completed = 0
    saved_ids: list[int] = []

    for model in models:
        for case in cases:
            completed += 1
            print(f"[{completed}/{total}] {model} :: {case.case_id}", flush=True)
            result = await engine.generate(
                input_text=case.input_text,
                schema_name=schema_name,
                model=model,
                use_few_shots=use_few_shots,
                max_attempts=max_attempts,
                expected=case.expected,
            )
            result_id = store.save_generation(
                input_text=case.input_text,
                response=result,
                run_id=run_id,
                case_id=case.case_id,
            )
            saved_ids.append(result_id)

    summary = store.summarize(run_id=run_id)
    return {
        "run_id": run_id,
        "schema_name": schema_name,
        "models": models,
        "cases": len(cases),
        "total_generations": total,
        "saved_ids": saved_ids,
        "output_path": str(output_path),
        "summary": summary,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a structured-output benchmark.")
    parser.add_argument("--schema", default="incident_report", help="Schema name to evaluate.")
    parser.add_argument("--models", nargs="+", required=True, help="Model ids, e.g. mock/incident-json ollama/llama3.1:8b.")
    parser.add_argument("--cases", required=True, help="CSV test case path.")
    parser.add_argument("--output", default="benchmark/results/run.db", help="SQLite output database path.")
    parser.add_argument("--run-id", default=None, help="Run id. Defaults to a UTC timestamp.")
    parser.add_argument("--max-attempts", default=3, type=int, help="Maximum attempts per generation.")
    parser.add_argument("--no-few-shots", action="store_true", help="Disable few-shot examples.")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    run_id = args.run_id or datetime.now(UTC).strftime("run_%Y%m%d_%H%M%S")
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary = await run_benchmark(
        schema_name=args.schema,
        models=args.models,
        cases_path=args.cases,
        output_path=output_path,
        run_id=run_id,
        max_attempts=args.max_attempts,
        use_few_shots=not args.no_few_shots,
    )
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())

