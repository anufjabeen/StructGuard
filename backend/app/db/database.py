from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
import os
import sqlite3
from pathlib import Path


def default_db_path() -> Path:
    configured = os.getenv("RESULTS_DB_PATH")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[2] / "data" / "results.db"


class SQLiteDatabase:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path else default_db_path()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS generation_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    run_id TEXT,
                    case_id TEXT,
                    input_text TEXT NOT NULL,
                    schema_name TEXT NOT NULL,
                    model TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    attempts INTEGER NOT NULL,
                    latency_ms INTEGER NOT NULL,
                    output_json TEXT
                );

                CREATE TABLE IF NOT EXISTS failure_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    generation_id INTEGER NOT NULL,
                    attempt INTEGER NOT NULL,
                    failure_type TEXT,
                    fields_json TEXT NOT NULL,
                    repairs_json TEXT NOT NULL,
                    extraction_strategy TEXT NOT NULL,
                    latency_ms INTEGER NOT NULL,
                    error TEXT,
                    raw_output TEXT NOT NULL,
                    extracted_json TEXT,
                    repaired_json TEXT,
                    FOREIGN KEY (generation_id)
                        REFERENCES generation_results(id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_generation_results_run_id
                    ON generation_results(run_id);

                CREATE INDEX IF NOT EXISTS idx_generation_results_model
                    ON generation_results(model);

                CREATE INDEX IF NOT EXISTS idx_failure_logs_generation_id
                    ON failure_logs(generation_id);
                """
            )
