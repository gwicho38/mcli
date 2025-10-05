"""
Unit tests for mcli.workflow.scheduler.persistence module
"""

import json
import pytest
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open


class TestJobStorage:
    """Test suite for JobStorage class"""

    def test_job_storage_init_with_custom_dir(self):
        """Test JobStorage initialization with custom directory"""
        from mcli.workflow.scheduler.persistence import JobStorage

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JobStorage(storage_dir=tmpdir)

            assert storage.storage_dir == Path(tmpdir)
            assert storage.jobs_file == Path(tmpdir) / "jobs.json"
            assert storage.history_file == Path(tmpdir) / "job_history.json"
            assert storage.lock is not None

    def test_job_storage_init_creates_directory(self):
        """Test that JobStorage creates storage directory"""
        from mcli.workflow.scheduler.persistence import JobStorage

        with tempfile.TemporaryDirectory() as tmpdir:
            storage_dir = Path(tmpdir) / "scheduler"
            storage = JobStorage(storage_dir=str(storage_dir))

            assert storage.storage_dir.exists()
            assert storage.storage_dir.is_dir()

    def test_job_storage_init_creates_files(self):
        """Test that JobStorage creates initial JSON files"""
        from mcli.workflow.scheduler.persistence import JobStorage

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JobStorage(storage_dir=tmpdir)

            assert storage.jobs_file.exists()
            assert storage.history_file.exists()

    def test_job_storage_default_directory(self):
        """Test that default storage directory is in ~/.mcli/scheduler"""
        from mcli.workflow.scheduler.persistence import JobStorage

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('mcli.workflow.scheduler.persistence.Path.home', return_value=Path(tmpdir)):
                storage = JobStorage()

                expected_dir = Path(tmpdir) / ".mcli" / "scheduler"
                assert storage.storage_dir == expected_dir

    def test_save_and_load_jobs(self):
        """Test saving and loading jobs"""
        from mcli.workflow.scheduler.persistence import JobStorage
        from mcli.workflow.scheduler.job import ScheduledJob, JobType

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JobStorage(storage_dir=tmpdir)

            # Create test jobs
            jobs = [
                ScheduledJob(
                    name="job1",
                    cron_expression="0 0 * * *",
                    job_type=JobType.COMMAND,
                    command="echo test1"
                ),
                ScheduledJob(
                    name="job2",
                    cron_expression="0 12 * * *",
                    job_type=JobType.PYTHON,
                    command="python script.py"
                )
            ]

            # Save jobs
            result = storage.save_jobs(jobs)
            assert result is True

            # Load jobs
            loaded_jobs = storage.load_jobs()
            assert len(loaded_jobs) == 2
            assert loaded_jobs[0].name == "job1"
            assert loaded_jobs[1].name == "job2"

    def test_save_jobs_empty_list(self):
        """Test saving empty job list"""
        from mcli.workflow.scheduler.persistence import JobStorage

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JobStorage(storage_dir=tmpdir)

            result = storage.save_jobs([])
            assert result is True

            loaded_jobs = storage.load_jobs()
            assert loaded_jobs == []

    def test_load_jobs_empty_file(self):
        """Test loading jobs from empty file"""
        from mcli.workflow.scheduler.persistence import JobStorage

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JobStorage(storage_dir=tmpdir)

            jobs = storage.load_jobs()
            assert jobs == []

    def test_save_single_job_new(self):
        """Test saving a new single job"""
        from mcli.workflow.scheduler.persistence import JobStorage
        from mcli.workflow.scheduler.job import ScheduledJob, JobType

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JobStorage(storage_dir=tmpdir)

            job = ScheduledJob(
                name="test_job",
                cron_expression="0 0 * * *",
                job_type=JobType.COMMAND,
                command="test"
            )

            result = storage.save_job(job)
            assert result is True

            loaded_jobs = storage.load_jobs()
            assert len(loaded_jobs) == 1
            assert loaded_jobs[0].name == "test_job"

    def test_save_single_job_update_existing(self):
        """Test updating an existing job"""
        from mcli.workflow.scheduler.persistence import JobStorage
        from mcli.workflow.scheduler.job import ScheduledJob, JobType

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JobStorage(storage_dir=tmpdir)

            # Create and save initial job
            job = ScheduledJob(
                name="test_job",
                cron_expression="0 0 * * *",
                job_type=JobType.COMMAND,
                command="original command",
                job_id="test-id-123"
            )
            storage.save_job(job)

            # Update job
            job.command = "updated command"
            storage.save_job(job)

            # Load and verify
            loaded_jobs = storage.load_jobs()
            assert len(loaded_jobs) == 1
            assert loaded_jobs[0].command == "updated command"

    def test_delete_job(self):
        """Test deleting a job"""
        from mcli.workflow.scheduler.persistence import JobStorage
        from mcli.workflow.scheduler.job import ScheduledJob, JobType

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JobStorage(storage_dir=tmpdir)

            # Create and save jobs
            job1 = ScheduledJob(
                name="job1",
                cron_expression="0 0 * * *",
                job_type=JobType.COMMAND,
                command="test1",
                job_id="id1"
            )
            job2 = ScheduledJob(
                name="job2",
                cron_expression="0 12 * * *",
                job_type=JobType.COMMAND,
                command="test2",
                job_id="id2"
            )

            storage.save_jobs([job1, job2])

            # Delete job1
            result = storage.delete_job("id1")
            assert result is True

            # Verify only job2 remains
            loaded_jobs = storage.load_jobs()
            assert len(loaded_jobs) == 1
            assert loaded_jobs[0].name == "job2"

    def test_delete_nonexistent_job(self):
        """Test deleting a job that doesn't exist returns False"""
        from mcli.workflow.scheduler.persistence import JobStorage

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JobStorage(storage_dir=tmpdir)

            result = storage.delete_job("nonexistent-id")
            assert result is False

    def test_get_job_by_id(self):
        """Test getting a specific job by ID"""
        from mcli.workflow.scheduler.persistence import JobStorage
        from mcli.workflow.scheduler.job import ScheduledJob, JobType

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JobStorage(storage_dir=tmpdir)

            job = ScheduledJob(
                name="test_job",
                cron_expression="0 0 * * *",
                job_type=JobType.COMMAND,
                command="test",
                job_id="test-id"
            )

            storage.save_job(job)

            retrieved_job = storage.get_job("test-id")
            assert retrieved_job is not None
            assert retrieved_job.name == "test_job"
            assert retrieved_job.id == "test-id"

    def test_get_job_not_found(self):
        """Test getting a job that doesn't exist returns None"""
        from mcli.workflow.scheduler.persistence import JobStorage

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JobStorage(storage_dir=tmpdir)

            job = storage.get_job("nonexistent-id")
            assert job is None

    def test_record_job_execution(self):
        """Test recording job execution history"""
        from mcli.workflow.scheduler.persistence import JobStorage
        from mcli.workflow.scheduler.job import ScheduledJob, JobType

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JobStorage(storage_dir=tmpdir)

            job = ScheduledJob(
                name="test_job",
                cron_expression="0 0 * * *",
                job_type=JobType.COMMAND,
                command="test",
                job_id="test-id"
            )

            execution_data = {
                "status": "completed",
                "runtime_seconds": 5,
                "output": "Success",
                "error": "",
                "exit_code": 0,
                "retries": 0
            }

            storage.record_job_execution(job, execution_data)

            # Verify history was recorded
            history = storage.get_job_history(job_id="test-id")
            assert len(history) == 1
            assert history[0]["job_id"] == "test-id"
            assert history[0]["job_name"] == "test_job"
            assert history[0]["status"] == "completed"

    def test_record_job_execution_limits_output_size(self):
        """Test that job execution records limit output size"""
        from mcli.workflow.scheduler.persistence import JobStorage
        from mcli.workflow.scheduler.job import ScheduledJob, JobType

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JobStorage(storage_dir=tmpdir)

            job = ScheduledJob(
                name="test",
                cron_expression="0 0 * * *",
                job_type=JobType.COMMAND,
                command="test",
                job_id="test-id"
            )

            # Create very long output
            long_output = "x" * 5000
            execution_data = {
                "status": "completed",
                "output": long_output,
                "error": ""
            }

            storage.record_job_execution(job, execution_data)

            history = storage.get_job_history(job_id="test-id")
            # Output should be truncated to 1000 chars
            assert len(history[0]["output"]) <= 1000

    def test_get_job_history_all(self):
        """Test getting all job history"""
        from mcli.workflow.scheduler.persistence import JobStorage
        from mcli.workflow.scheduler.job import ScheduledJob, JobType

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JobStorage(storage_dir=tmpdir)

            job = ScheduledJob(
                name="test",
                cron_expression="0 0 * * *",
                job_type=JobType.COMMAND,
                command="test",
                job_id="test-id"
            )

            # Record multiple executions
            for i in range(5):
                execution_data = {"status": f"run_{i}"}
                storage.record_job_execution(job, execution_data)

            history = storage.get_job_history()
            assert len(history) == 5

    def test_get_job_history_with_limit(self):
        """Test getting job history with limit"""
        from mcli.workflow.scheduler.persistence import JobStorage
        from mcli.workflow.scheduler.job import ScheduledJob, JobType

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JobStorage(storage_dir=tmpdir)

            job = ScheduledJob(
                name="test",
                cron_expression="0 0 * * *",
                job_type=JobType.COMMAND,
                command="test",
                job_id="test-id"
            )

            # Record 10 executions
            for i in range(10):
                execution_data = {"status": f"run_{i}"}
                storage.record_job_execution(job, execution_data)

            history = storage.get_job_history(limit=3)
            assert len(history) == 3

    def test_get_job_history_for_specific_job(self):
        """Test getting history for a specific job"""
        from mcli.workflow.scheduler.persistence import JobStorage
        from mcli.workflow.scheduler.job import ScheduledJob, JobType

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JobStorage(storage_dir=tmpdir)

            job1 = ScheduledJob(
                name="job1",
                cron_expression="0 0 * * *",
                job_type=JobType.COMMAND,
                command="test1",
                job_id="id1"
            )

            job2 = ScheduledJob(
                name="job2",
                cron_expression="0 0 * * *",
                job_type=JobType.COMMAND,
                command="test2",
                job_id="id2"
            )

            # Record executions for both jobs
            storage.record_job_execution(job1, {"status": "completed"})
            storage.record_job_execution(job2, {"status": "completed"})
            storage.record_job_execution(job1, {"status": "failed"})

            # Get history for job1 only
            history = storage.get_job_history(job_id="id1")
            assert len(history) == 2
            assert all(record["job_id"] == "id1" for record in history)

    def test_cleanup_old_history(self):
        """Test cleaning up old history records"""
        from mcli.workflow.scheduler.persistence import JobStorage
        from mcli.workflow.scheduler.job import ScheduledJob, JobType

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JobStorage(storage_dir=tmpdir)

            # Manually create history with old dates
            old_date = (datetime.now() - timedelta(days=60)).isoformat()
            recent_date = (datetime.now() - timedelta(days=1)).isoformat()

            history_data = {
                "history": [
                    {"job_id": "1", "executed_at": old_date, "status": "old"},
                    {"job_id": "2", "executed_at": recent_date, "status": "recent"}
                ],
                "version": "1.0"
            }

            storage._write_json_file(storage.history_file, history_data)

            # Cleanup records older than 30 days
            storage.cleanup_old_history(days=30)

            # Verify only recent record remains
            history = storage.get_job_history()
            assert len(history) == 1
            assert history[0]["status"] == "recent"

    def test_export_jobs(self):
        """Test exporting jobs to file"""
        from mcli.workflow.scheduler.persistence import JobStorage
        from mcli.workflow.scheduler.job import ScheduledJob, JobType

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JobStorage(storage_dir=tmpdir)

            job = ScheduledJob(
                name="export_job",
                cron_expression="0 0 * * *",
                job_type=JobType.COMMAND,
                command="test"
            )

            storage.save_job(job)

            export_path = Path(tmpdir) / "export.json"
            result = storage.export_jobs(str(export_path))

            assert result is True
            assert export_path.exists()

            # Verify export content
            with open(export_path, 'r') as f:
                export_data = json.load(f)

            assert "jobs" in export_data
            assert len(export_data["jobs"]) == 1
            assert export_data["jobs"][0]["name"] == "export_job"

    def test_import_jobs(self):
        """Test importing jobs from file"""
        from mcli.workflow.scheduler.persistence import JobStorage
        from mcli.workflow.scheduler.job import ScheduledJob, JobType

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JobStorage(storage_dir=tmpdir)

            # Create import file
            import_data = {
                "jobs": [
                    {
                        "name": "imported_job",
                        "cron_expression": "0 0 * * *",
                        "job_type": "command",
                        "command": "test",
                        "created_at": datetime.now().isoformat()
                    }
                ]
            }

            import_path = Path(tmpdir) / "import.json"
            with open(import_path, 'w') as f:
                json.dump(import_data, f)

            # Import jobs
            count = storage.import_jobs(str(import_path))

            assert count == 1

            # Verify job was imported
            jobs = storage.load_jobs()
            assert len(jobs) == 1
            assert jobs[0].name == "imported_job"

    def test_import_jobs_with_replace(self):
        """Test importing jobs with replace=True"""
        from mcli.workflow.scheduler.persistence import JobStorage

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JobStorage(storage_dir=tmpdir)

            # Add existing job
            import_data1 = {
                "jobs": [{
                    "name": "old_job",
                    "cron_expression": "0 0 * * *",
                    "job_type": "command",
                    "command": "test",
                    "created_at": datetime.now().isoformat()
                }]
            }

            import_path1 = Path(tmpdir) / "import1.json"
            with open(import_path1, 'w') as f:
                json.dump(import_data1, f)

            storage.import_jobs(str(import_path1))

            # Import new job with replace=True
            import_data2 = {
                "jobs": [{
                    "name": "new_job",
                    "cron_expression": "0 0 * * *",
                    "job_type": "command",
                    "command": "test",
                    "created_at": datetime.now().isoformat()
                }]
            }

            import_path2 = Path(tmpdir) / "import2.json"
            with open(import_path2, 'w') as f:
                json.dump(import_data2, f)

            count = storage.import_jobs(str(import_path2), replace=True)

            # Old job should be replaced
            jobs = storage.load_jobs()
            assert len(jobs) == 1
            assert jobs[0].name == "new_job"

    def test_import_jobs_skips_duplicates(self):
        """Test that import skips duplicate job names"""
        from mcli.workflow.scheduler.persistence import JobStorage

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JobStorage(storage_dir=tmpdir)

            # Create and import first job
            import_data = {
                "jobs": [
                    {
                        "name": "duplicate_job",
                        "cron_expression": "0 0 * * *",
                        "job_type": "command",
                        "command": "test1",
                        "created_at": datetime.now().isoformat()
                    },
                    {
                        "name": "duplicate_job",
                        "cron_expression": "0 12 * * *",
                        "job_type": "command",
                        "command": "test2",
                        "created_at": datetime.now().isoformat()
                    }
                ]
            }

            import_path = Path(tmpdir) / "import.json"
            with open(import_path, 'w') as f:
                json.dump(import_data, f)

            count = storage.import_jobs(str(import_path))

            # Only first job should be imported
            assert count == 1
            jobs = storage.load_jobs()
            assert len(jobs) == 1

    def test_get_storage_info(self):
        """Test getting storage information"""
        from mcli.workflow.scheduler.persistence import JobStorage
        from mcli.workflow.scheduler.job import ScheduledJob, JobType

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JobStorage(storage_dir=tmpdir)

            # Add some jobs
            job = ScheduledJob(
                name="test",
                cron_expression="0 0 * * *",
                job_type=JobType.COMMAND,
                command="test"
            )
            storage.save_job(job)

            info = storage.get_storage_info()

            assert "storage_dir" in info
            assert "jobs_file_size" in info
            assert "history_file_size" in info
            assert "total_size" in info
            assert "jobs_count" in info
            assert "history_count" in info
            assert info["jobs_count"] == 1

    def test_read_json_file_handles_missing_file(self):
        """Test that _read_json_file handles missing file gracefully"""
        from mcli.workflow.scheduler.persistence import JobStorage

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JobStorage(storage_dir=tmpdir)

            result = storage._read_json_file(Path(tmpdir) / "nonexistent.json")

            assert result == {}

    def test_read_json_file_handles_corrupted_json(self):
        """Test that _read_json_file handles corrupted JSON gracefully"""
        from mcli.workflow.scheduler.persistence import JobStorage

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JobStorage(storage_dir=tmpdir)

            # Create corrupted JSON file
            corrupted_file = Path(tmpdir) / "corrupted.json"
            corrupted_file.write_text("{invalid json}")

            result = storage._read_json_file(corrupted_file)

            assert result == {}

    def test_write_json_file_atomic_operation(self):
        """Test that _write_json_file uses atomic write"""
        from mcli.workflow.scheduler.persistence import JobStorage

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JobStorage(storage_dir=tmpdir)

            test_file = Path(tmpdir) / "test.json"
            test_data = {"key": "value"}

            storage._write_json_file(test_file, test_data)

            # Verify file exists and contains correct data
            assert test_file.exists()
            with open(test_file, 'r') as f:
                loaded_data = json.load(f)

            assert loaded_data == test_data

            # Verify temp file was cleaned up
            temp_file = test_file.with_suffix(".tmp")
            assert not temp_file.exists()

    def test_thread_safety_with_lock(self):
        """Test that operations use locking for thread safety"""
        from mcli.workflow.scheduler.persistence import JobStorage

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JobStorage(storage_dir=tmpdir)

            # Lock should exist
            assert storage.lock is not None
            assert hasattr(storage.lock, 'acquire')
            assert hasattr(storage.lock, 'release')

    def test_history_keeps_only_last_1000_records(self):
        """Test that history is limited to 1000 records"""
        from mcli.workflow.scheduler.persistence import JobStorage
        from mcli.workflow.scheduler.job import ScheduledJob, JobType

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JobStorage(storage_dir=tmpdir)

            # Manually create history with > 1000 records
            history_data = {
                "history": [
                    {"job_id": str(i), "executed_at": datetime.now().isoformat()}
                    for i in range(1100)
                ],
                "version": "1.0"
            }

            storage._write_json_file(storage.history_file, history_data)

            # Record a new execution (should trigger cleanup)
            job = ScheduledJob(
                name="test",
                cron_expression="0 0 * * *",
                job_type=JobType.COMMAND,
                command="test"
            )
            storage.record_job_execution(job, {"status": "completed"})

            # Verify history is limited to 1000
            history = storage.get_job_history(limit=2000)
            assert len(history) <= 1000

    def test_load_jobs_handles_corrupted_job_data(self):
        """Test that load_jobs skips corrupted job records"""
        from mcli.workflow.scheduler.persistence import JobStorage

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JobStorage(storage_dir=tmpdir)

            # Create jobs file with one valid and one invalid job
            jobs_data = {
                "jobs": [
                    {
                        "name": "valid_job",
                        "cron_expression": "0 0 * * *",
                        "job_type": "command",
                        "command": "test",
                        "created_at": datetime.now().isoformat()
                    },
                    {
                        "name": "invalid_job"
                        # Missing required fields
                    }
                ],
                "version": "1.0"
            }

            storage._write_json_file(storage.jobs_file, jobs_data)

            # Load should succeed with only valid job
            jobs = storage.load_jobs()
            assert len(jobs) == 1
            assert jobs[0].name == "valid_job"
