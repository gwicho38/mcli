"""Unit tests for Pydantic scheduler models."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from mcli.workflow.scheduler.models import (
    ExecutionRecord,
    JobHistoryFile,
    JobsFile,
    JobStatus,
    JobType,
    ScheduledJobModel,
)


class TestJobEnums:
    """Tests for job-related enums."""

    def test_job_status_values(self):
        """Test all job status values exist."""
        statuses = [s.value for s in JobStatus]
        assert "pending" in statuses
        assert "running" in statuses
        assert "completed" in statuses
        assert "failed" in statuses
        assert "cancelled" in statuses
        assert "skipped" in statuses

    def test_job_type_values(self):
        """Test all job type values exist."""
        types = [t.value for t in JobType]
        assert "command" in types
        assert "python" in types
        assert "cleanup" in types
        assert "system" in types
        assert "api_call" in types
        assert "custom" in types


class TestScheduledJobModel:
    """Tests for ScheduledJobModel."""

    def test_minimal_job(self):
        """Test creating a job with minimal required fields."""
        job = ScheduledJobModel(
            name="test_job",
            cron_expression="0 * * * *",
            command="echo hello",
        )
        assert job.name == "test_job"
        assert job.cron_expression == "0 * * * *"
        assert job.command == "echo hello"
        assert job.job_type == JobType.COMMAND
        assert job.enabled is True
        assert job.status == JobStatus.PENDING
        assert job.id  # Should have auto-generated UUID

    def test_full_job_config(self):
        """Test creating a job with all fields."""
        now = datetime.now()
        job = ScheduledJobModel(
            id="custom-uuid-123",
            name="backup_job",
            cron_expression="0 0 * * *",
            job_type=JobType.CLEANUP,
            command="/usr/bin/backup.sh",
            description="Daily backup",
            enabled=False,
            max_runtime=7200,
            retry_count=3,
            retry_delay=300,
            environment={"DB_HOST": "localhost"},
            working_directory="/home/user",
            output_format="text",
            notifications={"email": "admin@example.com"},
            status=JobStatus.RUNNING,
            created_at=now,
            run_count=5,
            success_count=4,
            failure_count=1,
        )
        assert job.id == "custom-uuid-123"
        assert job.name == "backup_job"
        assert job.job_type == JobType.CLEANUP
        assert job.description == "Daily backup"
        assert job.enabled is False
        assert job.max_runtime == 7200
        assert job.retry_count == 3
        assert job.environment == {"DB_HOST": "localhost"}
        assert job.run_count == 5

    def test_cron_expression_validation_valid(self):
        """Test valid cron expressions."""
        valid_crons = [
            "* * * * *",  # Every minute
            "0 * * * *",  # Every hour
            "0 0 * * *",  # Daily at midnight
            "0 0 * * 0",  # Weekly on Sunday
            "0 0 1 * *",  # Monthly on 1st
            "*/5 * * * *",  # Every 5 minutes
            "0 0 * * * *",  # 6 fields (with seconds)
        ]
        for cron in valid_crons:
            job = ScheduledJobModel(
                name="test",
                cron_expression=cron,
                command="echo test",
            )
            assert job.cron_expression == cron.strip()

    def test_cron_expression_validation_invalid(self):
        """Test invalid cron expressions are rejected."""
        invalid_crons = [
            "* * *",  # Too few fields
            "* * * *",  # 4 fields
            "* * * * * * *",  # Too many fields
            "",  # Empty
        ]
        for cron in invalid_crons:
            with pytest.raises(ValidationError) as exc_info:
                ScheduledJobModel(
                    name="test",
                    cron_expression=cron,
                    command="echo test",
                )
            assert "cron" in str(exc_info.value).lower()

    def test_max_runtime_bounds(self):
        """Test max_runtime must be within bounds."""
        # Valid range
        job = ScheduledJobModel(
            name="test",
            cron_expression="* * * * *",
            command="cmd",
            max_runtime=3600,
        )
        assert job.max_runtime == 3600

        # Too low
        with pytest.raises(ValidationError):
            ScheduledJobModel(
                name="test",
                cron_expression="* * * * *",
                command="cmd",
                max_runtime=0,
            )

        # Too high
        with pytest.raises(ValidationError):
            ScheduledJobModel(
                name="test",
                cron_expression="* * * * *",
                command="cmd",
                max_runtime=100000,  # > 86400
            )

    def test_retry_count_bounds(self):
        """Test retry_count must be non-negative and <= 10."""
        # Valid
        job = ScheduledJobModel(
            name="test",
            cron_expression="* * * * *",
            command="cmd",
            retry_count=5,
        )
        assert job.retry_count == 5

        # Too low
        with pytest.raises(ValidationError):
            ScheduledJobModel(
                name="test",
                cron_expression="* * * * *",
                command="cmd",
                retry_count=-1,
            )

        # Too high
        with pytest.raises(ValidationError):
            ScheduledJobModel(
                name="test",
                cron_expression="* * * * *",
                command="cmd",
                retry_count=11,
            )

    def test_environment_validation(self):
        """Test environment dict validation."""
        # Valid dict
        job = ScheduledJobModel(
            name="test",
            cron_expression="* * * * *",
            command="cmd",
            environment={"KEY": "value", "NUM": 123},  # Converts to strings
        )
        assert job.environment == {"KEY": "value", "NUM": "123"}

        # None becomes empty dict
        job2 = ScheduledJobModel(
            name="test",
            cron_expression="* * * * *",
            command="cmd",
            environment=None,
        )
        assert job2.environment == {}

    def test_should_retry_logic(self):
        """Test should_retry method."""
        job = ScheduledJobModel(
            name="test",
            cron_expression="* * * * *",
            command="cmd",
            retry_count=3,
            status=JobStatus.FAILED,
            current_retry=1,
        )
        assert job.should_retry() is True

        # At max retries
        job.current_retry = 3
        assert job.should_retry() is False

        # Not failed status
        job.status = JobStatus.COMPLETED
        assert job.should_retry() is False

    def test_name_required(self):
        """Test that name is required."""
        with pytest.raises(ValidationError) as exc_info:
            ScheduledJobModel(
                cron_expression="* * * * *",
                command="echo test",
            )
        assert "name" in str(exc_info.value)

    def test_command_required(self):
        """Test that command is required."""
        with pytest.raises(ValidationError) as exc_info:
            ScheduledJobModel(
                name="test",
                cron_expression="* * * * *",
            )
        assert "command" in str(exc_info.value)

    def test_serialization_roundtrip(self):
        """Test model can be serialized and deserialized."""
        job = ScheduledJobModel(
            name="test_job",
            cron_expression="0 * * * *",
            command="echo hello",
            environment={"KEY": "value"},
            status=JobStatus.RUNNING,
        )

        # Serialize to dict
        data = job.model_dump(mode="json")
        assert isinstance(data, dict)
        assert data["name"] == "test_job"
        assert data["status"] == "running"

        # Deserialize back
        restored = ScheduledJobModel.model_validate(data)
        assert restored.name == job.name
        assert restored.cron_expression == job.cron_expression
        assert restored.status == JobStatus.RUNNING


class TestExecutionRecord:
    """Tests for ExecutionRecord model."""

    def test_minimal_record(self):
        """Test ExecutionRecord with minimal fields."""
        record = ExecutionRecord(
            job_id="job-123",
            job_name="test_job",
            status="completed",
        )
        assert record.job_id == "job-123"
        assert record.job_name == "test_job"
        assert record.status == "completed"
        assert record.runtime_seconds == 0.0
        assert record.output == ""
        assert record.error == ""

    def test_full_record(self):
        """Test ExecutionRecord with all fields."""
        record = ExecutionRecord(
            job_id="job-456",
            job_name="backup",
            status="failed",
            runtime_seconds=45.5,
            output="Starting backup...",
            error="Connection refused",
            exit_code=1,
            retries=2,
        )
        assert record.runtime_seconds == 45.5
        assert record.exit_code == 1
        assert record.retries == 2

    def test_output_truncation(self):
        """Test that output is truncated to 1000 chars."""
        long_output = "x" * 2000
        record = ExecutionRecord(
            job_id="job-1",
            job_name="test",
            status="completed",
            output=long_output,
        )
        assert len(record.output) == 1000

    def test_error_truncation(self):
        """Test that error is truncated to 1000 chars."""
        long_error = "e" * 2000
        record = ExecutionRecord(
            job_id="job-1",
            job_name="test",
            status="failed",
            error=long_error,
        )
        assert len(record.error) == 1000

    def test_runtime_non_negative(self):
        """Test that runtime_seconds must be non-negative."""
        with pytest.raises(ValidationError):
            ExecutionRecord(
                job_id="job-1",
                job_name="test",
                status="failed",
                runtime_seconds=-1.0,
            )


class TestJobsFile:
    """Tests for JobsFile model."""

    def test_empty_jobs_file(self):
        """Test empty JobsFile."""
        jobs_file = JobsFile()
        assert jobs_file.jobs == []
        assert jobs_file.version == "1.0"
        assert jobs_file.count == 0

    def test_jobs_file_with_jobs(self):
        """Test JobsFile with jobs."""
        job = ScheduledJobModel(
            name="test",
            cron_expression="* * * * *",
            command="echo test",
        )
        jobs_file = JobsFile(
            jobs=[job],
            version="2.0",
            saved_at=datetime.now(),
            count=1,
        )
        assert len(jobs_file.jobs) == 1
        assert jobs_file.version == "2.0"
        assert jobs_file.count == 1

    def test_serialization_roundtrip(self):
        """Test JobsFile serialization."""
        job = ScheduledJobModel(
            name="test",
            cron_expression="0 * * * *",
            command="cmd",
        )
        jobs_file = JobsFile(jobs=[job], count=1)

        data = jobs_file.model_dump(mode="json")
        restored = JobsFile.model_validate(data)

        assert len(restored.jobs) == 1
        assert restored.jobs[0].name == "test"


class TestJobHistoryFile:
    """Tests for JobHistoryFile model."""

    def test_empty_history(self):
        """Test empty JobHistoryFile."""
        history_file = JobHistoryFile()
        assert history_file.history == []
        assert history_file.version == "1.0"
        assert history_file.updated_at is None

    def test_history_with_records(self):
        """Test JobHistoryFile with records."""
        record = ExecutionRecord(
            job_id="job-1",
            job_name="test",
            status="completed",
        )
        history_file = JobHistoryFile(
            history=[record],
            updated_at=datetime.now(),
        )
        assert len(history_file.history) == 1
        assert history_file.history[0].job_name == "test"

    def test_serialization_roundtrip(self):
        """Test JobHistoryFile serialization."""
        record = ExecutionRecord(
            job_id="job-123",
            job_name="backup",
            status="completed",
            runtime_seconds=30.0,
        )
        history_file = JobHistoryFile(
            history=[record],
            updated_at=datetime.now(),
        )

        data = history_file.model_dump(mode="json")
        restored = JobHistoryFile.model_validate(data)

        assert len(restored.history) == 1
        assert restored.history[0].job_id == "job-123"
