from fastapi import APIRouter, Depends, HTTPException

from app.core.benchmark_service import BenchmarkJobRegistry
from app.dependencies import get_benchmark_jobs
from app.models.schemas_pydantic import BenchmarkJobResponse, BenchmarkRunRequest

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])


@router.post("/run", response_model=BenchmarkJobResponse)
async def run_benchmark(
    request: BenchmarkRunRequest,
    jobs: BenchmarkJobRegistry = Depends(get_benchmark_jobs),
) -> BenchmarkJobResponse:
    return await jobs.start(request)


@router.get("", response_model=list[BenchmarkJobResponse])
async def list_benchmark_jobs(jobs: BenchmarkJobRegistry = Depends(get_benchmark_jobs)) -> list[BenchmarkJobResponse]:
    return jobs.list()


@router.get("/{run_id}", response_model=BenchmarkJobResponse)
async def get_benchmark_job(
    run_id: str,
    jobs: BenchmarkJobRegistry = Depends(get_benchmark_jobs),
) -> BenchmarkJobResponse:
    job = jobs.get(run_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Unknown benchmark run id: {run_id}")
    return job
