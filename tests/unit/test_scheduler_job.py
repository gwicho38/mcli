"""
Unit tests for mcli.workflow.scheduler.job module
"""

import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest


class TestJobStatus:
    """Test suite for JobStatus enum"""

    def test_job_status_enum_values(self):
        """Test JobStatus enum has all expected values"""
        from mcli.workflow.scheduler.job import JobStatus

        assert JobStatus.PENDING.value == "pending"
        assert JobStatus.RUNNING.value == "running"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.FAILED.value == "failed"
        assert JobStatus.CANCELLED.value == "cancelled"
        assert JobStatus.SKIPPED.value == "skipped"

    def test_job_status_enum_count(self):
        """Test JobStatus has exactly 6 statuses"""
        from mcli.workflow.scheduler.job import JobStatus

        assert len(list(JobStatus)) == 6


class TestJobType:
    """Test suite for JobType enum"""

    def test_job_type_enum_values(self):
        """Test JobType enum has all expected values"""
        from mcli.workflow.scheduler.job import JobType

        assert JobType.COMMAND.value == "command"
        assert JobType.PYTHON.value == "python"
        assert JobType.CLEANUP.value == "cleanup"
        assert JobType.SYSTEM.value == "system"
        assert JobType.API_CALL.value == "api_call"
        assert JobType.CUSTOM.value == "custom"

    def test_job_type_enum_count(self):
        """Test JobType has exactly 6 types"""
        from mcli.workflow.scheduler.job import JobType

        assert len(list(JobType)) == 6


class TestScheduledJob:
    """Test suite for ScheduledJob class"""

    def test_scheduled_job_init_minimal(self):
        """Test ScheduledJob initialization with minimal parameters"""
        from mcli.workflow.scheduler.job import JobType, ScheduledJob

        job = ScheduledJob(
            name="test_job",
            cron_expression="* * * * *",
            job_type=JobType.COMMAND,
            command="echo test",
        )

        assert job.name == "test_job"
        assert job.cron_expression == "* * * * *"
        assert job.job_type == JobType.COMMAND
        assert job.command == "echo test"
        assert job.description == ""
        assert job.enabled is True
        assert job.max_runtime == 3600
        assert job.retry_count == 0
        assert job.retry_delay == 60
        assert job.environment == {}
        assert job.working_directory is None
        assert job.output_format == "json"
        assert job.notifications == {}

    def test_scheduled_job_init_full_parameters(self):
        """Test ScheduledJob initialization with all parameters"""
        from mcli.workflow.scheduler.job import JobType, ScheduledJob

        env = {"PATH": "/usr/bin", "USER": "testuser"}
        notifications = {"email": "test@example.com"}

        job = ScheduledJob(
            name="full_job",
            cron_expression="0 0 * * *",
            job_type=JobType.PYTHON,
            command="python script.py",
            description="Full test job",
            enabled=False,
            max_runtime=7200,
            retry_count=3,
            retry_delay=120,
            environment=env,
            working_directory="/tmp",
            output_format="text",
            notifications=notifications,
            job_id="custom-id-123",
        )

        assert job.id == "custom-id-123"
        assert job.name == "full_job"
        assert job.description == "Full test job"
        assert job.enabled is False
        assert job.max_runtime == 7200
        assert job.retry_count == 3
        assert job.retry_delay == 120
        assert job.environment == env
        assert job.working_directory == "/tmp"
        assert job.output_format == "text"
        assert job.notifications == notifications

    def test_scheduled_job_auto_generates_id(self):
        """Test that job auto-generates UUID if not provided"""
        from mcli.workflow.scheduler.job import JobType, ScheduledJob

        job1 = ScheduledJob(
            name="job1", cron_expression="* * * * *", job_type=JobType.COMMAND, command="echo 1"
        )

        job2 = ScheduledJob(
            name="job2", cron_expression="* * * * *", job_type=JobType.COMMAND, command="echo 2"
        )

        assert job1.id != job2.id
        assert len(job1.id) == 36  # UUID format

    def test_scheduled_job_runtime_tracking_initialization(self):
        """Test that runtime tracking fields are initialized correctly"""
        from mcli.workflow.scheduler.job import JobStatus, JobType, ScheduledJob

        job = ScheduledJob(
            name="test", cron_expression="* * * * *", job_type=JobType.COMMAND, command="test"
        )

        assert job.status == JobStatus.PENDING
        assert isinstance(job.created_at, datetime)
        assert job.last_run is None
        assert job.next_run is None
        assert job.run_count == 0
        assert job.success_count == 0
        assert job.failure_count == 0
        assert job.last_output == ""
        assert job.last_error == ""
        assert job.runtime_seconds == 0
        assert job.current_retry == 0

    def test_to_dict_serialization(self):
        """Test job serialization to dictionary"""
        from mcli.workflow.scheduler.job import JobType, ScheduledJob

        job = ScheduledJob(
            name="serialize_test",
            cron_expression="0 0 * * *",
            job_type=JobType.COMMAND,
            command="test command",
            description="Test job",
            job_id="test-id-123",
        )

        job_dict = job.to_dict()

        assert job_dict["id"] == "test-id-123"
        assert job_dict["name"] == "serialize_test"
        assert job_dict["cron_expression"] == "0 0 * * *"
        assert job_dict["job_type"] == "command"
        assert job_dict["command"] == "test command"
        assert job_dict["description"] == "Test job"
        assert job_dict["enabled"] is True
        assert job_dict["status"] == "pending"
        assert "created_at" in job_dict
        assert job_dict["last_run"] is None
        assert job_dict["next_run"] is None

    def test_from_dict_deserialization(self):
        """Test job deserialization from dictionary"""
        from mcli.workflow.scheduler.job import JobStatus, JobType, ScheduledJob

        data = {
            "id": "test-id-456",
            "name": "deserialize_test",
            "cron_expression": "0 12 * * *",
            "job_type": "python",
            "command": "python test.py",
            "description": "Deserialization test",
            "enabled": False,
            "max_runtime": 1800,
            "retry_count": 2,
            "retry_delay": 90,
            "environment": {"KEY": "value"},
            "working_directory": "/opt",
            "output_format": "text",
            "notifications": {"slack": "#channel"},
            "status": "completed",
            "created_at": "2025-01-01T00:00:00",
            "last_run": "2025-01-02T12:00:00",
            "next_run": "2025-01-03T12:00:00",
            "run_count": 5,
            "success_count": 4,
            "failure_count": 1,
            "last_output": "Success",
            "last_error": "",
            "runtime_seconds": 45,
            "current_retry": 0,
        }

        job = ScheduledJob.from_dict(data)

        assert job.id == "test-id-456"
        assert job.name == "deserialize_test"
        assert job.cron_expression == "0 12 * * *"
        assert job.job_type == JobType.PYTHON
        assert job.command == "python test.py"
        assert job.description == "Deserialization test"
        assert job.enabled is False
        assert job.max_runtime == 1800
        assert job.retry_count == 2
        assert job.retry_delay == 90
        assert job.environment == {"KEY": "value"}
        assert job.working_directory == "/opt"
        assert job.output_format == "text"
        assert job.notifications == {"slack": "#channel"}
        assert job.status == JobStatus.COMPLETED
        assert isinstance(job.created_at, datetime)
        assert isinstance(job.last_run, datetime)
        assert isinstance(job.next_run, datetime)
        assert job.run_count == 5
        assert job.success_count == 4
        assert job.failure_count == 1

    def test_from_dict_minimal_data(self):
        """Test deserialization with minimal required fields"""
        from mcli.workflow.scheduler.job import ScheduledJob

        data = {
            "name": "minimal_job",
            "cron_expression": "* * * * *",
            "job_type": "command",
            "command": "echo test",
            "created_at": datetime.now().isoformat(),
        }

        job = ScheduledJob.from_dict(data)

        assert job.name == "minimal_job"
        assert job.description == ""
        assert job.enabled is True
        assert job.max_runtime == 3600
        assert job.retry_count == 0

    def test_update_status_to_running(self):
        """Test updating job status to RUNNING"""
        from mcli.workflow.scheduler.job import JobStatus, JobType, ScheduledJob

        job = ScheduledJob(
            name="test", cron_expression="* * * * *", job_type=JobType.COMMAND, command="test"
        )

        initial_run_count = job.run_count

        job.update_status(JobStatus.RUNNING, output="Starting job")

        assert job.status == JobStatus.RUNNING
        assert job.last_output == "Starting job"
        assert job.run_count == initial_run_count + 1
        assert isinstance(job.last_run, datetime)

    def test_update_status_to_completed(self):
        """Test updating job status to COMPLETED"""
        from mcli.workflow.scheduler.job import JobStatus, JobType, ScheduledJob

        job = ScheduledJob(
            name="test", cron_expression="* * * * *", job_type=JobType.COMMAND, command="test"
        )

        job.current_retry = 2
        initial_success_count = job.success_count

        job.update_status(JobStatus.COMPLETED, output="Job completed successfully")

        assert job.status == JobStatus.COMPLETED
        assert job.last_output == "Job completed successfully"
        assert job.success_count == initial_success_count + 1
        assert job.current_retry == 0  # Reset on success

    def test_update_status_to_failed(self):
        """Test updating job status to FAILED"""
        from mcli.workflow.scheduler.job import JobStatus, JobType, ScheduledJob

        job = ScheduledJob(
            name="test", cron_expression="* * * * *", job_type=JobType.COMMAND, command="test"
        )

        initial_failure_count = job.failure_count

        job.update_status(JobStatus.FAILED, error="Job failed with error")

        assert job.status == JobStatus.FAILED
        assert job.last_error == "Job failed with error"
        assert job.failure_count == initial_failure_count + 1

    def test_should_retry_when_retry_available(self):
        """Test should_retry returns True when retries available"""
        from mcli.workflow.scheduler.job import JobStatus, JobType, ScheduledJob

        job = ScheduledJob(
            name="test",
            cron_expression="* * * * *",
            job_type=JobType.COMMAND,
            command="test",
            retry_count=3,
        )

        job.status = JobStatus.FAILED
        job.current_retry = 1

        assert job.should_retry() is True

    def test_should_retry_when_max_retries_reached(self):
        """Test should_retry returns False when max retries reached"""
        from mcli.workflow.scheduler.job import JobStatus, JobType, ScheduledJob

        job = ScheduledJob(
            name="test",
            cron_expression="* * * * *",
            job_type=JobType.COMMAND,
            command="test",
            retry_count=3,
        )

        job.status = JobStatus.FAILED
        job.current_retry = 3

        assert job.should_retry() is False

    def test_should_retry_when_not_failed(self):
        """Test should_retry returns False when job not failed"""
        from mcli.workflow.scheduler.job import JobStatus, JobType, ScheduledJob

        job = ScheduledJob(
            name="test",
            cron_expression="* * * * *",
            job_type=JobType.COMMAND,
            command="test",
            retry_count=3,
        )

        job.status = JobStatus.COMPLETED
        job.current_retry = 1

        assert job.should_retry() is False

    def test_get_next_retry_time(self):
        """Test calculation of next retry time"""
        from mcli.workflow.scheduler.job import JobType, ScheduledJob

        job = ScheduledJob(
            name="test",
            cron_expression="* * * * *",
            job_type=JobType.COMMAND,
            command="test",
            retry_delay=120,
        )

        before = datetime.now()
        retry_time = job.get_next_retry_time()
        after = datetime.now()

        # Retry time should be approximately 120 seconds from now
        expected_min = before + timedelta(seconds=120)
        expected_max = after + timedelta(seconds=120)

        assert expected_min <= retry_time <= expected_max

    def test_to_json_serialization(self):
        """Test JSON string serialization"""
        from mcli.workflow.scheduler.job import JobType, ScheduledJob

        job = ScheduledJob(
            name="json_test",
            cron_expression="0 0 * * *",
            job_type=JobType.COMMAND,
            command="test",
            job_id="json-test-id",
        )

        json_str = job.to_json()

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed["id"] == "json-test-id"
        assert parsed["name"] == "json_test"
        assert parsed["job_type"] == "command"

    def test_str_representation(self):
        """Test string representation of job"""
        from mcli.workflow.scheduler.job import JobStatus, JobType, ScheduledJob

        job = ScheduledJob(
            name="test_job",
            cron_expression="* * * * *",
            job_type=JobType.COMMAND,
            command="test",
            job_id="12345678-1234-1234-1234-123456789012",
        )

        str_repr = str(job)

        assert "Job" in str_repr
        assert "12345678" in str_repr  # First 8 chars of ID
        assert "test_job" in str_repr
        assert "pending" in str_repr

    def test_repr_representation(self):
        """Test repr representation of job"""
        from mcli.workflow.scheduler.job import JobType, ScheduledJob

        job = ScheduledJob(
            name="repr_test",
            cron_expression="0 12 * * *",
            job_type=JobType.COMMAND,
            command="test",
            job_id="test-id",
        )

        repr_str = repr(job)

        assert "ScheduledJob" in repr_str
        assert "test-id" in repr_str
        assert "repr_test" in repr_str
        assert "0 12 * * *" in repr_str

    def test_round_trip_serialization(self):
        """Test serialization and deserialization preserves data"""
        from mcli.workflow.scheduler.job import JobType, ScheduledJob

        original = ScheduledJob(
            name="round_trip",
            cron_expression="0 0 * * *",
            job_type=JobType.PYTHON,
            command="python script.py",
            description="Round trip test",
            enabled=False,
            max_runtime=1800,
            retry_count=2,
            retry_delay=90,
            environment={"TEST": "value"},
            working_directory="/test",
            output_format="text",
            notifications={"email": "test@test.com"},
        )

        # Serialize and deserialize
        data = original.to_dict()
        restored = ScheduledJob.from_dict(data)

        # Verify all important fields match
        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.cron_expression == original.cron_expression
        assert restored.job_type == original.job_type
        assert restored.command == original.command
        assert restored.description == original.description
        assert restored.enabled == original.enabled
        assert restored.max_runtime == original.max_runtime
        assert restored.retry_count == original.retry_count
        assert restored.retry_delay == original.retry_delay
        assert restored.environment == original.environment
        assert restored.working_directory == original.working_directory
        assert restored.output_format == original.output_format
        assert restored.notifications == original.notifications

    def test_job_type_conversion_in_serialization(self):
        """Test JobType enum is properly converted in serialization"""
        from mcli.workflow.scheduler.job import JobType, ScheduledJob

        for job_type in JobType:
            job = ScheduledJob(
                name=f"test_{job_type.value}",
                cron_expression="* * * * *",
                job_type=job_type,
                command="test",
            )

            job_dict = job.to_dict()
            assert job_dict["job_type"] == job_type.value

            restored = ScheduledJob.from_dict(job_dict)
            assert restored.job_type == job_type

    def test_status_conversion_in_serialization(self):
        """Test JobStatus enum is properly converted in serialization"""
        from mcli.workflow.scheduler.job import JobStatus, JobType, ScheduledJob

        job = ScheduledJob(
            name="test", cron_expression="* * * * *", job_type=JobType.COMMAND, command="test"
        )

        for status in JobStatus:
            job.status = status
            job_dict = job.to_dict()
            assert job_dict["status"] == status.value

            restored = ScheduledJob.from_dict(job_dict)
            assert restored.status == status
