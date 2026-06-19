from __future__ import annotations

from fastapi import Request

from app.core.benchmark_service import BenchmarkJobRegistry
from app.core.guardrails_engine import GuardrailsEngine
from app.core.model_catalog import ModelCatalog
from app.core.schema_loader import SchemaLoader
from app.db.crud import ResultStore


def get_engine() -> GuardrailsEngine:
    return GuardrailsEngine()


def get_store() -> ResultStore:
    return ResultStore()


def get_model_catalog() -> ModelCatalog:
    return ModelCatalog()


def get_schema_loader() -> SchemaLoader:
    return SchemaLoader()


def get_benchmark_jobs(request: Request) -> BenchmarkJobRegistry:
    registry = getattr(request.app.state, "benchmark_jobs", None)
    if registry is None:
        registry = BenchmarkJobRegistry()
        request.app.state.benchmark_jobs = registry
    return registry
