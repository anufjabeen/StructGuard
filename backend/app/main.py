import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.analysis import router as analysis_router
from app.routers.benchmarks import router as benchmarks_router
from app.routers.generate import router as generate_router
from app.routers.models import router as models_router
from app.routers.results import router as results_router
from app.routers.schemas import router as schemas_router

app = FastAPI(
    title="Guardrails for Structured Outputs",
    version="0.1.0",
    description="Validate, repair, retry, and log schema-conformant LLM JSON outputs.",
)

default_origins = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000"
origins = [origin.strip() for origin in os.getenv("FRONTEND_ORIGINS", default_origins).split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(models_router)
app.include_router(generate_router)
app.include_router(schemas_router)
app.include_router(results_router)
app.include_router(benchmarks_router)
app.include_router(analysis_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
