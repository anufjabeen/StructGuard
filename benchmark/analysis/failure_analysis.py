from __future__ import annotations

from pathlib import Path
from typing import Any

from benchmark.analysis.common import connect, percent, rows_to_dicts


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
        rate = (row["count"] / total) if total else 0
        table.append(
            {
                "failure_type": row["failure_type"],
                "model": row["model"],
                "count": row["count"],
                "rate_of_generations": percent(rate),
            }
        )
    return table

