"""
Job persistence and storage for the MCLI scheduler

Handles saving/loading jobs to/from disk, ensuring persistence across power cycles
"""

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from mcli.lib.logger.logger import get_logger

from .job import ScheduledJob

logger = get_logger(__name__)


class JobStorage:
    """Handles persistent storage of scheduled jobs"""

    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = Path(storage_dir) if storage_dir else self._get_default_storage_dir()
        self.jobs_file = self.storage_dir / "jobs.json"
        self.history_file = self.storage_dir / "job_history.json"
        self.lock = threading.Lock()

        # Ensure storage directory exists
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Initialize files if they don't exist
        self._initialize_storage()

    def _get_default_storage_dir(self) -> Path:
        """Get default storage directory"""
        home = Path.home()
        storage_dir = home / ".mcli" / "scheduler"
        return storage_dir

    def _initialize_storage(self):
        """Initialize storage files if they don't exist"""
        if not self.jobs_file.exists():
            self._write_json_file(self.jobs_file, {"jobs": [], "version": "1.0"})

        if not self.history_file.exists():
            self._write_json_file(self.history_file, {"history": [], "version": "1.0"})

    def _read_json_file(self, file_path: Path) -> dict:
        """Safely read JSON file with error handling"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"File not found: {file_path}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {file_path}: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return {}

    def _write_json_file(self, file_path: Path, data: dict):
        """Safely write JSON file with atomic operation"""
        temp_file = file_path.with_suffix(".tmp")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # Atomic move
            temp_file.replace(file_path)

        except Exception as e:
            logger.error(f"Error writing {file_path}: {e}")
            if temp_file.exists():
                temp_file.unlink()

    def save_jobs(self, jobs: List[ScheduledJob]) -> bool:
        """Save list of jobs to persistent storage"""
        with self.lock:
            try:
                jobs_data = {
                    "jobs": [job.to_dict() for job in jobs],
                    "version": "1.0",
                    "saved_at": datetime.now().isoformat(),
                    "count": len(jobs),
                }

                self._write_json_file(self.jobs_file, jobs_data)
                logger.info(f"Saved {len(jobs)} jobs to {self.jobs_file}")
                return True

            except Exception as e:
                logger.error(f"Failed to save jobs: {e}")
                return False

    def load_jobs(self) -> List[ScheduledJob]:
        """Load jobs from persistent storage"""
        with self.lock:
            try:
                data = self._read_json_file(self.jobs_file)
                jobs_data = data.get("jobs", [])

                jobs = []
                for job_dict in jobs_data:
                    try:
                        job = ScheduledJob.from_dict(job_dict)
                        jobs.append(job)
                    except Exception as e:
                        logger.error(f"Failed to load job {job_dict.get('id', 'unknown')}: {e}")

                logger.info(f"Loaded {len(jobs)} jobs from {self.jobs_file}")
                return jobs

            except Exception as e:
                logger.error(f"Failed to load jobs: {e}")
                return []

    def save_job(self, job: ScheduledJob) -> bool:
        """Save a single job (update existing or add new)"""
        jobs = self.load_jobs()

        # Find existing job or add new one
        updated = False
        for i, existing_job in enumerate(jobs):
            if existing_job.id == job.id:
                jobs[i] = job
                updated = True
                break

        if not updated:
            jobs.append(job)

        return self.save_jobs(jobs)

    def delete_job(self, job_id: str) -> bool:
        """Delete a job from storage"""
        jobs = self.load_jobs()
        original_count = len(jobs)

        jobs = [job for job in jobs if job.id != job_id]

        if len(jobs) < original_count:
            return self.save_jobs(jobs)
        return False

    def get_job(self, job_id: str) -> Optional[ScheduledJob]:
        """Get a specific job by ID"""
        jobs = self.load_jobs()
        for job in jobs:
            if job.id == job_id:
                return job
        return None

    def record_job_execution(self, job: ScheduledJob, execution_data: dict):
        """Record job execution in history"""
        with self.lock:
            try:
                history_data = self._read_json_file(self.history_file)
                history = history_data.get("history", [])

                # Create execution record
                record = {
                    "job_id": job.id,
                    "job_name": job.name,
                    "executed_at": datetime.now().isoformat(),
                    "status": execution_data.get("status", "unknown"),
                    "runtime_seconds": execution_data.get("runtime_seconds", 0),
                    "output": execution_data.get("output", "")[:1000],  # Limit output size
                    "error": execution_data.get("error", "")[:1000],  # Limit error size
                    "exit_code": execution_data.get("exit_code"),
                    "retries": execution_data.get("retries", 0),
                }

                history.append(record)

                # Keep only last 1000 records
                if len(history) > 1000:
                    history = history[-1000:]

                history_data = {
                    "history": history,
                    "version": "1.0",
                    "updated_at": datetime.now().isoformat(),
                }

                self._write_json_file(self.history_file, history_data)

            except Exception as e:
                logger.error(f"Failed to record job execution: {e}")

    def get_job_history(self, job_id: Optional[str] = None, limit: int = 100) -> List[dict]:
        """Get job execution history"""
        try:
            history_data = self._read_json_file(self.history_file)
            history = history_data.get("history", [])

            if job_id:
                history = [record for record in history if record.get("job_id") == job_id]

            # Return most recent records first
            history = sorted(history, key=lambda x: x.get("executed_at", ""), reverse=True)

            return history[:limit]

        except Exception as e:
            logger.error(f"Failed to get job history: {e}")
            return []

    def cleanup_old_history(self, days: int = 30):
        """Remove job history older than specified days"""
        with self.lock:
            try:
                cutoff_date = datetime.now() - timedelta(days=days)
                cutoff_str = cutoff_date.isoformat()

                history_data = self._read_json_file(self.history_file)
                history = history_data.get("history", [])

                # Filter out old records
                filtered_history = [
                    record for record in history if record.get("executed_at", "") > cutoff_str
                ]

                removed_count = len(history) - len(filtered_history)

                if removed_count > 0:
                    history_data = {
                        "history": filtered_history,
                        "version": "1.0",
                        "updated_at": datetime.now().isoformat(),
                    }

                    self._write_json_file(self.history_file, history_data)
                    logger.info(f"Cleaned up {removed_count} old history records")

            except Exception as e:
                logger.error(f"Failed to cleanup old history: {e}")

    def export_jobs(self, export_path: str) -> bool:
        """Export all jobs to a file"""
        try:
            jobs = self.load_jobs()
            export_data = {
                "jobs": [job.to_dict() for job in jobs],
                "exported_at": datetime.now().isoformat(),
                "export_version": "1.0",
                "source": "mcli-scheduler",
            }

            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Exported {len(jobs)} jobs to {export_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export jobs: {e}")
            return False

    def import_jobs(self, import_path: str, replace: bool = False) -> int:
        """Import jobs from a file"""
        try:
            with open(import_path, "r", encoding="utf-8") as f:
                import_data = json.load(f)

            imported_jobs_data = import_data.get("jobs", [])
            existing_jobs = [] if replace else self.load_jobs()

            imported_count = 0
            for job_data in imported_jobs_data:
                try:
                    job = ScheduledJob.from_dict(job_data)

                    # Check for duplicates by name
                    if not replace and any(existing.name == job.name for existing in existing_jobs):
                        logger.warning(f"Skipping duplicate job: {job.name}")
                        continue

                    existing_jobs.append(job)
                    imported_count += 1

                except Exception as e:
                    logger.error(f"Failed to import job: {e}")

            if imported_count > 0:
                self.save_jobs(existing_jobs)
                logger.info(f"Imported {imported_count} jobs from {import_path}")

            return imported_count

        except Exception as e:
            logger.error(f"Failed to import jobs: {e}")
            return 0

    def get_storage_info(self) -> dict:
        """Get information about storage usage"""
        try:
            jobs_size = self.jobs_file.stat().st_size if self.jobs_file.exists() else 0
            history_size = self.history_file.stat().st_size if self.history_file.exists() else 0

            jobs_count = len(self.load_jobs())
            history_count = len(self.get_job_history())

            return {
                "storage_dir": str(self.storage_dir),
                "jobs_file_size": jobs_size,
                "history_file_size": history_size,
                "total_size": jobs_size + history_size,
                "jobs_count": jobs_count,
                "history_count": history_count,
                "jobs_file": str(self.jobs_file),
                "history_file": str(self.history_file),
            }

        except Exception as e:
            logger.error(f"Failed to get storage info: {e}")
            return {}


# Import required for datetime operations
from datetime import timedelta
