from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.core.analysis_tables import build_failure_breakdown, build_model_comparison, build_schema_complexity
from app.db.crud import ResultStore
from app.dependencies import get_store

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/tables")
async def get_analysis_tables(
    run_id: str | None = None,
    store: ResultStore = Depends(get_store),
) -> dict[str, list[dict[str, Any]]]:
    db_path = store.database.db_path
    return {
        "table1_model_comparison": build_model_comparison(db_path, run_id=run_id),
        "table2_failure_breakdown": build_failure_breakdown(db_path, run_id=run_id),
        "table3_schema_complexity": build_schema_complexity(db_path, run_id=run_id),
    }
