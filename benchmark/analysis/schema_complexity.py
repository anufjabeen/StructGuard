from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from benchmark.analysis.common import connect, percent, rounded, rows_to_dicts

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCHEMA_DIR = ROOT / "backend" / "app" / "schemas"


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

