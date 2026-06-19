import json
import os

from app.core.schema_loader import SchemaLoader, clear_schema_cache


def test_schema_loader_reloads_when_file_mtime_changes(tmp_path) -> None:
    schema_path = tmp_path / "sample.json"
    schema_path.write_text(json.dumps(_schema("FirstTitle")), encoding="utf-8")
    loader = SchemaLoader(tmp_path)

    assert loader.load("sample")["title"] == "FirstTitle"

    schema_path.write_text(json.dumps(_schema("SecondTitle")), encoding="utf-8")
    next_mtime = schema_path.stat().st_mtime_ns + 1_000_000_000
    os.utime(schema_path, ns=(next_mtime, next_mtime))

    assert loader.load("sample")["title"] == "SecondTitle"

    clear_schema_cache()


def _schema(title: str) -> dict[str, object]:
    return {
        "$schema": "http://json-schema.org/draft-07/schema",
        "title": title,
        "type": "object",
        "properties": {
            "name": {"type": "string"},
        },
    }
