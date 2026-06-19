from __future__ import annotations

import csv
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any


@contextmanager
def connect(db_path: str | Path) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()


def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def write_csv(path: str | Path, rows: list[dict[str, Any]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        output_path.write_text("", encoding="utf-8")
        return

    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: str | Path, rows: list[dict[str, Any]], title: str) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        output_path.write_text(f"# {title}\n\nNo rows.\n", encoding="utf-8")
        return

    headers = list(rows[0].keys())
    lines = [f"# {title}", ""]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for row in rows:
        lines.append("| " + " | ".join(_format_cell(row.get(header)) for header in headers) + " |")
    lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")


def percent(value: float | int | None) -> str:
    if value is None:
        return "0.0%"
    return f"{float(value) * 100:.1f}%"


def rounded(value: float | int | None, digits: int = 2) -> float:
    if value is None:
        return 0.0
    return round(float(value), digits)


def _format_cell(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("|", "\\|").replace("\n", " ")
