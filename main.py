"""Deliberate API - Multi-agent deliberation service.

A service that stress-tests ideas through structured AI debate.
"""

import os
import asyncio
import logging
import secrets
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.security import APIKeyHeader
from dotenv import load_dotenv

from models import (
    Job, JobStatus, DeliberateRequest,
    JobCreatedResponse, JobStatusResponse,
)
from engine import DeliberationEngine, DEFAULT_MODELS

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory job storage (replace with Redis/DynamoDB for production)
jobs: dict[str, Job] = {}

# API key validation
API_KEY_HEADER = APIKeyHeader(name="X-API-Key")
VALID_API_KEYS = set(os.getenv("API_KEYS", "").split(","))


def verify_api_key(api_key: str = Depends(API_KEY_HEADER)) -> str:
    """Verify the API key is valid."""
    if not VALID_API_KEYS or api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Deliberate API starting...")
    yield
    logger.info("Deliberate API shutting down...")


app = FastAPI(
    title="Deliberate API",
    description="Multi-agent deliberation service for stress-testing ideas",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers."""
    return {"status": "healthy"}


@app.post("/v1/deliberate", response_model=JobCreatedResponse)
async def create_deliberation(
    request: DeliberateRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key),
):
    """
    Start a new deliberation.

    Returns a job ID that can be polled for status and results.
    """
    # Generate job ID
    job_id = f"dlb_{secrets.token_urlsafe(12)}"

    # Use provided models or defaults
    models = request.models or DEFAULT_MODELS

    # Create job
    job = Job(
        id=job_id,
        status=JobStatus.PENDING,
        thesis=request.thesis,
        context=request.context,
        models=models,
    )
    jobs[job_id] = job

    # Start deliberation in background
    background_tasks.add_task(run_deliberation_task, job_id)

    logger.info(f"Created job {job_id}: {request.thesis[:50]}...")

    return JobCreatedResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        poll_url=f"/v1/jobs/{job_id}",
    )


@app.get("/v1/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    api_key: str = Depends(verify_api_key),
):
    """
    Get the status of a deliberation job.

    Poll this endpoint until status is 'completed' or 'failed'.
    """
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        current_round=job.current_round,
        result=job.result,
        error=job.error,
        created_at=job.created_at,
        completed_at=job.completed_at,
    )


@app.get("/v1/jobs", response_model=list[JobStatusResponse])
async def list_jobs(
    api_key: str = Depends(verify_api_key),
    limit: int = 20,
):
    """List recent jobs."""
    sorted_jobs = sorted(
        jobs.values(),
        key=lambda j: j.created_at,
        reverse=True,
    )[:limit]

    return [
        JobStatusResponse(
            job_id=job.id,
            status=job.status,
            current_round=job.current_round,
            result=job.result,
            error=job.error,
            created_at=job.created_at,
            completed_at=job.completed_at,
        )
        for job in sorted_jobs
    ]


async def run_deliberation_task(job_id: str):
    """Background task to run deliberation."""
    job = jobs.get(job_id)
    if not job:
        return

    job.status = JobStatus.RUNNING
    engine = DeliberationEngine()

    async def on_progress(round_num: int, message: str):
        job.current_round = round_num
        logger.info(f"Job {job_id}: Round {round_num} - {message}")

    try:
        result = await engine.run_deliberation(job, on_progress)
        job.result = result
        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.utcnow()
        logger.info(f"Job {job_id} completed: {result.verdict[:50]}...")

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)
        job.status = JobStatus.FAILED
        job.error = str(e)
        job.completed_at = datetime.utcnow()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
