from app.core.failure_taxonomy import FailureType
from app.core.json_extractor import JsonExtractor


def test_extracts_direct_json() -> None:
    result = JsonExtractor().extract('{"title": "Valid object"}')

    assert result.data == {"title": "Valid object"}
    assert result.strategy == "direct_parse"
    assert result.failure_type is None


def test_extracts_wrapped_markdown_json() -> None:
    result = JsonExtractor().extract('Here you go:\n```json\n{"title": "Wrapped"}\n```')

    assert result.data == {"title": "Wrapped"}
    assert result.strategy == "markdown_code_block"
    assert result.failure_type == FailureType.WRAPPED_JSON


def test_detects_partial_json() -> None:
    result = JsonExtractor().extract('{"title": "Oops"')

    assert result.data is None
    assert result.failure_type == FailureType.PARTIAL_JSON

