import json
from pathlib import Path
from typing import Any


class PromptBuilder:
    def __init__(self, few_shot_dir: Path | None = None) -> None:
        self.few_shot_dir = few_shot_dir or Path(__file__).resolve().parents[1] / "few_shots"

    def build(
        self,
        input_text: str,
        schema_name: str,
        schema: dict[str, Any],
        use_few_shots: bool = True,
        corrective_context: str | None = None,
    ) -> str:
        parts = [
            "Extract information from the source text and return one JSON object.",
            "Return ONLY the JSON object. Do not use markdown, prose, comments, or trailing text.",
            "The JSON must match this JSON Schema exactly.",
            json.dumps(schema, indent=2),
        ]

        if use_few_shots:
            examples = self._load_examples(schema_name)
            if examples:
                parts.append("Examples:")
                for example in examples:
                    parts.append(f"Input: {example['input_text']}")
                    parts.append("Output:")
                    parts.append(json.dumps(example["output"], indent=2))

        if corrective_context:
            parts.extend(
                [
                    "Your previous response failed validation.",
                    corrective_context,
                    "Try again with a corrected JSON object only.",
                ]
            )

        parts.append("Source text:")
        parts.append(input_text)
        return "\n\n".join(parts)

    def _load_examples(self, schema_name: str) -> list[dict[str, Any]]:
        path = self.few_shot_dir / f"{schema_name}_examples.json"
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8") as file:
            loaded = json.load(file)
        return loaded if isinstance(loaded, list) else []

