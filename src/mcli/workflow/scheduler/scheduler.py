"""
Main scheduler engine for MCLI cron functionality

Coordinates job scheduling, execution, monitoring, and persistence.
Provides the primary interface for the cron scheduling system.
"""

import asyncio
import json
import os
import signal
import subprocess
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from mcli.lib.logger.logger import get_logger

from .cron_parser import CronExpression
from .job import JobStatus, JobType, ScheduledJob
from .monitor import JobMonitor
from .persistence import JobStorage

logger = get_logger(__name__)


class JobExecutor:
    """Handles job execution in separate processes/threads"""

    def __init__(self):
        self.running_processes: Dict[str, subprocess.Popen] = {}
        self.lock = threading.Lock()

    def execute_job(self, job: ScheduledJob) -> Dict[str, Any]:
        """Execute a job and return execution results"""
        start_time = datetime.now()
        result = {
            "job_id": job.id,
            "started_at": start_time.isoformat(),
            "status": JobStatus.RUNNING.value,
            "output": "",
            "error": "",
            "exit_code": None,
            "runtime_seconds": 0,
        }

        try:
            job.update_status(JobStatus.RUNNING)
            logger.info(f"Executing job {job.name} [{job.id}]")

            if job.job_type == JobType.COMMAND:
                result.update(self._execute_command(job))
            elif job.job_type == JobType.PYTHON:
                result.update(self._execute_python(job))
            elif job.job_type == JobType.CLEANUP:
                result.update(self._execute_cleanup(job))
            elif job.job_type == JobType.SYSTEM:
                result.update(self._execute_system(job))
            elif job.job_type == JobType.API_CALL:
                result.update(self._execute_api_call(job))
            else:
                result.update(self._execute_custom(job))

        except Exception as e:
            logger.error(f"Job execution failed for {job.name}: {e}")
            result.update({"status": JobStatus.FAILED.value, "error": str(e), "exit_code": -1})

        # Calculate runtime
        end_time = datetime.now()
        runtime = (end_time - start_time).total_seconds()
        result["runtime_seconds"] = runtime
        result["completed_at"] = end_time.isoformat()

        # Update job status
        if result["status"] == JobStatus.RUNNING.value:
            if result.get("exit_code") == 0:
                job.update_status(JobStatus.COMPLETED, result["output"], result["error"])
                result["status"] = JobStatus.COMPLETED.value
            else:
                job.update_status(JobStatus.FAILED, result["output"], result["error"])
                result["status"] = JobStatus.FAILED.value

        job.runtime_seconds = runtime
        return result

    def _execute_command(self, job: ScheduledJob) -> Dict[str, Any]:
        """Execute shell command"""
        env = os.environ.copy()
        env.update(job.environment)

        process = subprocess.Popen(
            job.command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            cwd=job.working_directory,
        )

        # Store process for potential cancellation
        with self.lock:
            self.running_processes[job.id] = process

        try:
            stdout, stderr = process.communicate(timeout=job.max_runtime)
            return {"output": stdout, "error": stderr, "exit_code": process.returncode}
        except subprocess.TimeoutExpired:
            process.kill()
            return {
                "output": "",
                "error": f"Job timed out after {job.max_runtime} seconds",
                "exit_code": -1,
                "status": JobStatus.FAILED.value,
            }
        finally:
            with self.lock:
                self.running_processes.pop(job.id, None)

    def _execute_python(self, job: ScheduledJob) -> Dict[str, Any]:
        """Execute Python code"""
        try:
            # Create temporary Python file
            import tempfile

            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write(job.command)
                temp_file = f.name

            try:
                # Execute Python file
                env = os.environ.copy()
                env.update(job.environment)

                process = subprocess.Popen(
                    [os.sys.executable, temp_file],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    env=env,
                    cwd=job.working_directory,
                )

                stdout, stderr = process.communicate(timeout=job.max_runtime)
                return {"output": stdout, "error": stderr, "exit_code": process.returncode}
            finally:
                os.unlink(temp_file)

        except Exception as e:
            return {
                "output": "",
                "error": f"Python execution failed: {e}",
                "exit_code": -1,
                "status": JobStatus.FAILED.value,
            }

    def _execute_cleanup(self, job: ScheduledJob) -> Dict[str, Any]:
        """Execute file system cleanup tasks"""
        try:
            # Parse cleanup command (JSON format expected)
            cleanup_config = json.loads(job.command)

            results = []
            for task in cleanup_config.get("tasks", []):
                task_type = task.get("type")
                path = task.get("path")

                if task_type == "delete_old_files":
                    days = task.get("days", 30)
                    pattern = task.get("pattern", "*")
                    result = self._cleanup_old_files(path, days, pattern)
                    results.append(result)
                elif task_type == "empty_trash":
                    result = self._empty_trash()
                    results.append(result)
                elif task_type == "organize_desktop":
                    result = self._organize_desktop()
                    results.append(result)

            return {"output": json.dumps(results, indent=2), "error": "", "exit_code": 0}

        except Exception as e:
            return {
                "output": "",
                "error": f"Cleanup task failed: {e}",
                "exit_code": -1,
                "status": JobStatus.FAILED.value,
            }

    def _execute_system(self, job: ScheduledJob) -> Dict[str, Any]:
        """Execute system maintenance tasks"""
        # Similar to cleanup but for system-level tasks
        return self._execute_command(job)

    def _execute_api_call(self, job: ScheduledJob) -> Dict[str, Any]:
        """Execute HTTP API calls"""
        try:
            import requests

            # Parse API call configuration
            api_config = json.loads(job.command)

            method = api_config.get("method", "GET").upper()
            url = api_config["url"]
            headers = api_config.get("headers", {})
            data = api_config.get("data")
            timeout = min(api_config.get("timeout", 30), job.max_runtime)

            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=data if data else None,
                timeout=timeout,
            )

            return {
                "output": json.dumps(
                    {
                        "status_code": response.status_code,
                        "headers": dict(response.headers),
                        "body": response.text,
                    },
                    indent=2,
                ),
                "error": "",
                "exit_code": 0 if response.ok else 1,
            }

        except Exception as e:
            return {
                "output": "",
                "error": f"API call failed: {e}",
                "exit_code": -1,
                "status": JobStatus.FAILED.value,
            }

    def _execute_custom(self, job: ScheduledJob) -> Dict[str, Any]:
        """Execute custom job types"""
        # Default to command execution
        return self._execute_command(job)

    def _cleanup_old_files(self, path: str, days: int, pattern: str) -> Dict[str, Any]:
        """Clean up old files in a directory"""
        try:
            import glob
            from pathlib import Path

            cutoff_time = datetime.now() - timedelta(days=days)
            deleted_files = []

            for file_path in glob.glob(os.path.join(path, pattern)):
                file_obj = Path(file_path)
                if file_obj.is_file():
                    mod_time = datetime.fromtimestamp(file_obj.stat().st_mtime)
                    if mod_time < cutoff_time:
                        file_obj.unlink()
                        deleted_files.append(str(file_path))

            return {
                "task": "delete_old_files",
                "path": path,
                "deleted_count": len(deleted_files),
                "deleted_files": deleted_files[:10],  # Limit output
            }

        except Exception as e:
            return {"task": "delete_old_files", "error": str(e)}

    def _empty_trash(self) -> Dict[str, Any]:
        """Empty system trash/recycle bin"""
        try:
            import platform

            system = platform.system()

            if system == "Darwin":  # macOS
                subprocess.run(
                    ["osascript", "-e", 'tell application "Finder" to empty trash'], check=True
                )
            elif system == "Windows":
                subprocess.run(["powershell", "-Command", "Clear-RecycleBin -Force"], check=True)
            else:  # Linux
                trash_dir = os.path.expanduser("~/.local/share/Trash/files")
                if os.path.exists(trash_dir):
                    import shutil

                    shutil.rmtree(trash_dir)
                    os.makedirs(trash_dir)

            return {"task": "empty_trash", "status": "completed"}

        except Exception as e:
            return {"task": "empty_trash", "error": str(e)}

    def _organize_desktop(self) -> Dict[str, Any]:
        """Organize desktop files into folders"""
        try:
            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
            if not os.path.exists(desktop_path):
                return {"task": "organize_desktop", "error": "Desktop path not found"}

            organized_files = []
            file_types = {
                "Documents": [".pdf", ".doc", ".docx", ".txt", ".rtf"],
                "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg"],
                "Archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
                "Videos": [".mp4", ".avi", ".mov", ".mkv", ".wmv"],
                "Audio": [".mp3", ".wav", ".flac", ".aac", ".ogg"],
            }

            for filename in os.listdir(desktop_path):
                file_path = os.path.join(desktop_path, filename)
                if os.path.isfile(file_path):
                    file_ext = os.path.splitext(filename)[1].lower()

                    for folder, extensions in file_types.items():
                        if file_ext in extensions:
                            folder_path = os.path.join(desktop_path, folder)
                            os.makedirs(folder_path, exist_ok=True)

                            new_path = os.path.join(folder_path, filename)
                            os.rename(file_path, new_path)
                            organized_files.append(f"{filename} -> {folder}/")
                            break

            return {
                "task": "organize_desktop",
                "organized_count": len(organized_files),
                "organized_files": organized_files[:10],  # Limit output
            }

        except Exception as e:
            return {"task": "organize_desktop", "error": str(e)}

    def kill_job(self, job_id: str) -> bool:
        """Kill a running job process"""
        with self.lock:
            process = self.running_processes.get(job_id)
            if process and process.poll() is None:
                try:
                    process.terminate()
                    time.sleep(2)  # Give it time to terminate gracefully
                    if process.poll() is None:
                        process.kill()
                    return True
                except Exception as e:
                    logger.error(f"Failed to kill job {job_id}: {e}")
                    return False
        return False


class JobScheduler:
    """Main scheduler that coordinates all cron functionality"""

    def __init__(self, storage_dir: Optional[str] = None):
        self.storage = JobStorage(storage_dir)
        self.monitor = JobMonitor()
        self.executor = JobExecutor()

        self.jobs: Dict[str, ScheduledJob] = {}
        self.running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()

        # Load existing jobs
        self._load_jobs()

        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _load_jobs(self):
        """Load jobs from persistent storage"""
        jobs = self.storage.load_jobs()
        self.jobs = {job.id: job for job in jobs}
        logger.info(f"Loaded {len(self.jobs)} jobs from storage")

    def _save_jobs(self):
        """Save all jobs to persistent storage"""
        jobs_list = list(self.jobs.values())
        self.storage.save_jobs(jobs_list)

    def start(self):
        """Start the scheduler"""
        if self.running:
            logger.warning("Scheduler already running")
            return

        self.running = True
        self.monitor.start_monitoring()

        # Execute @reboot jobs
        self._execute_reboot_jobs()

        # Start main scheduler loop
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()

        logger.info("Job scheduler started")

    def stop(self):
        """Stop the scheduler"""
        if not self.running:
            return

        self.running = False
        self.monitor.stop_monitoring()

        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=10)

        # Save current state
        self._save_jobs()

        logger.info("Job scheduler stopped")

    def _signal_handler(self, signum, frame):
        """Handle system signals"""
        logger.info(f"Received signal {signum}, shutting down scheduler...")
        self.stop()

    def _scheduler_loop(self):
        """Main scheduling loop"""
        while self.running:
            try:
                current_time = datetime.now()

                for job in list(self.jobs.values()):
                    if not job.enabled:
                        continue

                    # Check if job should run
                    if self._should_run_job(job, current_time):
                        self._queue_job_execution(job)

                    # Handle retries
                    if job.should_retry():
                        retry_time = job.get_next_retry_time()
                        if current_time >= retry_time:
                            job.current_retry += 1
                            self._queue_job_execution(job)

                # Update next run times
                self._update_next_run_times()

                # Save state periodically
                self._save_jobs()

                time.sleep(30)  # Check every 30 seconds

            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(60)  # Wait longer on error

    def _should_run_job(self, job: ScheduledJob, current_time: datetime) -> bool:
        """Check if a job should run at the current time"""
        if job.status == JobStatus.RUNNING:
            return False

        try:
            cron = CronExpression(job.cron_expression)

            # For @reboot jobs, only run at startup
            if cron.is_reboot:
                return False

            # Check if it's time to run
            if job.next_run and current_time >= job.next_run:
                return True

            # Fallback: check if cron expression matches current time
            return cron.matches_now()

        except Exception as e:
            logger.error(f"Error checking job schedule for {job.name}: {e}")
            return False

    def _queue_job_execution(self, job: ScheduledJob):
        """Queue a job for execution"""

        def execute_job_thread():
            try:
                # Execute the job
                result = self.executor.execute_job(job)

                # Record execution history
                self.storage.record_job_execution(job, result)

                # Update next run time
                self._update_job_next_run(job)

                logger.info(f"Job {job.name} completed with status: {result['status']}")

            except Exception as e:
                logger.error(f"Error executing job {job.name}: {e}")
                job.update_status(JobStatus.FAILED, "", str(e))

        # Execute in separate thread
        thread = threading.Thread(target=execute_job_thread, daemon=True)
        thread.start()

        # Add to monitor
        self.monitor.add_job(job, thread)

    def _update_job_next_run(self, job: ScheduledJob):
        """Update job's next run time"""
        try:
            cron = CronExpression(job.cron_expression)
            if not cron.is_reboot:
                job.next_run = cron.get_next_run_time()
        except Exception as e:
            logger.error(f"Error updating next run time for {job.name}: {e}")

    def _update_next_run_times(self):
        """Update next run times for all jobs"""
        for job in self.jobs.values():
            if job.enabled and job.next_run is None:
                self._update_job_next_run(job)

    def _execute_reboot_jobs(self):
        """Execute jobs marked with @reboot"""
        reboot_jobs = [
            job
            for job in self.jobs.values()
            if job.enabled and job.cron_expression.strip().lower() == "@reboot"
        ]

        for job in reboot_jobs:
            logger.info(f"Executing @reboot job: {job.name}")
            self._queue_job_execution(job)

    # Public API methods

    def add_job(self, job: ScheduledJob) -> bool:
        """Add a new job to the scheduler"""
        try:
            with self.lock:
                self.jobs[job.id] = job
                self._update_job_next_run(job)

            self.storage.save_job(job)
            logger.info(f"Added job: {job.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to add job {job.name}: {e}")
            return False

    def remove_job(self, job_id: str) -> bool:
        """Remove a job from the scheduler"""
        try:
            with self.lock:
                job = self.jobs.pop(job_id, None)

            if job:
                self.storage.delete_job(job_id)
                # Try to kill if running
                self.executor.kill_job(job_id)
                logger.info(f"Removed job: {job.name}")
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to remove job {job_id}: {e}")
            return False

    def get_job(self, job_id: str) -> Optional[ScheduledJob]:
        """Get a job by ID"""
        return self.jobs.get(job_id)

    def get_all_jobs(self) -> List[ScheduledJob]:
        """Get all jobs"""
        return list(self.jobs.values())

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed status of a job"""
        job = self.jobs.get(job_id)
        if not job:
            return None

        return {
            "job": job.to_dict(),
            "is_running": self.monitor.is_job_running(job_id),
            "runtime": self.monitor.get_job_runtime(job_id),
            "history": self.storage.get_job_history(job_id, limit=5),
        }

    def get_scheduler_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics"""
        total_jobs = len(self.jobs)
        enabled_jobs = len([j for j in self.jobs.values() if j.enabled])
        running_jobs = len(self.monitor.get_running_jobs())

        return {
            "running": self.running,
            "total_jobs": total_jobs,
            "enabled_jobs": enabled_jobs,
            "running_jobs": running_jobs,
            "monitor_stats": self.monitor.get_monitor_stats(),
            "storage_info": self.storage.get_storage_info(),
        }

    def create_json_response(self) -> Dict[str, Any]:
        """Create JSON response for frontend integration"""
        jobs_data = []
        for job in self.jobs.values():
            job_data = job.to_dict()
            job_data["is_running"] = self.monitor.is_job_running(job.id)
            job_data["runtime"] = self.monitor.get_job_runtime(job.id)
            jobs_data.append(job_data)

        return {
            "timestamp": datetime.now().isoformat(),
            "scheduler": self.get_scheduler_stats(),
            "jobs": jobs_data,
        }


# Convenience functions for common job types


def create_desktop_cleanup_job(
    name: str = "Desktop Cleanup",
    cron_expression: str = "0 9 * * 1",  # Monday 9 AM
    enabled: bool = True,
) -> ScheduledJob:
    """Create a job to organize desktop files"""
    cleanup_config = {"tasks": [{"type": "organize_desktop"}]}

    return ScheduledJob(
        name=name,
        cron_expression=cron_expression,
        job_type=JobType.CLEANUP,
        command=json.dumps(cleanup_config),
        description="Automatically organize desktop files into folders",
        enabled=enabled,
    )


def create_temp_cleanup_job(
    name: str = "Temp File Cleanup",
    cron_expression: str = "0 2 * * *",  # Daily at 2 AM
    temp_path: str = "/tmp",
    days: int = 7,
    enabled: bool = True,
) -> ScheduledJob:
    """Create a job to clean up old temporary files"""
    cleanup_config = {
        "tasks": [{"type": "delete_old_files", "path": temp_path, "days": days, "pattern": "*"}]
    }

    return ScheduledJob(
        name=name,
        cron_expression=cron_expression,
        job_type=JobType.CLEANUP,
        command=json.dumps(cleanup_config),
        description=f"Clean up files older than {days} days from {temp_path}",
        enabled=enabled,
    )


def create_system_backup_job(
    name: str = "System Backup",
    cron_expression: str = "0 1 * * 0",  # Sunday 1 AM
    backup_command: str = "rsync -av /home/user/ /backup/",
    enabled: bool = True,
) -> ScheduledJob:
    """Create a system backup job"""
    return ScheduledJob(
        name=name,
        cron_expression=cron_expression,
        job_type=JobType.SYSTEM,
        command=backup_command,
        description="Weekly system backup",
        enabled=enabled,
        max_runtime=7200,  # 2 hours
    )
