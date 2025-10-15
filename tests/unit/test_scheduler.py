"""
Unit tests for mcli.workflow.scheduler.scheduler module
"""

import subprocess
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

import pytest

from mcli.workflow.scheduler.job import JobStatus, JobType, ScheduledJob
from mcli.workflow.scheduler.scheduler import JobExecutor, JobScheduler


class TestJobExecutor:
    """Test suite for JobExecutor"""

    def setup_method(self):
        """Setup test environment"""
        self.executor = JobExecutor()

    def test_executor_initialization(self):
        """Test executor initializes correctly"""
        assert self.executor.running_processes == {}
        assert self.executor.lock is not None

    @patch("subprocess.Popen")
    def test_execute_command_success(self, mock_popen):
        """Test successful command execution"""
        # Mock subprocess
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("output", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        job = ScheduledJob(
            name="test_job",
            cron_expression="* * * * *",
            job_type=JobType.COMMAND,
            command="echo 'test'",
        )

        result = self.executor.execute_job(job)

        assert result["status"] == JobStatus.COMPLETED.value
        assert result["exit_code"] == 0
        assert result["job_id"] == job.id
        assert "runtime_seconds" in result

    @patch("subprocess.Popen")
    def test_execute_command_failure(self, mock_popen):
        """Test command execution failure"""
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("", "error output")
        mock_process.returncode = 1
        mock_popen.return_value = mock_process

        job = ScheduledJob(
            name="failing_job",
            cron_expression="* * * * *",
            job_type=JobType.COMMAND,
            command="false",
        )

        result = self.executor.execute_job(job)

        assert result["status"] == JobStatus.FAILED.value
        assert result["exit_code"] == 1

    @patch("subprocess.Popen")
    def test_execute_command_with_timeout(self, mock_popen):
        """Test command execution with timeout"""
        mock_process = MagicMock()
        mock_process.communicate.side_effect = subprocess.TimeoutExpired("cmd", 5)
        mock_popen.return_value = mock_process

        job = ScheduledJob(
            name="timeout_job",
            cron_expression="* * * * *",
            job_type=JobType.COMMAND,
            command="sleep 100",
            max_runtime=5,
        )

        result = self.executor.execute_job(job)

        assert result["status"] == JobStatus.FAILED.value
        assert "timed out" in result["error"].lower()
        mock_process.kill.assert_called_once()

    @patch("subprocess.Popen")
    def test_execute_command_with_environment(self, mock_popen):
        """Test command execution with custom environment"""
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        job = ScheduledJob(
            name="env_job",
            cron_expression="* * * * *",
            job_type=JobType.COMMAND,
            command="echo $TEST_VAR",
            environment={"TEST_VAR": "test_value"},
        )

        self.executor.execute_job(job)

        # Verify environment was passed
        call_args = mock_popen.call_args
        env = call_args[1]["env"]
        assert "TEST_VAR" in env
        assert env["TEST_VAR"] == "test_value"

    @patch("subprocess.Popen")
    def test_execute_command_with_working_directory(self, mock_popen):
        """Test command execution with working directory"""
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        with tempfile.TemporaryDirectory() as tmpdir:
            job = ScheduledJob(
                name="cwd_job",
                cron_expression="* * * * *",
                job_type=JobType.COMMAND,
                command="pwd",
                working_directory=tmpdir,
            )

            self.executor.execute_job(job)

            # Verify working directory was set
            call_args = mock_popen.call_args
            assert call_args[1]["cwd"] == tmpdir

    @patch("builtins.exec")
    def test_execute_python_code(self, mock_exec):
        """Test Python code execution"""
        job = ScheduledJob(
            name="python_job",
            cron_expression="* * * * *",
            job_type=JobType.PYTHON,
            command="print('hello')",
        )

        result = self.executor.execute_job(job)

        # Should attempt to execute Python code
        assert result["job_id"] == job.id
        assert "runtime_seconds" in result

    @patch("requests.request")
    def test_execute_api_call_success(self, mock_request):
        """Test API call execution"""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.text = '{"result": "success"}'
        mock_response.headers = {"Content-Type": "application/json"}
        mock_request.return_value = mock_response

        job = ScheduledJob(
            name="api_job",
            cron_expression="* * * * *",
            job_type=JobType.API_CALL,
            command='{"url": "https://api.example.com/test", "method": "GET"}',
        )

        result = self.executor.execute_job(job)

        assert result["status"] == JobStatus.COMPLETED.value
        assert result["exit_code"] == 0
        mock_request.assert_called_once()

    @patch("requests.request")
    def test_execute_api_call_failure(self, mock_request):
        """Test API call execution failure"""
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_response.headers = {}
        mock_request.return_value = mock_response

        job = ScheduledJob(
            name="api_fail_job",
            cron_expression="* * * * *",
            job_type=JobType.API_CALL,
            command='{"url": "https://api.example.com/notfound"}',
        )

        result = self.executor.execute_job(job)

        assert result["exit_code"] == 1

    def test_execute_job_updates_status(self):
        """Test that execute_job updates job status correctly"""
        with patch("subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.communicate.return_value = ("success", "")
            mock_process.returncode = 0
            mock_popen.return_value = mock_process

            job = ScheduledJob(
                name="status_test",
                cron_expression="* * * * *",
                job_type=JobType.COMMAND,
                command="echo test",
            )

            initial_status = job.status
            result = self.executor.execute_job(job)

            # Job should transition from PENDING -> RUNNING -> COMPLETED
            assert job.status == JobStatus.COMPLETED
            assert job.success_count > 0

    def test_execute_job_handles_exception(self):
        """Test that execute_job handles exceptions gracefully"""
        job = ScheduledJob(
            name="exception_test",
            cron_expression="* * * * *",
            job_type=JobType.COMMAND,
            command="echo test",
        )

        with patch("subprocess.Popen", side_effect=Exception("Test error")):
            result = self.executor.execute_job(job)

            assert result["status"] == JobStatus.FAILED.value
            assert "Test error" in result["error"]
            assert result["exit_code"] == -1


class TestJobScheduler:
    """Test suite for JobScheduler"""

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.scheduler = JobScheduler(storage_dir=self.temp_dir)

    def teardown_method(self):
        """Cleanup test environment"""
        if self.scheduler.running:
            self.scheduler.stop()
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_scheduler_initialization(self):
        """Test scheduler initializes correctly"""
        assert self.scheduler.storage is not None
        assert self.scheduler.monitor is not None
        assert self.scheduler.executor is not None
        assert self.scheduler.jobs == {}
        assert not self.scheduler.running

    def test_add_job(self):
        """Test adding a job"""
        job = ScheduledJob(
            name="test_job",
            cron_expression="0 * * * *",
            job_type=JobType.COMMAND,
            command="echo test",
        )

        self.scheduler.add_job(job)

        assert job.id in self.scheduler.jobs
        assert self.scheduler.jobs[job.id] == job

    def test_add_multiple_jobs_with_same_name(self):
        """Test adding multiple jobs with the same name"""
        job1 = ScheduledJob(
            name="duplicate",
            cron_expression="0 * * * *",
            job_type=JobType.COMMAND,
            command="echo test",
        )

        job2 = ScheduledJob(
            name="duplicate",
            cron_expression="0 * * * *",
            job_type=JobType.COMMAND,
            command="echo test2",
        )

        self.scheduler.add_job(job1)
        self.scheduler.add_job(job2)

        # Scheduler allows multiple jobs with same name (different IDs)
        jobs_with_name = [j for j in self.scheduler.jobs.values() if j.name == "duplicate"]
        assert len(jobs_with_name) == 2

    def test_remove_job(self):
        """Test removing a job"""
        job = ScheduledJob(
            name="removable",
            cron_expression="0 * * * *",
            job_type=JobType.COMMAND,
            command="echo test",
        )

        self.scheduler.add_job(job)
        assert job.id in self.scheduler.jobs

        self.scheduler.remove_job(job.id)
        assert job.id not in self.scheduler.jobs

    def test_remove_nonexistent_job(self):
        """Test removing a job that doesn't exist"""
        # Should not raise an error
        self.scheduler.remove_job("nonexistent-id")

    def test_get_job(self):
        """Test getting a job by ID"""
        job = ScheduledJob(
            name="getable",
            cron_expression="0 * * * *",
            job_type=JobType.COMMAND,
            command="echo test",
        )

        self.scheduler.add_job(job)
        retrieved = self.scheduler.get_job(job.id)

        assert retrieved == job

    def test_get_nonexistent_job(self):
        """Test getting a job that doesn't exist"""
        result = self.scheduler.get_job("nonexistent")
        assert result is None

    def test_list_jobs(self):
        """Test listing all jobs"""
        job1 = ScheduledJob(
            name="job1", cron_expression="0 * * * *", job_type=JobType.COMMAND, command="echo 1"
        )

        job2 = ScheduledJob(
            name="job2", cron_expression="0 0 * * *", job_type=JobType.COMMAND, command="echo 2"
        )

        self.scheduler.add_job(job1)
        self.scheduler.add_job(job2)

        jobs = list(self.scheduler.jobs.values())

        assert len(jobs) == 2
        assert job1 in jobs
        assert job2 in jobs

    def test_scheduler_persistence(self):
        """Test that jobs are persisted to storage"""
        job = ScheduledJob(
            name="persistent",
            cron_expression="0 * * * *",
            job_type=JobType.COMMAND,
            command="echo test",
        )

        self.scheduler.add_job(job)

        # Create new scheduler with same storage dir
        new_scheduler = JobScheduler(storage_dir=self.temp_dir)

        # Should load the job
        assert job.id in new_scheduler.jobs

    def test_start_scheduler(self):
        """Test starting the scheduler"""
        assert not self.scheduler.running

        with patch.object(self.scheduler.monitor, "start_monitoring"):
            with patch("threading.Thread"):
                self.scheduler.start()

        assert self.scheduler.running

    def test_start_already_running(self):
        """Test starting scheduler when already running"""
        self.scheduler.running = True

        with patch.object(self.scheduler.monitor, "start_monitoring") as mock_start:
            self.scheduler.start()

            # Should not start monitoring again
            mock_start.assert_not_called()

    def test_stop_scheduler(self):
        """Test stopping the scheduler"""
        self.scheduler.running = True

        with patch.object(self.scheduler.monitor, "stop_monitoring"):
            self.scheduler.stop()

        assert not self.scheduler.running

    def test_get_job_status(self):
        """Test getting job status"""
        job = ScheduledJob(
            name="status_job",
            cron_expression="0 * * * *",
            job_type=JobType.COMMAND,
            command="echo test",
        )

        self.scheduler.add_job(job)
        status = self.scheduler.get_job_status(job.id)

        assert status is not None
        assert "job" in status
        assert status["job"]["name"] == "status_job"
        assert "is_running" in status
        assert "runtime" in status
        assert "history" in status

    def test_get_status_nonexistent_job(self):
        """Test getting status of nonexistent job"""
        status = self.scheduler.get_job_status("nonexistent")
        assert status is None

    def test_scheduler_cleanup(self):
        """Test scheduler cleanup on stop"""
        job = ScheduledJob(
            name="cleanup_test",
            cron_expression="0 * * * *",
            job_type=JobType.COMMAND,
            command="echo test",
        )

        self.scheduler.add_job(job)
        self.scheduler.start()

        # Verify it's running
        assert self.scheduler.running

        # Stop and verify cleanup
        self.scheduler.stop()
        assert not self.scheduler.running
