import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator, FormatChecker


class SchemaNotFoundError(ValueError):
    pass


class SchemaLoader:
    def __init__(self, schema_dir: Path | None = None) -> None:
        self.schema_dir = schema_dir or Path(__file__).resolve().parents[1] / "schemas"

    def list_schemas(self) -> list[str]:
        return sorted(path.stem for path in self.schema_dir.glob("*.json"))

    def load(self, schema_name: str) -> dict[str, Any]:
        if not schema_name.replace("_", "").isalnum():
            raise SchemaNotFoundError(f"Invalid schema name: {schema_name}")

        schema_path = (self.schema_dir / f"{schema_name}.json").resolve()
        if self.schema_dir.resolve() not in schema_path.parents or not schema_path.exists():
            raise SchemaNotFoundError(f"Unknown schema: {schema_name}")

        return _load_schema(schema_path, schema_path.stat().st_mtime_ns)

    def validator(self, schema_name: str) -> Draft7Validator:
        return self.validator_from_schema(self.load(schema_name))

    def validator_from_schema(self, schema: dict[str, Any]) -> Draft7Validator:
        return Draft7Validator(schema, format_checker=FormatChecker())


def clear_schema_cache() -> None:
    _load_schema.cache_clear()


@lru_cache(maxsize=32)
def _load_schema(schema_path: Path, mtime_ns: int) -> dict[str, Any]:
    with schema_path.open("r", encoding="utf-8") as file:
        schema = json.load(file)
    Draft7Validator.check_schema(schema)
    return schema
