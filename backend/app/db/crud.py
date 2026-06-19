from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.db.database import SQLiteDatabase
from app.models.schemas_pydantic import GenerationResponse, RawAttempt


class ResultStore:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.database = SQLiteDatabase(db_path)
        self.database.initialize()

    def save_generation(
        self,
        *,
        input_text: str,
        response: GenerationResponse,
        run_id: str | None = None,
        case_id: str | None = None,
    ) -> int:
        with self.database.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO generation_results (
                    run_id,
                    case_id,
                    input_text,
                    schema_name,
                    model,
                    success,
                    attempts,
                    latency_ms,
                    output_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    case_id,
                    input_text,
                    response.schema_name,
                    response.model,
                    int(response.success),
                    response.attempts,
                    response.latency_ms,
                    self._json(response.output),
                ),
            )
            generation_id = int(cursor.lastrowid)

            for attempt in response.raw_attempts:
                self._save_attempt(connection, generation_id, attempt)

            return generation_id

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT run_id,
                       MIN(created_at) AS started_at,
                       MAX(created_at) AS last_result_at,
                       COUNT(*) AS total,
                       SUM(success) AS passed,
                       COUNT(DISTINCT model) AS model_count,
                       COUNT(DISTINCT schema_name) AS schema_count,
                       GROUP_CONCAT(DISTINCT model) AS models_csv,
                       GROUP_CONCAT(DISTINCT schema_name) AS schemas_csv
                FROM generation_results
                WHERE run_id = ?
                GROUP BY run_id
                """,
                (run_id,),
            ).fetchone()
        if row is None:
            return None

        payload = self._row_to_dict(row)
        total = payload["total"] or 0
        passed = payload["passed"] or 0
        payload["pass_rate"] = (passed / total) if total else 0
        payload["models"] = self._split_csv(payload.pop("models_csv"))
        payload["schemas"] = self._split_csv(payload.pop("schemas_csv"))
        return payload

    def list_results(self, run_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 500))
        sql = """
            SELECT id, created_at, run_id, case_id, input_text, schema_name, model,
                   success, attempts, latency_ms,
                   (
                       SELECT fl.failure_type
                       FROM failure_logs fl
                       WHERE fl.generation_id = generation_results.id
                         AND fl.failure_type IS NOT NULL
                       ORDER BY fl.attempt DESC
                       LIMIT 1
                   ) AS failure_type,
                   (
                       SELECT fl.error
                       FROM failure_logs fl
                       WHERE fl.generation_id = generation_results.id
                         AND fl.failure_type IS NOT NULL
                       ORDER BY fl.attempt DESC
                       LIMIT 1
                   ) AS failure_message,
                   (
                       SELECT fl.fields_json
                       FROM failure_logs fl
                       WHERE fl.generation_id = generation_results.id
                         AND fl.failure_type IS NOT NULL
                       ORDER BY fl.attempt DESC
                       LIMIT 1
                   ) AS failure_fields_json
            FROM generation_results
        """
        params: list[Any] = []
        if run_id:
            sql += " WHERE run_id = ?"
            params.append(run_id)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        with self.database.connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [self._result_summary_row_to_dict(row) for row in rows]

    def list_runs(self, limit: int = 100) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 500))
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT run_id,
                       MIN(created_at) AS started_at,
                       MAX(created_at) AS last_result_at,
                       COUNT(*) AS total,
                       SUM(success) AS passed,
                       COUNT(DISTINCT model) AS model_count,
                       COUNT(DISTINCT schema_name) AS schema_count
                FROM generation_results
                WHERE run_id IS NOT NULL
                GROUP BY run_id
                ORDER BY last_result_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        runs = []
        for row in rows:
            payload = self._row_to_dict(row)
            total = payload["total"] or 0
            passed = payload["passed"] or 0
            payload["pass_rate"] = (passed / total) if total else 0
            runs.append(payload)
        return runs

    def get_result(self, result_id: int) -> dict[str, Any] | None:
        with self.database.connect() as connection:
            result = connection.execute(
                "SELECT * FROM generation_results WHERE id = ?",
                (result_id,),
            ).fetchone()
            if result is None:
                return None
            attempts = connection.execute(
                "SELECT * FROM failure_logs WHERE generation_id = ? ORDER BY attempt",
                (result_id,),
            ).fetchall()

        payload = self._row_to_dict(result)
        payload["output"] = self._loads(payload.pop("output_json"))
        payload["raw_attempts"] = [self._attempt_row_to_dict(row) for row in attempts]
        return payload

    def summarize(self, run_id: str | None = None) -> dict[str, Any]:
        where = "WHERE run_id = ?" if run_id else ""
        params: list[Any] = [run_id] if run_id else []
        failure_where = "WHERE fl.failure_type IS NOT NULL"
        failure_params: list[Any] = []
        if run_id:
            failure_where = "WHERE gr.run_id = ? AND fl.failure_type IS NOT NULL"
            failure_params.append(run_id)

        with self.database.connect() as connection:
            by_model = connection.execute(
                f"""
                SELECT model,
                       COUNT(*) AS total,
                       SUM(success) AS passed,
                       AVG(attempts) AS avg_attempts,
                       AVG(latency_ms) AS avg_latency_ms
                FROM generation_results
                {where}
                GROUP BY model
                ORDER BY model
                """,
                params,
            ).fetchall()

            failure_breakdown = connection.execute(
                f"""
                SELECT gr.model,
                       fl.failure_type,
                       COUNT(*) AS count
                FROM failure_logs fl
                JOIN generation_results gr ON gr.id = fl.generation_id
                {failure_where}
                GROUP BY gr.model, fl.failure_type
                ORDER BY gr.model, fl.failure_type
                """,
                failure_params,
            ).fetchall()

        return {
            "run_id": run_id,
            "by_model": [
                {
                    "model": row["model"],
                    "total": row["total"],
                    "passed": row["passed"] or 0,
                    "pass_rate": ((row["passed"] or 0) / row["total"]) if row["total"] else 0,
                    "avg_attempts": row["avg_attempts"],
                    "avg_latency_ms": row["avg_latency_ms"],
                }
                for row in by_model
            ],
            "failure_breakdown": [self._row_to_dict(row) for row in failure_breakdown],
        }

    def _save_attempt(self, connection: Any, generation_id: int, attempt: RawAttempt) -> None:
        failure_type = attempt.failure.value if attempt.failure else None
        connection.execute(
            """
            INSERT INTO failure_logs (
                generation_id,
                attempt,
                failure_type,
                fields_json,
                repairs_json,
                extraction_strategy,
                latency_ms,
                error,
                raw_output,
                extracted_json,
                repaired_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                generation_id,
                attempt.attempt,
                failure_type,
                self._json_list(attempt.fields),
                self._json_list(attempt.repairs),
                attempt.extraction_strategy,
                attempt.latency_ms,
                attempt.error,
                attempt.raw,
                self._json(attempt.extracted),
                self._json(attempt.repaired),
            ),
        )

    def _attempt_row_to_dict(self, row: Any) -> dict[str, Any]:
        payload = self._row_to_dict(row)
        payload["fields"] = self._loads(payload.pop("fields_json")) or []
        payload["repairs"] = self._loads(payload.pop("repairs_json")) or []
        payload["extracted"] = self._loads(payload.pop("extracted_json"))
        payload["repaired"] = self._loads(payload.pop("repaired_json"))
        return payload

    def _result_summary_row_to_dict(self, row: Any) -> dict[str, Any]:
        payload = self._row_to_dict(row)
        payload["failure_fields"] = self._loads(payload.pop("failure_fields_json")) or []
        return payload

    def _json_list(self, value: list[Any] | None) -> str:
        return self._json(value or []) or "[]"

    def _json(self, value: Any) -> str | None:
        if value is None:
            return None
        return json.dumps(value, sort_keys=True, default=str)

    def _loads(self, value: str | None) -> Any:
        if value is None:
            return None
        return json.loads(value)

    def _row_to_dict(self, row: Any) -> dict[str, Any]:
        payload = dict(row)
        if "success" in payload:
            payload["success"] = bool(payload["success"])
        return payload

    def _split_csv(self, value: str | None) -> list[str]:
        if not value:
            return []
        return [item for item in value.split(",") if item]
