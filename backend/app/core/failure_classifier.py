from __future__ import annotations

from typing import Any

from jsonschema import ValidationError
from rapidfuzz import fuzz

from app.core.failure_taxonomy import FailureType


class FailureClassifier:
    def classify_schema_error(self, error: ValidationError) -> tuple[FailureType, list[str]]:
        path = [str(part) for part in error.absolute_path]
        fields = [".".join(path)] if path else []

        if error.validator == "required":
            missing = self._extract_missing_required_field(error.message)
            return FailureType.MISSING_REQUIRED_FIELD, [missing] if missing else fields
        if error.validator == "type":
            return FailureType.WRONG_TYPE, fields
        if error.validator == "enum":
            return FailureType.INVALID_ENUM, fields
        if error.validator in {"format", "minLength", "maxLength", "minimum", "maximum", "pattern"}:
            return FailureType.FORMAT_VIOLATION, fields
        if error.validator == "additionalProperties":
            return FailureType.SCOPE_CREEP, fields
        return FailureType.UNKNOWN, fields

    def semantic_failures(
        self,
        output: dict[str, Any],
        expected: dict[str, Any] | None,
        threshold: int = 85,
    ) -> list[tuple[FailureType, str, str]]:
        if not expected:
            return []

        failures: list[tuple[FailureType, str, str]] = []
        for field, expected_value in expected.items():
            if expected_value is None or field not in output:
                continue
            actual_value = output[field]
            if self._matches(expected_value, actual_value, threshold):
                continue

            failure_type = FailureType.FIELD_CONFUSION if self._expected_found_elsewhere(output, field, expected_value) else FailureType.HALLUCINATED_VALUE
            failures.append((failure_type, field, f"expected={expected_value!r}; actual={actual_value!r}"))
        return failures

    def _matches(self, expected: Any, actual: Any, threshold: int) -> bool:
        if expected == actual:
            return True
        if isinstance(expected, str) and isinstance(actual, str):
            return fuzz.token_set_ratio(expected.lower(), actual.lower()) >= threshold
        if isinstance(expected, str) and isinstance(actual, (int, float, bool)):
            return expected.strip().lower() == str(actual).lower()
        if isinstance(actual, str) and isinstance(expected, (int, float, bool)):
            return actual.strip().lower() == str(expected).lower()
        return False

    def _expected_found_elsewhere(self, output: dict[str, Any], expected_field: str, expected_value: Any) -> bool:
        if not isinstance(expected_value, str):
            return False
        needle = expected_value.lower()
        for field, value in output.items():
            if field == expected_field or not isinstance(value, str):
                continue
            if fuzz.token_set_ratio(needle, value.lower()) >= 85:
                return True
        return False

    def _extract_missing_required_field(self, message: str) -> str | None:
        marker = "' is a required property"
        if marker not in message:
            return None
        return message.split(marker, 1)[0].strip("'")
