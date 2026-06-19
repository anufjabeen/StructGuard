import json
import re
from dataclasses import dataclass
from typing import Any

from app.core.failure_taxonomy import FailureType


@dataclass(frozen=True)
class ExtractionResult:
    data: dict[str, Any] | None
    strategy: str
    failure_type: FailureType | None
    error: str | None = None


class JsonExtractor:
    _code_block_pattern = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)

    def extract(self, raw_text: str) -> ExtractionResult:
        stripped = raw_text.strip()
        direct = self._try_parse_object(stripped)
        if direct is not None:
            return ExtractionResult(data=direct, strategy="direct_parse", failure_type=None)

        code_block_match = self._code_block_pattern.search(stripped)
        if code_block_match:
            parsed = self._try_parse_object(code_block_match.group(1).strip())
            if parsed is not None:
                return ExtractionResult(
                    data=parsed,
                    strategy="markdown_code_block",
                    failure_type=FailureType.WRAPPED_JSON,
                )

        object_text = self._extract_first_balanced_object(stripped)
        if object_text:
            parsed = self._try_parse_object(object_text)
            if parsed is not None:
                return ExtractionResult(
                    data=parsed,
                    strategy="first_balanced_object",
                    failure_type=FailureType.WRAPPED_JSON,
                )
            return ExtractionResult(
                data=None,
                strategy="first_balanced_object",
                failure_type=FailureType.PARTIAL_JSON,
                error="Found an object-like span, but it was not parseable JSON.",
            )

        failure = FailureType.PARTIAL_JSON if self._looks_truncated(stripped) else FailureType.INVALID_JSON
        return ExtractionResult(
            data=None,
            strategy="none",
            failure_type=failure,
            error="No valid JSON object could be extracted.",
        )

    def _try_parse_object(self, text: str) -> dict[str, Any] | None:
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None

    def _extract_first_balanced_object(self, text: str) -> str | None:
        start = text.find("{")
        if start == -1:
            return None

        depth = 0
        in_string = False
        escape = False
        for index, char in enumerate(text[start:], start=start):
            if escape:
                escape = False
                continue
            if char == "\\" and in_string:
                escape = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start : index + 1]
        return text[start:] if depth > 0 else None

    def _looks_truncated(self, text: str) -> bool:
        return text.count("{") > text.count("}") or text.count("[") > text.count("]")

