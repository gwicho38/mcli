"""
Unit tests for mcli.workflow.scheduler.monitor module
"""

import threading
import time
from datetime import datetime
from unittest.mock import MagicMock, call, patch

import pytest


class TestJobMonitor:
    """Test suite for JobMonitor class"""

    def setup_method(self):
        """Setup test environment"""
        # Import here to avoid issues if module doesn't exist
        from mcli.workflow.scheduler.monitor import JobMonitor

        self.JobMonitor = JobMonitor

    def teardown_method(self):
        """Cleanup after each test"""
        # Make sure monitoring is stopped
        pass

    def test_job_monitor_init_without_callback(self):
        """Test JobMonitor initialization without callback"""
        monitor = self.JobMonitor()

        assert monitor.running_jobs == {}
        assert monitor.job_start_times == {}
        assert monitor.status_callback is None
        assert monitor.monitor_thread is None
        assert monitor.monitoring is False
        assert monitor.lock is not None

    def test_job_monitor_init_with_callback(self):
        """Test JobMonitor initialization with callback"""
        callback = MagicMock()
        monitor = self.JobMonitor(status_callback=callback)

        assert monitor.status_callback == callback

    def test_start_monitoring_starts_thread(self):
        """Test that start_monitoring starts the monitor thread"""
        monitor = self.JobMonitor()

        monitor.start_monitoring()

        assert monitor.monitoring is True
        assert monitor.monitor_thread is not None
        assert monitor.monitor_thread.is_alive()
        assert monitor.monitor_thread.daemon is True

        # Cleanup
        monitor.stop_monitoring()

    def test_start_monitoring_idempotent(self):
        """Test that calling start_monitoring multiple times is safe"""
        monitor = self.JobMonitor()

        monitor.start_monitoring()
        first_thread = monitor.monitor_thread

        monitor.start_monitoring()
        second_thread = monitor.monitor_thread

        # Should be the same thread
        assert first_thread == second_thread

        # Cleanup
        monitor.stop_monitoring()

    def test_stop_monitoring_stops_thread(self):
        """Test that stop_monitoring stops the monitor thread"""
        monitor = self.JobMonitor()

        monitor.start_monitoring()
        assert monitor.monitoring is True

        monitor.stop_monitoring()

        assert monitor.monitoring is False
        # Thread should have stopped or be stopping
        time.sleep(0.2)  # Give thread time to finish

    def test_stop_monitoring_when_not_started(self):
        """Test that stop_monitoring works even if monitoring never started"""
        monitor = self.JobMonitor()

        # Should not raise exception
        monitor.stop_monitoring()

        assert monitor.monitoring is False

    def test_add_job_to_monitor(self):
        """Test adding a job to monitor"""
        from mcli.workflow.scheduler.job import JobType, ScheduledJob

        monitor = self.JobMonitor()

        job = ScheduledJob(
            name="test_job", cron_expression="* * * * *", job_type=JobType.COMMAND, command="test"
        )

        thread = threading.Thread(target=lambda: time.sleep(0.1))
        thread.start()

        monitor.add_job(job, thread)

        assert job.id in monitor.running_jobs
        assert job.id in monitor.job_start_times
        assert monitor.running_jobs[job.id] == thread
        assert isinstance(monitor.job_start_times[job.id], datetime)

        # Wait for thread to finish
        thread.join()

    def test_get_running_jobs_returns_job_ids(self):
        """Test get_running_jobs returns list of job IDs"""
        from mcli.workflow.scheduler.job import JobType, ScheduledJob

        monitor = self.JobMonitor()

        job1 = ScheduledJob(
            name="job1", cron_expression="* * * * *", job_type=JobType.COMMAND, command="test1"
        )

        job2 = ScheduledJob(
            name="job2", cron_expression="* * * * *", job_type=JobType.COMMAND, command="test2"
        )

        thread1 = threading.Thread(target=lambda: time.sleep(0.1))
        thread2 = threading.Thread(target=lambda: time.sleep(0.1))
        thread1.start()
        thread2.start()

        monitor.add_job(job1, thread1)
        monitor.add_job(job2, thread2)

        running_jobs = monitor.get_running_jobs()

        assert len(running_jobs) == 2
        assert job1.id in running_jobs
        assert job2.id in running_jobs

        # Cleanup
        thread1.join()
        thread2.join()

    def test_get_running_jobs_empty_list(self):
        """Test get_running_jobs returns empty list when no jobs"""
        monitor = self.JobMonitor()

        running_jobs = monitor.get_running_jobs()

        assert running_jobs == []

    def test_is_job_running_returns_true_for_running_job(self):
        """Test is_job_running returns True for running job"""
        from mcli.workflow.scheduler.job import JobType, ScheduledJob

        monitor = self.JobMonitor()

        job = ScheduledJob(
            name="test", cron_expression="* * * * *", job_type=JobType.COMMAND, command="test"
        )

        thread = threading.Thread(target=lambda: time.sleep(0.1))
        thread.start()

        monitor.add_job(job, thread)

        assert monitor.is_job_running(job.id) is True

        # Cleanup
        thread.join()

    def test_is_job_running_returns_false_for_unknown_job(self):
        """Test is_job_running returns False for unknown job"""
        monitor = self.JobMonitor()

        assert monitor.is_job_running("unknown-job-id") is False

    def test_get_job_runtime(self):
        """Test getting runtime for a running job"""
        from mcli.workflow.scheduler.job import JobType, ScheduledJob

        monitor = self.JobMonitor()

        job = ScheduledJob(
            name="test", cron_expression="* * * * *", job_type=JobType.COMMAND, command="test"
        )

        thread = threading.Thread(target=lambda: time.sleep(0.5))
        thread.start()

        monitor.add_job(job, thread)

        # Wait a bit
        time.sleep(0.2)

        runtime = monitor.get_job_runtime(job.id)

        assert runtime is not None
        assert runtime >= 0
        assert isinstance(runtime, int)

        # Cleanup
        thread.join()

    def test_get_job_runtime_returns_none_for_unknown_job(self):
        """Test get_job_runtime returns None for unknown job"""
        monitor = self.JobMonitor()

        runtime = monitor.get_job_runtime("unknown-job-id")

        assert runtime is None

    def test_kill_job_returns_false_for_alive_thread(self):
        """Test kill_job returns False for alive thread (Python limitation)"""
        from mcli.workflow.scheduler.job import JobType, ScheduledJob

        monitor = self.JobMonitor()

        job = ScheduledJob(
            name="test", cron_expression="* * * * *", job_type=JobType.COMMAND, command="test"
        )

        thread = threading.Thread(target=lambda: time.sleep(0.5))
        thread.start()

        monitor.add_job(job, thread)

        # Try to kill - should return False due to Python thread limitation
        result = monitor.kill_job(job.id)

        assert result is False

        # Cleanup
        thread.join()

    def test_kill_job_returns_true_for_unknown_job(self):
        """Test kill_job returns True for unknown job"""
        monitor = self.JobMonitor()

        result = monitor.kill_job("unknown-job-id")

        assert result is True

    def test_get_monitor_stats_basic(self):
        """Test get_monitor_stats returns basic statistics"""
        monitor = self.JobMonitor()

        stats = monitor.get_monitor_stats()

        assert "monitoring" in stats
        assert "running_jobs_count" in stats
        assert "running_job_ids" in stats
        assert "monitor_thread_alive" in stats
        assert "job_runtimes" in stats

        assert stats["monitoring"] is False
        assert stats["running_jobs_count"] == 0
        assert stats["running_job_ids"] == []
        assert stats["monitor_thread_alive"] is False
        assert stats["job_runtimes"] == {}

    def test_get_monitor_stats_with_running_jobs(self):
        """Test get_monitor_stats with running jobs"""
        from mcli.workflow.scheduler.job import JobType, ScheduledJob

        monitor = self.JobMonitor()
        monitor.start_monitoring()

        job = ScheduledJob(
            name="test", cron_expression="* * * * *", job_type=JobType.COMMAND, command="test"
        )

        thread = threading.Thread(target=lambda: time.sleep(0.5))
        thread.start()

        monitor.add_job(job, thread)

        # Wait a bit
        time.sleep(0.1)

        stats = monitor.get_monitor_stats()

        assert stats["monitoring"] is True
        assert stats["running_jobs_count"] == 1
        assert job.id in stats["running_job_ids"]
        assert stats["monitor_thread_alive"] is True
        assert job.id in stats["job_runtimes"]
        assert stats["job_runtimes"][job.id] >= 0

        # Cleanup
        monitor.stop_monitoring()
        thread.join()

    def test_remove_job_from_monitor(self):
        """Test _remove_job removes job from tracking"""
        from mcli.workflow.scheduler.job import JobType, ScheduledJob

        monitor = self.JobMonitor()

        job = ScheduledJob(
            name="test", cron_expression="* * * * *", job_type=JobType.COMMAND, command="test"
        )

        thread = threading.Thread(target=lambda: time.sleep(0.1))
        thread.start()

        monitor.add_job(job, thread)

        assert job.id in monitor.running_jobs

        monitor._remove_job(job.id)

        assert job.id not in monitor.running_jobs
        assert job.id not in monitor.job_start_times

        # Cleanup
        thread.join()

    def test_remove_job_nonexistent_job_no_error(self):
        """Test _remove_job doesn't error on nonexistent job"""
        monitor = self.JobMonitor()

        # Should not raise exception
        monitor._remove_job("nonexistent-id")

    def test_monitor_loop_removes_completed_jobs(self):
        """Test that monitor loop removes completed jobs"""
        from mcli.workflow.scheduler.job import JobType, ScheduledJob

        monitor = self.JobMonitor()

        job = ScheduledJob(
            name="test", cron_expression="* * * * *", job_type=JobType.COMMAND, command="test"
        )

        # Create a short-running thread
        thread = threading.Thread(target=lambda: time.sleep(0.05))
        thread.start()

        monitor.add_job(job, thread)

        assert job.id in monitor.running_jobs

        # Wait for thread to complete
        thread.join()

        # Manually trigger check (instead of waiting for monitor loop)
        monitor._check_running_jobs()

        # Job should be removed
        assert job.id not in monitor.running_jobs

    def test_check_running_jobs_with_multiple_jobs(self):
        """Test _check_running_jobs with multiple jobs"""
        from mcli.workflow.scheduler.job import JobType, ScheduledJob

        monitor = self.JobMonitor()

        # Create two jobs - one short, one long
        job1 = ScheduledJob(
            name="short_job", cron_expression="* * * * *", job_type=JobType.COMMAND, command="test1"
        )

        job2 = ScheduledJob(
            name="long_job", cron_expression="* * * * *", job_type=JobType.COMMAND, command="test2"
        )

        thread1 = threading.Thread(target=lambda: time.sleep(0.05))
        thread2 = threading.Thread(target=lambda: time.sleep(1.0))
        thread1.start()
        thread2.start()

        monitor.add_job(job1, thread1)
        monitor.add_job(job2, thread2)

        # Wait for first thread to complete
        thread1.join()

        # Check jobs
        monitor._check_running_jobs()

        # job1 should be removed, job2 should remain
        assert job1.id not in monitor.running_jobs
        assert job2.id in monitor.running_jobs

        # Cleanup
        thread2.join()

    def test_monitor_loop_handles_exceptions(self):
        """Test that monitor loop handles exceptions gracefully"""
        monitor = self.JobMonitor()

        # Patch _check_running_jobs to raise exception
        with patch.object(monitor, "_check_running_jobs", side_effect=Exception("Test error")):
            monitor.start_monitoring()

            # Wait a bit - monitor should not crash
            time.sleep(0.5)

            assert monitor.monitoring is True

            monitor.stop_monitoring()

    def test_thread_safety_with_concurrent_operations(self):
        """Test thread safety with concurrent add/remove operations"""
        from mcli.workflow.scheduler.job import JobType, ScheduledJob

        monitor = self.JobMonitor()
        monitor.start_monitoring()

        jobs = []
        threads = []

        # Add multiple jobs concurrently
        def add_jobs():
            for i in range(5):
                job = ScheduledJob(
                    name=f"job_{i}",
                    cron_expression="* * * * *",
                    job_type=JobType.COMMAND,
                    command=f"test{i}",
                )
                thread = threading.Thread(target=lambda: time.sleep(0.1))
                thread.start()
                monitor.add_job(job, thread)
                jobs.append(job)
                threads.append(thread)

        # Start multiple threads adding jobs
        adder_threads = [threading.Thread(target=add_jobs) for _ in range(3)]
        for t in adder_threads:
            t.start()

        for t in adder_threads:
            t.join()

        # All jobs should be tracked
        running_jobs = monitor.get_running_jobs()
        assert len(running_jobs) > 0

        # Cleanup
        for t in threads:
            t.join()
        monitor.stop_monitoring()

    def test_monitor_stats_job_runtimes_accuracy(self):
        """Test that job runtime calculations are reasonably accurate"""
        from mcli.workflow.scheduler.job import JobType, ScheduledJob

        monitor = self.JobMonitor()

        job = ScheduledJob(
            name="test", cron_expression="* * * * *", job_type=JobType.COMMAND, command="test"
        )

        thread = threading.Thread(target=lambda: time.sleep(0.5))
        thread.start()

        monitor.add_job(job, thread)

        # Wait for specific duration
        time.sleep(0.3)

        stats = monitor.get_monitor_stats()
        runtime = stats["job_runtimes"][job.id]

        # Runtime should be approximately 0.3 seconds (allow some variance)
        assert 0 <= runtime <= 1  # Should be less than 1 second

        # Cleanup
        thread.join()

    def test_monitor_with_status_callback(self):
        """Test monitor with status callback function"""
        callback = MagicMock()
        monitor = self.JobMonitor(status_callback=callback)

        # Callback should be stored
        assert monitor.status_callback == callback

        # Note: Actual callback invocation would require scheduler integration
        # This tests that the callback is properly initialized

    def test_kill_job_with_finished_thread(self):
        """Test kill_job with already finished thread"""
        from mcli.workflow.scheduler.job import JobType, ScheduledJob

        monitor = self.JobMonitor()

        job = ScheduledJob(
            name="test", cron_expression="* * * * *", job_type=JobType.COMMAND, command="test"
        )

        thread = threading.Thread(target=lambda: time.sleep(0.05))
        thread.start()

        monitor.add_job(job, thread)

        # Wait for thread to finish
        thread.join()

        # Try to kill - should return True because thread is not alive
        result = monitor.kill_job(job.id)

        assert result is True
