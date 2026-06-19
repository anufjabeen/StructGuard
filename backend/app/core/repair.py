from __future__ import annotations

from copy import deepcopy
from datetime import timezone
import re
from typing import Any

from dateutil import parser as date_parser
from rapidfuzz import fuzz, process


class JsonRepairer:
    _iso_like_date_pattern = re.compile(
        r"\b\d{4}[-/]\d{1,2}(?:[-/]\d{1,2})?\b|\b\d{1,2}[-/]\d{1,2}[-/]\d{4}\b"
    )
    _month_name_date_pattern = re.compile(
        r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\b.*\b\d{4}\b|"
        r"\b\d{4}\b.*\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\b",
        re.IGNORECASE,
    )

    enum_aliases = {
        "severity": {
            "urgent": "high",
            "p0": "critical",
            "p1": "critical",
            "sev1": "critical",
            "sev2": "high",
            "p2": "high",
            "p3": "medium",
            "p4": "low",
        },
        "risk_level": {
            "urgent": "high",
            "p0": "critical",
            "p1": "critical",
            "p2": "high",
            "p3": "medium",
            "p4": "low",
        },
        "status": {
            "opened": "open",
            "pending": "open",
            "triage": "investigating",
            "triaged": "investigating",
            "investigate": "investigating",
            "in progress": "investigating",
            "in-progress": "investigating",
            "complete": "resolved",
            "completed": "resolved",
            "closed": "resolved",
            "fixed": "resolved",
        },
    }

    def repair(self, data: dict[str, Any], schema: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
        repaired = deepcopy(data)
        repairs: list[str] = []
        self._repair_object(repaired, schema, repairs, path="")
        return repaired, repairs

    def _repair_object(self, data: dict[str, Any], schema: dict[str, Any], repairs: list[str], path: str) -> None:
        properties = schema.get("properties", {})
        for field, field_schema in properties.items():
            if field not in data:
                continue

            current_path = f"{path}.{field}" if path else field
            value = data[field]
            field_type = field_schema.get("type")

            if field_type == "object" and isinstance(value, dict):
                self._repair_object(value, field_schema, repairs, current_path)
                continue

            if field_type == "array" and isinstance(value, list):
                item_schema = field_schema.get("items", {})
                if item_schema.get("type") == "string":
                    data[field] = [str(item) for item in value]
                continue

            enum_values = field_schema.get("enum")
            if enum_values and isinstance(value, str):
                normalized = value.strip().lower()
                enum_alias = self.enum_aliases.get(field, {}).get(normalized)
                if enum_alias in enum_values:
                    data[field] = enum_alias
                    repairs.append(f"REPAIRED_ENUM:{current_path}")
                    continue

                if normalized in enum_values:
                    if normalized != value:
                        data[field] = normalized
                        repairs.append(f"CASE_NORMALIZED:{current_path}")
                    continue

                match = self._safe_enum_match(normalized, enum_values)
                if match is not None:
                    data[field] = match[0]
                    repairs.append(f"REPAIRED_ENUM:{current_path}")
                    continue

            if field_type == "integer" and isinstance(value, str):
                parsed = self._parse_integer(value)
                if parsed is not None:
                    data[field] = parsed
                    repairs.append(f"STRING_TO_INTEGER:{current_path}")
                    continue

            if field_schema.get("format") == "date-time" and isinstance(value, str):
                parsed_datetime = self._parse_datetime(value)
                if parsed_datetime:
                    data[field] = parsed_datetime
                    if parsed_datetime != value:
                        repairs.append(f"DATE_NORMALIZED:{current_path}")

    def _parse_integer(self, value: str) -> int | None:
        cleaned = value.strip().replace(",", "")
        if cleaned.isdigit() or (cleaned.startswith("-") and cleaned[1:].isdigit()):
            return int(cleaned)
        word_numbers = {
            "zero": 0,
            "one": 1,
            "two": 2,
            "three": 3,
            "four": 4,
            "five": 5,
            "ten": 10,
            "hundred": 100,
        }
        return word_numbers.get(cleaned.lower())

    def _parse_datetime(self, value: str) -> str | None:
        if not self._looks_like_date(value):
            return None
        try:
            parsed = date_parser.parse(value)
        except (ValueError, OverflowError, TypeError):
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    def _safe_enum_match(self, normalized: str, enum_values: list[str]) -> tuple[str, float, int] | None:
        if len(normalized) < 4:
            return None
        return process.extractOne(normalized, enum_values, scorer=fuzz.ratio, score_cutoff=90)

    def _looks_like_date(self, value: str) -> bool:
        return bool(self._iso_like_date_pattern.search(value) or self._month_name_date_pattern.search(value))
