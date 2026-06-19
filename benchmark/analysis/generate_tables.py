from __future__ import annotations

import argparse
import json
from pathlib import Path

from benchmark.analysis.common import write_csv, write_markdown
from benchmark.analysis.failure_analysis import build_failure_breakdown
from benchmark.analysis.model_comparison import build_model_comparison
from benchmark.analysis.schema_complexity import build_schema_complexity


def generate_tables(db_path: str | Path, output_dir: str | Path, run_id: str | None = None) -> dict[str, str]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    table1 = build_model_comparison(db_path, run_id=run_id)
    table2 = build_failure_breakdown(db_path, run_id=run_id)
    table3 = build_schema_complexity(db_path, run_id=run_id)

    outputs = {
        "table1_csv": str(output / "table1_model_comparison.csv"),
        "table1_md": str(output / "table1_model_comparison.md"),
        "table2_csv": str(output / "table2_failure_breakdown.csv"),
        "table2_md": str(output / "table2_failure_breakdown.md"),
        "table3_csv": str(output / "table3_schema_complexity.csv"),
        "table3_md": str(output / "table3_schema_complexity.md"),
    }

    write_csv(outputs["table1_csv"], table1)
    write_markdown(outputs["table1_md"], table1, "Table 1 - Overall Success Rate by Model")
    write_csv(outputs["table2_csv"], table2)
    write_markdown(outputs["table2_md"], table2, "Table 2 - Failure Type Breakdown by Model")
    write_csv(outputs["table3_csv"], table3)
    write_markdown(outputs["table3_md"], table3, "Table 3 - Schema Complexity Effect")

    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate paper tables from a benchmark SQLite database.")
    parser.add_argument("--db", required=True, help="Benchmark SQLite database path.")
    parser.add_argument("--out", required=True, help="Output directory for CSV and Markdown tables.")
    parser.add_argument("--run-id", default=None, help="Optional run id filter.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    outputs = generate_tables(db_path=args.db, output_dir=args.out, run_id=args.run_id)
    print(json.dumps(outputs, indent=2))


if __name__ == "__main__":
    main()

