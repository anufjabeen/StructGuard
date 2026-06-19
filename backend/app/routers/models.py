from typing import Any

from fastapi import APIRouter, Depends

from app.core.model_catalog import ModelCatalog
from app.dependencies import get_model_catalog

router = APIRouter(prefix="/models", tags=["models"])


@router.get("")
async def list_models(catalog: ModelCatalog = Depends(get_model_catalog)) -> dict[str, Any]:
    return await catalog.describe()
