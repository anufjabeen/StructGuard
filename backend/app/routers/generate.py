import logging

from fastapi import APIRouter, Depends, HTTPException

from app.core.guardrails_engine import GuardrailsEngine
from app.core.schema_loader import SchemaNotFoundError
from app.db.crud import ResultStore
from app.dependencies import get_engine, get_store
from app.models.schemas_pydantic import GenerateRequest, GenerationResponse

router = APIRouter(prefix="/generate", tags=["generate"])
logger = logging.getLogger(__name__)


@router.post("", response_model=GenerationResponse)
async def generate(
    request: GenerateRequest,
    engine: GuardrailsEngine = Depends(get_engine),
    store: ResultStore = Depends(get_store),
) -> GenerationResponse:
    try:
        result = await engine.generate(
            input_text=request.input_text,
            schema_name=request.schema_name,
            model=request.model,
            use_few_shots=request.use_few_shots,
            max_attempts=request.max_attempts,
            expected=request.expected,
        )
        if request.persist:
            result_id = store.save_generation(
                input_text=request.input_text,
                response=result,
                run_id=request.run_id,
                case_id=request.case_id,
            )
            result = result.model_copy(update={"result_id": result_id})
        return result
    except SchemaNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unhandled generation failure for schema=%s model=%s", request.schema_name, request.model)
        raise HTTPException(status_code=500, detail="Generation failed unexpectedly.") from exc
