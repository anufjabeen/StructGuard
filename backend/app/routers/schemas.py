from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.core.schema_loader import SchemaLoader, SchemaNotFoundError
from app.dependencies import get_schema_loader

router = APIRouter(prefix="/schemas", tags=["schemas"])


@router.get("")
async def list_schemas(schema_loader: SchemaLoader = Depends(get_schema_loader)) -> dict[str, list[str]]:
    return {"schemas": schema_loader.list_schemas()}


@router.get("/{schema_name}")
async def get_schema(
    schema_name: str,
    schema_loader: SchemaLoader = Depends(get_schema_loader),
) -> dict[str, Any]:
    try:
        return schema_loader.load(schema_name)
    except SchemaNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
