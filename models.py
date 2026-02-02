"""Data models for the Deliberate API."""

from datetime import datetime
from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field


# === Request Models ===

class DeliberateRequest(BaseModel):
    """Request to start a deliberation."""

    thesis: str = Field(..., description="The question or proposition to analyze")
    context: str | None = Field(None, description="Optional background context")
    models: list[str] | None = Field(
        None,
        description="LLM models to use (3 required). Defaults to diverse set.",
        min_length=3,
        max_length=3,
    )


# === Job Models ===

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Job(BaseModel):
    """A deliberation job."""

    id: str
    status: JobStatus
    thesis: str
    context: str | None = None
    models: list[str]
    current_round: int | None = None
    result: "DeliberationResult | None" = None
    error: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    tokens_used: int = 0


# === Result Models ===

class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DeliberationResult(BaseModel):
    """The structured output of a deliberation."""

    # Core answer
    answer: str = Field(..., description="Direct response to the query")
    confidence: Confidence = Field(..., description="Overall confidence level")

    # Supporting points
    support: list[str] = Field(
        default_factory=list,
        description="Key points supporting the answer"
    )

    # Concerns/risks
    concerns: list[str] = Field(
        default_factory=list,
        description="Key risks or limitations"
    )

    # Strongest agreement
    conviction: str = Field("", description="What agents most strongly agreed on")

    # Open questions
    open_questions: list[str] = Field(
        default_factory=list,
        description="Unresolved issues that matter most"
    )

    # Metadata
    tokens_used: int = 0
    rounds_completed: int = 3


# === Response Models ===

class JobCreatedResponse(BaseModel):
    """Response when a job is created."""

    job_id: str
    status: JobStatus
    poll_url: str


class JobStatusResponse(BaseModel):
    """Response when polling job status."""

    job_id: str
    status: JobStatus
    current_round: int | None = None
    result: DeliberationResult | None = None
    error: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


# === Agent Output (internal) ===

class AgentOutput(BaseModel):
    """Output from a single agent for a round."""

    agent_id: str
    model: str
    content: str
    tokens_used: int


class RoundOutput(BaseModel):
    """Output from a complete round."""

    round_number: int
    outputs: list[AgentOutput]
    total_tokens: int
