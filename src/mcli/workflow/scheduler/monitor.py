"""
Job monitoring and execution tracking for the MCLI scheduler
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional

from mcli.lib.logger.logger import get_logger

from .job import JobStatus, ScheduledJob

logger = get_logger(__name__)


class JobMonitor:
    """Monitors running jobs and handles timeouts, retries, and status updates"""

    def __init__(self, status_callback: Optional[Callable] = None):
        self.running_jobs: Dict[str, threading.Thread] = {}
        self.job_start_times: Dict[str, datetime] = {}
        self.status_callback = status_callback
        self.monitor_thread: Optional[threading.Thread] = None
        self.monitoring = False
        self.lock = threading.Lock()

    def start_monitoring(self):
        """Start the monitoring thread"""
        if self.monitoring:
            return

        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Job monitor started")

    def stop_monitoring(self):
        """Stop the monitoring thread"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Job monitor stopped")

    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                self._check_running_jobs()
                time.sleep(10)  # Check every 10 seconds
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")

    def _check_running_jobs(self):
        """Check status of running jobs"""
        with self.lock:
            current_time = datetime.now()
            jobs_to_remove = []

            for job_id, thread in self.running_jobs.items():
                start_time = self.job_start_times.get(job_id)

                if start_time:
                    runtime = (current_time - start_time).total_seconds()

                    # Check if thread is still alive
                    if not thread.is_alive():
                        jobs_to_remove.append(job_id)
                        logger.debug(f"Job {job_id} completed, removing from monitor")

                    # Note: Timeout handling would need job reference for max_runtime
                    # This is a simplified implementation

            # Clean up completed jobs
            for job_id in jobs_to_remove:
                self._remove_job(job_id)

    def add_job(self, job: ScheduledJob, thread: threading.Thread):
        """Add a job to monitoring"""
        with self.lock:
            self.running_jobs[job.id] = thread
            self.job_start_times[job.id] = datetime.now()
            logger.debug(f"Added job {job.id} to monitor")

    def _remove_job(self, job_id: str):
        """Remove a job from monitoring"""
        self.running_jobs.pop(job_id, None)
        self.job_start_times.pop(job_id, None)

    def get_running_jobs(self) -> List[str]:
        """Get list of currently running job IDs"""
        with self.lock:
            return list(self.running_jobs.keys())

    def is_job_running(self, job_id: str) -> bool:
        """Check if a specific job is currently running"""
        with self.lock:
            return job_id in self.running_jobs

    def get_job_runtime(self, job_id: str) -> Optional[int]:
        """Get runtime in seconds for a running job"""
        with self.lock:
            start_time = self.job_start_times.get(job_id)
            if start_time:
                return int((datetime.now() - start_time).total_seconds())
        return None

    def kill_job(self, job_id: str) -> bool:
        """Attempt to kill a running job"""
        with self.lock:
            thread = self.running_jobs.get(job_id)
            if thread and thread.is_alive():
                # Note: Python threads cannot be forcibly killed
                # This would need process-based execution for true killing
                logger.warning(f"Cannot forcibly kill job {job_id} - Python thread limitation")
                return False
        return True

    def get_monitor_stats(self) -> dict:
        """Get monitoring statistics"""
        with self.lock:
            stats = {
                "monitoring": self.monitoring,
                "running_jobs_count": len(self.running_jobs),
                "running_job_ids": list(self.running_jobs.keys()),
                "monitor_thread_alive": (
                    self.monitor_thread.is_alive() if self.monitor_thread else False
                ),
            }

            # Add runtime info for each job
            current_time = datetime.now()
            job_runtimes = {}
            for job_id, start_time in self.job_start_times.items():
                runtime = (current_time - start_time).total_seconds()
                job_runtimes[job_id] = int(runtime)

            stats["job_runtimes"] = job_runtimes
            return stats
