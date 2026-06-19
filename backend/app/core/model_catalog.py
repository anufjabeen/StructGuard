from __future__ import annotations

import os
from typing import Any

import httpx


class ModelCatalog:
    def __init__(self, ollama_base_url: str | None = None) -> None:
        self.ollama_base_url = (ollama_base_url or os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434").rstrip("/")

    async def describe(self) -> dict[str, Any]:
        ollama = await self._ollama_status()
        installed = ollama["models"] if ollama["available"] else []
        return {
            "mock_models": [
                {
                    "id": "mock/incident-json",
                    "label": "Schema-valid mock",
                    "supports": ["incident_report", "bug_template", "change_request"],
                },
                {
                    "id": "mock/wrapped-json",
                    "label": "Wrapped JSON mock",
                    "supports": ["incident_report", "bug_template", "change_request"],
                },
                {
                    "id": "mock/bad-enum",
                    "label": "Repair-path mock",
                    "supports": ["incident_report"],
                },
            ],
            "ollama": {
                "base_url": self.ollama_base_url,
                "available": ollama["available"],
                "models": installed,
            },
            "suggested_models": [
                "ollama/llama3.2:3b",
                "ollama/llama3.1:8b",
                "ollama/mistral:latest",
                "ollama/gemma2:latest",
                "mock/incident-json",
                "mock/wrapped-json",
            ],
        }

    async def _ollama_status(self) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.ollama_base_url}/api/tags")
            response.raise_for_status()
        except (httpx.HTTPError, ValueError):
            return {"available": False, "models": []}

        body = response.json()
        models = [
            f"ollama/{model['name']}"
            for model in body.get("models", [])
            if isinstance(model, dict) and isinstance(model.get("name"), str)
        ]
        return {"available": True, "models": models}
