from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any


DEFAULT_SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schemas"


@contextmanager
def connect(db_path: str | Path) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()


def build_model_comparison(db_path: str | Path, run_id: str | None = None) -> list[dict[str, Any]]:
    where = "WHERE gr.run_id = ?" if run_id else ""
    params: list[Any] = [run_id] if run_id else []

    with connect(db_path) as connection:
        rows = connection.execute(
            f"""
            WITH repairs AS (
                SELECT generation_id,
                       MAX(
                           CASE
                               WHEN repairs_json IS NOT NULL
                                    AND repairs_json != '[]'
                               THEN 1
                               ELSE 0
                           END
                       ) AS had_repair
                FROM failure_logs
                GROUP BY generation_id
            )
            SELECT gr.model,
                   COUNT(*) AS total,
                   SUM(gr.success) AS passed,
                   AVG(gr.attempts) AS avg_attempts,
                   AVG(gr.latency_ms) AS avg_latency_ms,
                   AVG(COALESCE(repairs.had_repair, 0)) AS repair_rate
            FROM generation_results gr
            LEFT JOIN repairs ON repairs.generation_id = gr.id
            {where}
            GROUP BY gr.model
            ORDER BY gr.model
            """,
            params,
        ).fetchall()

    table: list[dict[str, Any]] = []
    for row in rows_to_dicts(rows):
        total = row["total"] or 0
        passed = row["passed"] or 0
        table.append(
            {
                "model": row["model"],
                "total": total,
                "passed": passed,
                "pass_rate": percent((passed / total) if total else 0),
                "avg_attempts": rounded(row["avg_attempts"]),
                "repair_rate": percent(row["repair_rate"]),
                "avg_latency_ms": rounded(row["avg_latency_ms"]),
            }
        )
    return table


def build_failure_breakdown(db_path: str | Path, run_id: str | None = None) -> list[dict[str, Any]]:
    run_filter = "WHERE run_id = ?" if run_id else ""
    failure_filter = "WHERE fl.failure_type IS NOT NULL"
    total_params: list[Any] = [run_id] if run_id else []
    failure_params: list[Any] = []
    if run_id:
        failure_filter = "WHERE gr.run_id = ? AND fl.failure_type IS NOT NULL"
        failure_params.append(run_id)

    with connect(db_path) as connection:
        total_rows = connection.execute(
            f"""
            SELECT model, COUNT(*) AS total
            FROM generation_results
            {run_filter}
            GROUP BY model
            """,
            total_params,
        ).fetchall()
        failure_rows = connection.execute(
            f"""
            SELECT gr.model,
                   fl.failure_type,
                   COUNT(*) AS count
            FROM failure_logs fl
            JOIN generation_results gr ON gr.id = fl.generation_id
            {failure_filter}
            GROUP BY gr.model, fl.failure_type
            ORDER BY fl.failure_type, gr.model
            """,
            failure_params,
        ).fetchall()

    totals = {row["model"]: row["total"] for row in total_rows}
    table: list[dict[str, Any]] = []
    for row in rows_to_dicts(failure_rows):
        total = totals.get(row["model"], 0)
        table.append(
            {
                "failure_type": row["failure_type"],
                "model": row["model"],
                "count": row["count"],
                "rate_of_generations": percent((row["count"] / total) if total else 0),
            }
        )
    return table


def build_schema_complexity(
    db_path: str | Path,
    run_id: str | None = None,
    schema_dir: str | Path = DEFAULT_SCHEMA_DIR,
) -> list[dict[str, Any]]:
    complexities = _load_schema_complexities(Path(schema_dir))
    where = "WHERE run_id = ?" if run_id else ""
    params: list[Any] = [run_id] if run_id else []

    with connect(db_path) as connection:
        rows = connection.execute(
            f"""
            SELECT schema_name,
                   model,
                   COUNT(*) AS total,
                   SUM(success) AS passed,
                   AVG(attempts) AS avg_attempts
            FROM generation_results
            {where}
            GROUP BY schema_name, model
            ORDER BY schema_name, model
            """,
            params,
        ).fetchall()

    table: list[dict[str, Any]] = []
    for row in rows_to_dicts(rows):
        total = row["total"] or 0
        passed = row["passed"] or 0
        complexity = complexities.get(row["schema_name"], {})
        table.append(
            {
                "schema": row["schema_name"],
                "model": row["model"],
                "fields": complexity.get("fields", 0),
                "required": complexity.get("required", 0),
                "nested_objects": complexity.get("nested_objects", 0),
                "total": total,
                "pass_rate": percent((passed / total) if total else 0),
                "avg_attempts": rounded(row["avg_attempts"]),
            }
        )
    return table


def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def percent(value: float | int | None) -> str:
    if value is None:
        return "0.0%"
    return f"{float(value) * 100:.1f}%"


def rounded(value: float | int | None, digits: int = 2) -> float:
    if value is None:
        return 0.0
    return round(float(value), digits)


def _load_schema_complexities(schema_dir: Path) -> dict[str, dict[str, int]]:
    complexities: dict[str, dict[str, int]] = {}
    for schema_path in schema_dir.glob("*.json"):
        with schema_path.open("r", encoding="utf-8") as file:
            schema = json.load(file)
        complexities[schema_path.stem] = {
            "fields": len(schema.get("properties", {})),
            "required": len(schema.get("required", [])),
            "nested_objects": _count_nested_objects(schema),
        }
    return complexities


def _count_nested_objects(schema: dict[str, Any]) -> int:
    count = 0
    for field_schema in schema.get("properties", {}).values():
        if field_schema.get("type") == "object":
            count += 1 + _count_nested_objects(field_schema)
        if field_schema.get("type") == "array":
            item_schema = field_schema.get("items", {})
            if item_schema.get("type") == "object":
                count += 1 + _count_nested_objects(item_schema)
    return count
