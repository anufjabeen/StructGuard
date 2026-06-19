from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.db.crud import ResultStore
from app.dependencies import get_store

router = APIRouter(prefix="/results", tags=["results"])


@router.get("")
async def list_results(
    run_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    store: ResultStore = Depends(get_store),
) -> dict[str, list[dict[str, Any]]]:
    return {"results": store.list_results(run_id=run_id, limit=limit)}


@router.get("/summary")
async def summarize_results(run_id: str | None = None, store: ResultStore = Depends(get_store)) -> dict[str, Any]:
    return store.summarize(run_id=run_id)


@router.get("/runs")
async def list_runs(
    limit: int = Query(default=100, ge=1, le=500),
    store: ResultStore = Depends(get_store),
) -> dict[str, list[dict[str, Any]]]:
    return {"runs": store.list_runs(limit=limit)}


@router.get("/{result_id}")
async def get_result(result_id: int, store: ResultStore = Depends(get_store)) -> dict[str, Any]:
    result = store.get_result(result_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Unknown result id: {result_id}")
    return result
