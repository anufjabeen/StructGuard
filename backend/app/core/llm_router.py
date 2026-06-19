import json
import os
from typing import Any

import httpx


class LLMRouterError(RuntimeError):
    pass


class RateLimitError(LLMRouterError):
    pass


class LLMUnavailableError(LLMRouterError):
    pass


class LLMRouter:
    def __init__(self, ollama_base_url: str | None = None) -> None:
        self.ollama_base_url = (ollama_base_url or os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434").rstrip("/")

    async def generate(self, prompt: str, model: str, max_tokens: int = 1000) -> str:
        if model.startswith("mock/"):
            return self._mock_response(prompt, model)
        if model.startswith("ollama/"):
            return await self._call_ollama(prompt=prompt, model=model.removeprefix("ollama/"), max_tokens=max_tokens)
        raise LLMRouterError(f"Unsupported model id: {model}")

    async def _call_ollama(self, prompt: str, model: str, max_tokens: int) -> str:
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0,
                "num_predict": max_tokens,
            },
        }
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(f"{self.ollama_base_url}/api/generate", json=payload)
        except httpx.ConnectError as exc:
            raise LLMUnavailableError(
                f"Could not connect to Ollama at {self.ollama_base_url}. Is `ollama serve` running?"
            ) from exc
        except httpx.TimeoutException as exc:
            raise LLMUnavailableError("Timed out waiting for Ollama response.") from exc

        if response.status_code == 429:
            raise RateLimitError("Ollama returned HTTP 429.")
        if response.status_code >= 400:
            raise LLMUnavailableError(f"Ollama returned HTTP {response.status_code}: {response.text[:300]}")

        body = response.json()
        text = body.get("response")
        if not isinstance(text, str):
            raise LLMUnavailableError("Ollama response did not contain a string `response` field.")
        return text

    def _mock_response(self, prompt: str, model: str) -> str:
        schema_name = self._schema_from_prompt(prompt)
        if model == "mock/wrapped-json":
            return f"""Here is the structured output:
```json
{json.dumps(self._mock_payload(schema_name), indent=2)}
```"""

        if model == "mock/bad-enum":
            return """{
  "title": "Checkout outage affecting users",
  "severity": "urgent",
  "affected_service": "checkout",
  "reported_at": "June 16 2026 10:14",
  "affected_users": "500",
  "description": "Checkout service was unavailable for a group of users.",
  "status": "OPEN"
}"""

        return json.dumps(self._mock_payload(schema_name), indent=2)

    def _schema_from_prompt(self, prompt: str) -> str:
        if '"title": "BugTicket"' in prompt:
            return "bug_template"
        if '"title": "ChangeRequest"' in prompt:
            return "change_request"
        return "incident_report"

    def _mock_payload(self, schema_name: str) -> dict[str, Any]:
        if schema_name == "bug_template":
            return {
                "title": "Checkout button fails on payment page",
                "severity": "high",
                "component": "checkout",
                "environment": "production",
                "steps_to_reproduce": [
                    "Open the checkout page",
                    "Enter valid payment details",
                    "Select the submit payment button",
                ],
                "expected_behavior": "The payment should submit and create an order.",
                "actual_behavior": "The button displays an error and the order is not created.",
                "reported_at": "2026-06-16T10:14:00Z",
                "browser": "Chrome",
                "os": "Windows",
                "status": "triaged",
                "assignee": {
                    "name": "Unassigned",
                    "team": "Web Platform",
                },
            }

        if schema_name == "change_request":
            return {
                "title": "Increase checkout database connection pool",
                "change_type": "normal",
                "risk_level": "medium",
                "affected_services": ["checkout", "payments"],
                "requested_by": {
                    "name": "Taylor Morgan",
                    "team": "SRE",
                },
                "requested_at": "2026-06-16T10:14:00Z",
                "implementation_window": {
                    "starts_at": "2026-06-17T02:00:00Z",
                    "ends_at": "2026-06-17T03:00:00Z",
                },
                "rollback_plan": "Restore the previous connection pool setting and restart the checkout service.",
                "approval_status": "pending",
                "business_justification": "Reducing checkout saturation will improve order completion reliability.",
                "dependencies": ["database maintenance window"],
                "reviewers": [
                    {
                        "name": "Jordan Lee",
                        "role": "operations",
                    }
                ],
            }

        return {
            "title": "Checkout outage affecting users",
            "severity": "critical",
            "affected_service": "checkout",
            "reported_at": "2026-06-16T10:14:00Z",
            "affected_users": 500,
            "description": "Checkout service was unavailable for a group of users.",
            "root_cause": "Unknown at report time",
            "resolution_steps": ["Investigate service health", "Notify incident response"],
            "status": "investigating",
            "assignee": {
                "name": "Unassigned",
                "team": "SRE",
            },
        }
