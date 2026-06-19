from __future__ import annotations

from pathlib import Path
from typing import Any

from benchmark.analysis.common import connect, percent, rounded, rows_to_dicts


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
        pass_rate = (passed / total) if total else 0
        table.append(
            {
                "model": row["model"],
                "total": total,
                "passed": passed,
                "pass_rate": percent(pass_rate),
                "avg_attempts": rounded(row["avg_attempts"]),
                "repair_rate": percent(row["repair_rate"]),
                "avg_latency_ms": rounded(row["avg_latency_ms"]),
            }
        )
    return table

