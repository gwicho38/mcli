"""
Pydantic models for scheduler job configurations.

Provides type-safe validation for:
- Job definitions (ScheduledJobModel)
- Job storage files (JobsFile, JobHistoryFile)
- Execution records (ExecutionRecord)

These models replace manual dict serialization with Pydantic's
built-in validation, serialization, and type coercion.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class JobStatus(str, Enum):
    """Job execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class JobType(str, Enum):
    """Types of jobs that can be scheduled."""

    COMMAND = "command"  # Execute shell commands
    PYTHON = "python"  # Execute Python code
    CLEANUP = "cleanup"  # File system cleanup tasks
    SYSTEM = "system"  # System maintenance tasks
    API_CALL = "api_call"  # HTTP API calls
    CUSTOM = "custom"  # Custom user-defined jobs


class ScheduledJobModel(BaseModel):
    """
    Pydantic model for a scheduled job configuration.

    Validates all job fields and provides serialization via model_dump().
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True,
    )

    # Core job definition
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., min_length=1, max_length=255)
    cron_expression: str = Field(..., min_length=1)
    job_type: JobType = Field(default=JobType.COMMAND)
    command: str = Field(..., min_length=1)
    description: str = Field(default="")
    enabled: bool = Field(default=True)

    # Execution constraints
    max_runtime: int = Field(default=3600, ge=1, le=86400)  # 1 second to 24 hours
    retry_count: int = Field(default=0, ge=0, le=10)
    retry_delay: int = Field(default=60, ge=1, le=3600)  # 1 second to 1 hour

    # Environment configuration
    environment: dict[str, str] = Field(default_factory=dict)
    working_directory: Optional[str] = Field(default=None)
    output_format: str = Field(default="json")
    notifications: dict[str, Any] = Field(default_factory=dict)

    # Runtime state tracking
    status: JobStatus = Field(default=JobStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.now)
    last_run: Optional[datetime] = Field(default=None)
    next_run: Optional[datetime] = Field(default=None)
    run_count: int = Field(default=0, ge=0)
    success_count: int = Field(default=0, ge=0)
    failure_count: int = Field(default=0, ge=0)
    last_output: str = Field(default="")
    last_error: str = Field(default="")
    runtime_seconds: float = Field(default=0.0, ge=0.0)
    current_retry: int = Field(default=0, ge=0)

    @field_validator("cron_expression")
    @classmethod
    def validate_cron_expression(cls, v: str) -> str:
        """Validate cron expression format (basic check)."""
        parts = v.strip().split()
        # Standard cron has 5 parts, some systems allow 6 (with seconds)
        if len(parts) < 5 or len(parts) > 6:
            raise ValueError(f"Invalid cron expression: expected 5 or 6 fields, got {len(parts)}")
        return v.strip()

    @field_validator("environment", mode="before")
    @classmethod
    def validate_environment(cls, v: Any) -> dict[str, str]:
        """Ensure environment values are strings."""
        if v is None:
            return {}
        if not isinstance(v, dict):
            raise ValueError("environment must be a dictionary")
        return {str(k): str(val) for k, val in v.items()}

    def should_retry(self) -> bool:
        """Check if job should be retried after failure."""
        return self.status == JobStatus.FAILED and self.current_retry < self.retry_count


class ExecutionRecord(BaseModel):
    """Record of a single job execution."""

    model_config = ConfigDict(str_strip_whitespace=True)

    job_id: str
    job_name: str
    executed_at: datetime = Field(default_factory=datetime.now)
    status: str
    runtime_seconds: float = Field(default=0.0, ge=0.0)
    output: str = Field(default="", max_length=1000)
    error: str = Field(default="", max_length=1000)
    exit_code: Optional[int] = Field(default=None)
    retries: int = Field(default=0, ge=0)

    @field_validator("output", "error", mode="before")
    @classmethod
    def truncate_long_strings(cls, v: Any) -> str:
        """Truncate output/error to max 1000 characters."""
        if v is None:
            return ""
        s = str(v)
        return s[:1000] if len(s) > 1000 else s


class JobsFile(BaseModel):
    """Schema for jobs.json storage file."""

    model_config = ConfigDict(str_strip_whitespace=True)

    jobs: list[ScheduledJobModel] = Field(default_factory=list)
    version: str = Field(default="1.0")
    saved_at: Optional[datetime] = Field(default=None)
    count: int = Field(default=0, ge=0)

    @field_validator("count", mode="before")
    @classmethod
    def compute_count(cls, v: Any, info) -> int:
        """Auto-compute count from jobs list if not provided."""
        # This is a fallback; actual count should match jobs length
        return v if v is not None else 0


class JobHistoryFile(BaseModel):
    """Schema for job_history.json storage file."""

    model_config = ConfigDict(str_strip_whitespace=True)

    history: list[ExecutionRecord] = Field(default_factory=list)
    version: str = Field(default="1.0")
    updated_at: Optional[datetime] = Field(default=None)


# Type aliases for backward compatibility
JobStatusEnum = JobStatus
JobTypeEnum = JobType
