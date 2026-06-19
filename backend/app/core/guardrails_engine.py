from __future__ import annotations

import time
from typing import Any

from app.core.failure_classifier import FailureClassifier
from app.core.failure_taxonomy import FailureType
from app.core.json_extractor import JsonExtractor
from app.core.llm_router import LLMRouter, LLMRouterError, LLMUnavailableError, RateLimitError
from app.core.prompt_builder import PromptBuilder
from app.core.repair import JsonRepairer
from app.core.schema_loader import SchemaLoader
from app.models.schemas_pydantic import FailureSummary, GenerationResponse, RawAttempt


class GuardrailsEngine:
    def __init__(
        self,
        schema_loader: SchemaLoader | None = None,
        prompt_builder: PromptBuilder | None = None,
        llm_router: LLMRouter | None = None,
    ) -> None:
        self.schema_loader = schema_loader or SchemaLoader()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.llm_router = llm_router or LLMRouter()
        self.extractor = JsonExtractor()
        self.repairer = JsonRepairer()
        self.classifier = FailureClassifier()

    async def generate(
        self,
        input_text: str,
        schema_name: str,
        model: str,
        use_few_shots: bool = True,
        max_attempts: int = 3,
        expected: dict[str, Any] | None = None,
    ) -> GenerationResponse:
        schema = self.schema_loader.load(schema_name)
        validator = self.schema_loader.validator(schema_name)
        attempts: list[RawAttempt] = []
        corrective_context: str | None = None
        started = time.perf_counter()

        for attempt_number in range(1, max_attempts + 1):
            prompt = self.prompt_builder.build(
                input_text=input_text,
                schema_name=schema_name,
                schema=schema,
                use_few_shots=use_few_shots,
                corrective_context=corrective_context,
            )
            attempt_started = time.perf_counter()
            try:
                raw_output = await self.llm_router.generate(prompt=prompt, model=model)
            except RateLimitError as exc:
                raw_attempt = self._attempt_from_exception(attempt_number, FailureType.RATE_LIMITED, exc, attempt_started)
                attempts.append(raw_attempt)
                corrective_context = raw_attempt.error
                continue
            except LLMUnavailableError as exc:
                attempts.append(self._attempt_from_exception(attempt_number, FailureType.LLM_UNAVAILABLE, exc, attempt_started))
                break
            except LLMRouterError as exc:
                attempts.append(self._attempt_from_exception(attempt_number, FailureType.UNKNOWN, exc, attempt_started))
                break

            extraction = self.extractor.extract(raw_output)
            if extraction.data is None:
                raw_attempt = RawAttempt(
                    attempt=attempt_number,
                    raw=raw_output,
                    extracted=None,
                    repaired=None,
                    extraction_strategy=extraction.strategy,
                    failure=extraction.failure_type,
                    fields=[],
                    repairs=[],
                    latency_ms=self._elapsed_ms(attempt_started),
                    error=extraction.error,
                )
                attempts.append(raw_attempt)
                corrective_context = self._corrective_context(raw_attempt)
                continue

            repaired, repairs = self.repairer.repair(extraction.data, schema)
            validation_errors = sorted(
                validator.iter_errors(repaired),
                key=lambda error: list(error.absolute_path),
            )

            if validation_errors:
                first_error = validation_errors[0]
                failure_type, fields = self.classifier.classify_schema_error(first_error)
                raw_attempt = RawAttempt(
                    attempt=attempt_number,
                    raw=raw_output,
                    extracted=extraction.data,
                    repaired=repaired,
                    extraction_strategy=extraction.strategy,
                    failure=failure_type,
                    fields=fields,
                    repairs=repairs,
                    latency_ms=self._elapsed_ms(attempt_started),
                    error=first_error.message,
                )
                attempts.append(raw_attempt)
                corrective_context = self._corrective_context(raw_attempt)
                continue

            semantic_failures = self.classifier.semantic_failures(repaired, expected)
            if semantic_failures:
                failure_type, field, error = semantic_failures[0]
                raw_attempt = RawAttempt(
                    attempt=attempt_number,
                    raw=raw_output,
                    extracted=extraction.data,
                    repaired=repaired,
                    extraction_strategy=extraction.strategy,
                    failure=failure_type,
                    fields=[field],
                    repairs=repairs,
                    latency_ms=self._elapsed_ms(attempt_started),
                    error=error,
                )
                attempts.append(raw_attempt)
                corrective_context = self._corrective_context(raw_attempt)
                continue

            attempts.append(
                RawAttempt(
                    attempt=attempt_number,
                    raw=raw_output,
                    extracted=extraction.data,
                    repaired=repaired,
                    extraction_strategy=extraction.strategy,
                    failure=extraction.failure_type,
                    fields=[],
                    repairs=repairs,
                    latency_ms=self._elapsed_ms(attempt_started),
                    error=None,
                )
            )
            return GenerationResponse(
                success=True,
                schema_name=schema_name,
                model=model,
                attempts=len(attempts),
                output=repaired,
                raw_attempts=attempts,
                latency_ms=self._elapsed_ms(started),
            )

        return GenerationResponse(
            success=False,
            schema_name=schema_name,
            model=model,
            attempts=len(attempts),
            output=None,
            raw_attempts=attempts,
            latency_ms=self._elapsed_ms(started),
            failure_summary=self._failure_summary(attempts),
        )

    def _attempt_from_exception(
        self,
        attempt_number: int,
        failure_type: FailureType,
        exc: Exception,
        attempt_started: float,
    ) -> RawAttempt:
        return RawAttempt(
            attempt=attempt_number,
            raw="",
            extracted=None,
            repaired=None,
            extraction_strategy="none",
            failure=failure_type,
            fields=[],
            repairs=[],
            latency_ms=self._elapsed_ms(attempt_started),
            error=str(exc),
        )

    def _corrective_context(self, attempt: RawAttempt) -> str:
        fields = f" Fields: {', '.join(attempt.fields)}." if attempt.fields else ""
        details = f" Details: {attempt.error}" if attempt.error else ""
        return f"Failure type: {attempt.failure}.{fields}{details}"

    def _failure_summary(self, attempts: list[RawAttempt]) -> FailureSummary | None:
        if not attempts:
            return None
        attempt = attempts[-1]
        if attempt.failure is None:
            return None
        return FailureSummary(
            attempt=attempt.attempt,
            failure_type=attempt.failure,
            fields=attempt.fields,
            message=attempt.error,
            repairs=attempt.repairs,
            extraction_strategy=attempt.extraction_strategy,
            latency_ms=attempt.latency_ms,
        )

    def _elapsed_ms(self, start: float) -> int:
        return round((time.perf_counter() - start) * 1000)
