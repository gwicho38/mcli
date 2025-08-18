"""
Job definitions and status tracking for the MCLI scheduler
"""

import json
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)


class JobStatus(Enum):
    """Job execution status"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class JobType(Enum):
    """Types of jobs that can be scheduled"""

    COMMAND = "command"  # Execute shell commands
    PYTHON = "python"  # Execute Python code
    CLEANUP = "cleanup"  # File system cleanup tasks
    SYSTEM = "system"  # System maintenance tasks
    API_CALL = "api_call"  # HTTP API calls
    CUSTOM = "custom"  # Custom user-defined jobs


class ScheduledJob:
    """Represents a scheduled job with all its metadata"""

    def __init__(
        self,
        name: str,
        cron_expression: str,
        job_type: JobType,
        command: str,
        description: str = "",
        enabled: bool = True,
        max_runtime: int = 3600,  # 1 hour default
        retry_count: int = 0,
        retry_delay: int = 60,  # 1 minute default
        environment: Optional[Dict[str, str]] = None,
        working_directory: Optional[str] = None,
        output_format: str = "json",
        notifications: Optional[Dict[str, Any]] = None,
        job_id: Optional[str] = None,
    ):
        self.id = job_id or str(uuid.uuid4())
        self.name = name
        self.cron_expression = cron_expression
        self.job_type = job_type
        self.command = command
        self.description = description
        self.enabled = enabled
        self.max_runtime = max_runtime
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.environment = environment or {}
        self.working_directory = working_directory
        self.output_format = output_format
        self.notifications = notifications or {}

        # Runtime tracking
        self.status = JobStatus.PENDING
        self.created_at = datetime.now()
        self.last_run = None
        self.next_run = None
        self.run_count = 0
        self.success_count = 0
        self.failure_count = 0
        self.last_output = ""
        self.last_error = ""
        self.runtime_seconds = 0
        self.current_retry = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary for serialization"""
        return {
            "id": self.id,
            "name": self.name,
            "cron_expression": self.cron_expression,
            "job_type": self.job_type.value,
            "command": self.command,
            "description": self.description,
            "enabled": self.enabled,
            "max_runtime": self.max_runtime,
            "retry_count": self.retry_count,
            "retry_delay": self.retry_delay,
            "environment": self.environment,
            "working_directory": self.working_directory,
            "output_format": self.output_format,
            "notifications": self.notifications,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "run_count": self.run_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "last_output": self.last_output,
            "last_error": self.last_error,
            "runtime_seconds": self.runtime_seconds,
            "current_retry": self.current_retry,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScheduledJob":
        """Create job from dictionary"""
        job = cls(
            name=data["name"],
            cron_expression=data["cron_expression"],
            job_type=JobType(data["job_type"]),
            command=data["command"],
            description=data.get("description", ""),
            enabled=data.get("enabled", True),
            max_runtime=data.get("max_runtime", 3600),
            retry_count=data.get("retry_count", 0),
            retry_delay=data.get("retry_delay", 60),
            environment=data.get("environment", {}),
            working_directory=data.get("working_directory"),
            output_format=data.get("output_format", "json"),
            notifications=data.get("notifications", {}),
            job_id=data.get("id"),
        )

        # Restore runtime state
        job.status = JobStatus(data.get("status", "pending"))
        job.created_at = datetime.fromisoformat(data["created_at"])
        job.last_run = datetime.fromisoformat(data["last_run"]) if data.get("last_run") else None
        job.next_run = datetime.fromisoformat(data["next_run"]) if data.get("next_run") else None
        job.run_count = data.get("run_count", 0)
        job.success_count = data.get("success_count", 0)
        job.failure_count = data.get("failure_count", 0)
        job.last_output = data.get("last_output", "")
        job.last_error = data.get("last_error", "")
        job.runtime_seconds = data.get("runtime_seconds", 0)
        job.current_retry = data.get("current_retry", 0)

        return job

    def update_status(self, status: JobStatus, output: str = "", error: str = ""):
        """Update job status and related metadata"""
        self.status = status
        self.last_output = output
        self.last_error = error

        if status == JobStatus.RUNNING:
            self.last_run = datetime.now()
            self.run_count += 1
        elif status == JobStatus.COMPLETED:
            self.success_count += 1
            self.current_retry = 0
        elif status == JobStatus.FAILED:
            self.failure_count += 1

    def should_retry(self) -> bool:
        """Check if job should be retried after failure"""
        return self.status == JobStatus.FAILED and self.current_retry < self.retry_count

    def get_next_retry_time(self) -> datetime:
        """Calculate next retry time"""
        return datetime.now() + timedelta(seconds=self.retry_delay)

    def to_json(self) -> str:
        """Convert job to JSON string"""
        return json.dumps(self.to_dict(), indent=2)

    def __str__(self) -> str:
        return f"Job(id={self.id[:8]}, name={self.name}, status={self.status.value})"

    def __repr__(self) -> str:
        return f"ScheduledJob(id='{self.id}', name='{self.name}', cron='{self.cron_expression}')"
