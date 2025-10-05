"""
Integration tests for mcli.workflow.scheduler.scheduler module
"""

import pytest
import tempfile
import time
import threading
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock, call


class TestJobExecutor:
    """Test suite for JobExecutor class"""

    def test_job_executor_init(self):
        """Test JobExecutor initialization"""
        from mcli.workflow.scheduler.scheduler import JobExecutor

        executor = JobExecutor()

        assert executor.running_processes == {}
        assert executor.lock is not None

    @patch('mcli.workflow.scheduler.scheduler.subprocess.Popen')
    def test_execute_command_job_success(self, mock_popen):
        """Test executing a command job successfully"""
        from mcli.workflow.scheduler.scheduler import JobExecutor
        from mcli.workflow.scheduler.job import ScheduledJob, JobType, JobStatus

        # Mock subprocess
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("output text", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        executor = JobExecutor()

        job = ScheduledJob(
            name="test_command",
            cron_expression="0 0 * * *",
            job_type=JobType.COMMAND,
            command="echo test"
        )

        result = executor.execute_job(job)

        assert result["status"] == JobStatus.COMPLETED.value
        assert result["exit_code"] == 0
        assert "output" in result
        assert job.status == JobStatus.COMPLETED

    @patch('mcli.workflow.scheduler.scheduler.subprocess.Popen')
    def test_execute_command_job_failure(self, mock_popen):
        """Test executing a command job that fails"""
        from mcli.workflow.scheduler.scheduler import JobExecutor
        from mcli.workflow.scheduler.job import ScheduledJob, JobType, JobStatus

        # Mock subprocess failure
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("", "error message")
        mock_process.returncode = 1
        mock_popen.return_value = mock_process

        executor = JobExecutor()

        job = ScheduledJob(
            name="failing_job",
            cron_expression="0 0 * * *",
            job_type=JobType.COMMAND,
            command="exit 1"
        )

        result = executor.execute_job(job)

        assert result["status"] == JobStatus.FAILED.value
        assert result["exit_code"] == 1
        assert job.status == JobStatus.FAILED

    @patch('mcli.workflow.scheduler.scheduler.subprocess.Popen')
    def test_execute_command_with_timeout(self, mock_popen):
        """Test command execution with timeout"""
        from mcli.workflow.scheduler.scheduler import JobExecutor
        from mcli.workflow.scheduler.job import ScheduledJob, JobType, JobStatus
        import subprocess

        # Mock subprocess timeout
        mock_process = MagicMock()
        mock_process.communicate.side_effect = subprocess.TimeoutExpired("cmd", 5)
        mock_popen.return_value = mock_process

        executor = JobExecutor()

        job = ScheduledJob(
            name="timeout_job",
            cron_expression="0 0 * * *",
            job_type=JobType.COMMAND,
            command="sleep 100",
            max_runtime=5
        )

        result = executor.execute_job(job)

        assert result["status"] == JobStatus.FAILED.value
        assert "timed out" in result["error"].lower()
        mock_process.kill.assert_called_once()


class TestJobScheduler:
    """Test suite for JobScheduler class"""

    def test_job_scheduler_init(self):
        """Test JobScheduler initialization"""
        from mcli.workflow.scheduler.scheduler import JobScheduler

        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = JobScheduler(storage_dir=tmpdir)

            assert scheduler.storage is not None
            assert scheduler.monitor is not None
            assert scheduler.executor is not None
            assert scheduler.jobs == {}
            assert scheduler.running is False
            assert scheduler.scheduler_thread is None

    def test_add_job_to_scheduler(self):
        """Test adding a job to scheduler"""
        from mcli.workflow.scheduler.scheduler import JobScheduler
        from mcli.workflow.scheduler.job import ScheduledJob, JobType

        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = JobScheduler(storage_dir=tmpdir)

            job = ScheduledJob(
                name="test_job",
                cron_expression="0 0 * * *",
                job_type=JobType.COMMAND,
                command="echo test"
            )

            result = scheduler.add_job(job)

            assert result is True
            assert job.id in scheduler.jobs
            assert scheduler.jobs[job.id].name == "test_job"

    def test_remove_job_from_scheduler(self):
        """Test removing a job from scheduler"""
        from mcli.workflow.scheduler.scheduler import JobScheduler
        from mcli.workflow.scheduler.job import ScheduledJob, JobType

        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = JobScheduler(storage_dir=tmpdir)

            job = ScheduledJob(
                name="test_job",
                cron_expression="0 0 * * *",
                job_type=JobType.COMMAND,
                command="echo test"
            )

            scheduler.add_job(job)
            result = scheduler.remove_job(job.id)

            assert result is True
            assert job.id not in scheduler.jobs

    def test_remove_nonexistent_job(self):
        """Test removing a job that doesn't exist"""
        from mcli.workflow.scheduler.scheduler import JobScheduler

        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = JobScheduler(storage_dir=tmpdir)

            result = scheduler.remove_job("nonexistent-id")

            assert result is False

    def test_get_job_by_id(self):
        """Test getting a job by ID"""
        from mcli.workflow.scheduler.scheduler import JobScheduler
        from mcli.workflow.scheduler.job import ScheduledJob, JobType

        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = JobScheduler(storage_dir=tmpdir)

            job = ScheduledJob(
                name="test_job",
                cron_expression="0 0 * * *",
                job_type=JobType.COMMAND,
                command="echo test"
            )

            scheduler.add_job(job)
            retrieved_job = scheduler.get_job(job.id)

            assert retrieved_job is not None
            assert retrieved_job.id == job.id
            assert retrieved_job.name == "test_job"

    def test_get_all_jobs(self):
        """Test getting all jobs"""
        from mcli.workflow.scheduler.scheduler import JobScheduler
        from mcli.workflow.scheduler.job import ScheduledJob, JobType

        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = JobScheduler(storage_dir=tmpdir)

            job1 = ScheduledJob(
                name="job1",
                cron_expression="0 0 * * *",
                job_type=JobType.COMMAND,
                command="echo 1"
            )

            job2 = ScheduledJob(
                name="job2",
                cron_expression="0 12 * * *",
                job_type=JobType.COMMAND,
                command="echo 2"
            )

            scheduler.add_job(job1)
            scheduler.add_job(job2)

            all_jobs = scheduler.get_all_jobs()

            assert len(all_jobs) == 2
            assert any(j.name == "job1" for j in all_jobs)
            assert any(j.name == "job2" for j in all_jobs)

    def test_get_job_status(self):
        """Test getting job status"""
        from mcli.workflow.scheduler.scheduler import JobScheduler
        from mcli.workflow.scheduler.job import ScheduledJob, JobType

        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = JobScheduler(storage_dir=tmpdir)

            job = ScheduledJob(
                name="test_job",
                cron_expression="0 0 * * *",
                job_type=JobType.COMMAND,
                command="echo test"
            )

            scheduler.add_job(job)
            status = scheduler.get_job_status(job.id)

            assert status is not None
            assert "job" in status
            assert "is_running" in status
            assert "runtime" in status
            assert "history" in status
            assert status["job"]["name"] == "test_job"

    def test_get_job_status_nonexistent(self):
        """Test getting status for nonexistent job returns None"""
        from mcli.workflow.scheduler.scheduler import JobScheduler

        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = JobScheduler(storage_dir=tmpdir)

            status = scheduler.get_job_status("nonexistent-id")

            assert status is None

    def test_get_scheduler_stats(self):
        """Test getting scheduler statistics"""
        from mcli.workflow.scheduler.scheduler import JobScheduler
        from mcli.workflow.scheduler.job import ScheduledJob, JobType

        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = JobScheduler(storage_dir=tmpdir)

            job = ScheduledJob(
                name="test_job",
                cron_expression="0 0 * * *",
                job_type=JobType.COMMAND,
                command="echo test",
                enabled=True
            )

            scheduler.add_job(job)
            stats = scheduler.get_scheduler_stats()

            assert "running" in stats
            assert "total_jobs" in stats
            assert "enabled_jobs" in stats
            assert "running_jobs" in stats
            assert "monitor_stats" in stats
            assert "storage_info" in stats
            assert stats["total_jobs"] == 1
            assert stats["enabled_jobs"] == 1

    def test_start_scheduler(self):
        """Test starting the scheduler"""
        from mcli.workflow.scheduler.scheduler import JobScheduler

        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = JobScheduler(storage_dir=tmpdir)

            scheduler.start()

            assert scheduler.running is True
            assert scheduler.scheduler_thread is not None
            assert scheduler.scheduler_thread.is_alive()

            # Cleanup
            scheduler.stop()

    def test_stop_scheduler(self):
        """Test stopping the scheduler"""
        from mcli.workflow.scheduler.scheduler import JobScheduler

        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = JobScheduler(storage_dir=tmpdir)

            scheduler.start()
            time.sleep(0.2)  # Let it start

            scheduler.stop()

            assert scheduler.running is False

    def test_start_scheduler_idempotent(self):
        """Test that starting scheduler multiple times is safe"""
        from mcli.workflow.scheduler.scheduler import JobScheduler

        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = JobScheduler(storage_dir=tmpdir)

            scheduler.start()
            first_thread = scheduler.scheduler_thread

            # Try starting again
            scheduler.start()
            second_thread = scheduler.scheduler_thread

            # Should be the same thread
            assert first_thread == second_thread

            # Cleanup
            scheduler.stop()

    def test_jobs_persist_across_restart(self):
        """Test that jobs persist when scheduler restarts"""
        from mcli.workflow.scheduler.scheduler import JobScheduler
        from mcli.workflow.scheduler.job import ScheduledJob, JobType

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create scheduler and add job
            scheduler1 = JobScheduler(storage_dir=tmpdir)

            job = ScheduledJob(
                name="persistent_job",
                cron_expression="0 0 * * *",
                job_type=JobType.COMMAND,
                command="echo test"
            )

            scheduler1.add_job(job)
            job_id = job.id

            # Create new scheduler instance with same storage
            scheduler2 = JobScheduler(storage_dir=tmpdir)

            # Job should be loaded
            assert job_id in scheduler2.jobs
            assert scheduler2.jobs[job_id].name == "persistent_job"

    def test_create_json_response(self):
        """Test creating JSON response for frontend"""
        from mcli.workflow.scheduler.scheduler import JobScheduler
        from mcli.workflow.scheduler.job import ScheduledJob, JobType

        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = JobScheduler(storage_dir=tmpdir)

            job = ScheduledJob(
                name="test_job",
                cron_expression="0 0 * * *",
                job_type=JobType.COMMAND,
                command="echo test"
            )

            scheduler.add_job(job)
            response = scheduler.create_json_response()

            assert "timestamp" in response
            assert "scheduler" in response
            assert "jobs" in response
            assert len(response["jobs"]) == 1
            assert response["jobs"][0]["name"] == "test_job"
            assert "is_running" in response["jobs"][0]

    def test_update_next_run_times(self):
        """Test that next run times are updated"""
        from mcli.workflow.scheduler.scheduler import JobScheduler
        from mcli.workflow.scheduler.job import ScheduledJob, JobType

        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = JobScheduler(storage_dir=tmpdir)

            job = ScheduledJob(
                name="test_job",
                cron_expression="0 0 * * *",
                job_type=JobType.COMMAND,
                command="echo test"
            )

            # Initially next_run is None
            assert job.next_run is None

            scheduler.add_job(job)

            # After adding, next_run should be set
            assert job.next_run is not None
            assert isinstance(job.next_run, datetime)


class TestConvenienceFunctions:
    """Test suite for convenience job creation functions"""

    def test_create_desktop_cleanup_job(self):
        """Test creating desktop cleanup job"""
        from mcli.workflow.scheduler.scheduler import create_desktop_cleanup_job
        from mcli.workflow.scheduler.job import JobType

        job = create_desktop_cleanup_job()

        assert job.name == "Desktop Cleanup"
        assert job.job_type == JobType.CLEANUP
        assert job.enabled is True
        assert "organize_desktop" in job.command

    def test_create_desktop_cleanup_job_custom(self):
        """Test creating desktop cleanup job with custom params"""
        from mcli.workflow.scheduler.scheduler import create_desktop_cleanup_job

        job = create_desktop_cleanup_job(
            name="My Cleanup",
            cron_expression="0 10 * * *",
            enabled=False
        )

        assert job.name == "My Cleanup"
        assert job.cron_expression == "0 10 * * *"
        assert job.enabled is False

    def test_create_temp_cleanup_job(self):
        """Test creating temp file cleanup job"""
        from mcli.workflow.scheduler.scheduler import create_temp_cleanup_job
        from mcli.workflow.scheduler.job import JobType

        job = create_temp_cleanup_job()

        assert job.name == "Temp File Cleanup"
        assert job.job_type == JobType.CLEANUP
        assert "delete_old_files" in job.command
        assert "/tmp" in job.command

    def test_create_temp_cleanup_job_custom_path(self):
        """Test creating temp cleanup job with custom path"""
        from mcli.workflow.scheduler.scheduler import create_temp_cleanup_job

        job = create_temp_cleanup_job(
            temp_path="/var/tmp",
            days=14
        )

        assert "/var/tmp" in job.command
        assert "14" in job.command

    def test_create_system_backup_job(self):
        """Test creating system backup job"""
        from mcli.workflow.scheduler.scheduler import create_system_backup_job
        from mcli.workflow.scheduler.job import JobType

        job = create_system_backup_job()

        assert job.name == "System Backup"
        assert job.job_type == JobType.SYSTEM
        assert job.max_runtime == 7200

    def test_create_system_backup_job_custom_command(self):
        """Test creating system backup job with custom command"""
        from mcli.workflow.scheduler.scheduler import create_system_backup_job

        job = create_system_backup_job(
            backup_command="tar -czf /backup/backup.tar.gz /data"
        )

        assert "tar" in job.command
        assert "/backup/backup.tar.gz" in job.command
