"""Restart policy supervisor for mcli services.

Monitors services with restart policies and automatically restarts them
when they die unexpectedly.
"""

import threading
import time
from collections import defaultdict
from typing import Dict

from mcli.lib.constants import ServiceDefaults
from mcli.lib.logger.logger import get_logger
from mcli.lib.services.config import ServiceConfig
from mcli.lib.services.health import check_pid_alive
from mcli.lib.services.state import load_state, save_state

logger = get_logger(__name__)


class ServiceSupervisor:
    """Daemon thread that monitors services and applies restart policies."""

    def __init__(self, manager):
        self._manager = manager
        self._threads: Dict[str, threading.Thread] = {}
        self._stop_events: Dict[str, threading.Event] = {}
        self._restart_times: Dict[str, list] = defaultdict(list)

    def start_supervisor(self, config: ServiceConfig) -> None:
        """Start a supervisor thread for a service."""
        name = config.name
        if name in self._threads and self._threads[name].is_alive():
            logger.debug(f"Supervisor already running for {name}")
            return

        if config.restart_policy == "never":
            return

        stop_event = threading.Event()
        self._stop_events[name] = stop_event

        thread = threading.Thread(
            target=self._supervisor_loop,
            args=(config, stop_event),
            daemon=True,
            name=f"supervisor-{name}",
        )
        thread.start()
        self._threads[name] = thread
        logger.info(f"Supervisor started for {name} (policy: {config.restart_policy})")

    def stop_supervisor(self, name: str) -> None:
        """Stop the supervisor thread for a service."""
        event = self._stop_events.pop(name, None)
        if event:
            event.set()

        thread = self._threads.pop(name, None)
        if thread and thread.is_alive():
            thread.join(timeout=5)

        self._restart_times.pop(name, None)
        logger.info(f"Supervisor stopped for {name}")

    def _supervisor_loop(self, config: ServiceConfig, stop_event: threading.Event) -> None:
        """Main supervisor loop."""
        name = config.name

        while not stop_event.is_set():
            stop_event.wait(timeout=ServiceDefaults.HEALTH_CHECK_INTERVAL)
            if stop_event.is_set():
                break

            state = load_state(name)
            if not state or state.status != "running":
                continue

            pid = state.pid
            if pid and check_pid_alive(pid):
                continue

            # Process died — check restart policy
            should_restart = False
            if config.restart_policy == "always":
                should_restart = True
            elif config.restart_policy == "on-failure":
                should_restart = True

            if not should_restart:
                continue

            # Check restart window
            now = time.time()
            window = ServiceDefaults.RESTART_WINDOW
            self._restart_times[name] = [t for t in self._restart_times[name] if now - t < window]

            if len(self._restart_times[name]) >= ServiceDefaults.MAX_RESTART_ATTEMPTS:
                logger.error(
                    f"Service {name} exceeded max restarts "
                    f"({ServiceDefaults.MAX_RESTART_ATTEMPTS}) in {window}s"
                )
                state.status = "failed"
                save_state(state)
                break

            # Restart with delay
            self._restart_times[name].append(now)
            attempt = len(self._restart_times[name])
            logger.info(
                f"Restarting {name} (attempt {attempt}/{ServiceDefaults.MAX_RESTART_ATTEMPTS})"
            )

            time.sleep(ServiceDefaults.RESTART_DELAY)

            new_pid = self._manager.start_service(config)
            if new_pid:
                state = load_state(name)
                if state:
                    state.restart_count += 1
                    save_state(state)
            else:
                logger.error(f"Failed to restart service {name}")

    def stop_all(self) -> None:
        """Stop all supervisor threads."""
        for name in list(self._stop_events.keys()):
            self.stop_supervisor(name)
