import inspect
import logging
import os
import platform
import signal
import subprocess
import sys
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path
from types import FrameType
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

import psutil


class McliLogger:
    """
    Central logger for mcli that logs only to file, not to console.
    """

    _instance = None
    _runtime_tracing_enabled = False
    _system_tracing_enabled = False
    _system_trace_interval = 5  # Default to check every 5 seconds
    _system_trace_process_ids = set()  # Process IDs to monitor
    _system_trace_thread = None
    _excluded_modules: Set[str] = set()
    _trace_level = 0  # 0=off, 1=function calls, 2=line by line, 3=verbose
    _system_trace_level = 0  # 0=off, 1=basic, 2=detailed

    @classmethod
    def get_logger(cls, name="mcli.out"):
        """Get or create the singleton logger instance."""
        if cls._instance is None:
            cls._instance = cls(name)
        return cls._instance.logger

    @classmethod
    def get_trace_logger(cls):
        """Get the trace logger instance for interpreter trace events."""
        if cls._instance is None:
            cls._instance = cls("mcli.out")
        return cls._instance.trace_logger

    @classmethod
    def get_system_trace_logger(cls):
        """Get the system trace logger instance for OS process monitoring."""
        if cls._instance is None:
            cls._instance = cls("mcli.out")
        return cls._instance.system_trace_logger

    @classmethod
    def enable_runtime_tracing(cls, level: int = 1, excluded_modules: Optional[List[str]] = None):
        """
        Enable Python interpreter runtime tracing.

        Args:
            level: Tracing detail level (0=off, 1=function calls only, 2=line by line, 3=verbose)
            excluded_modules: List of module prefixes to exclude from tracing
        """
        if cls._instance is None:
            cls._instance = cls("mcli.out")

        cls._trace_level = max(0, min(level, 3))  # Clamp to 0-3

        if excluded_modules:
            cls._excluded_modules = set(excluded_modules)
        else:
            # Default exclusions to avoid excessive logging
            cls._excluded_modules = {
                "logging",
                "importlib",
                "typing",
                "abc",
                "inspect",
                "pkg_resources",
                "encodings",
                "_weakrefset",
                "weakref",
                "sre_",
                "re",
                "functools",
                "threading",
                "copyreg",
                "collections",
                "_collections_abc",
                "enum",
            }

        if cls._trace_level > 0 and not cls._runtime_tracing_enabled:
            # Enable tracing
            sys.settrace(cls._instance._trace_callback)
            threading.settrace(cls._instance._trace_callback)
            cls._runtime_tracing_enabled = True
            cls._instance.trace_logger.info(
                f"Python interpreter tracing enabled (level={cls._trace_level})"
            )
        elif cls._trace_level == 0 and cls._runtime_tracing_enabled:
            # Disable tracing
            sys.settrace(None)
            threading.settrace(None)
            cls._runtime_tracing_enabled = False
            cls._instance.trace_logger.info("Python interpreter tracing disabled")

    @classmethod
    def enable_system_tracing(cls, level: int = 1, interval: int = 5):
        """
        Enable OS-level system tracing for process monitoring.

        Args:
            level: System trace level (0=off, 1=basic info, 2=detailed)
            interval: Monitoring interval in seconds
        """
        if cls._instance is None:
            cls._instance = cls("mcli.out")

        # Add current process to monitoring
        cls._system_trace_process_ids.add(os.getpid())
        cls._system_trace_interval = max(1, interval)  # Minimum 1 second
        cls._system_trace_level = max(0, min(level, 2))  # Clamp to 0-2

        # Start monitoring thread if not already running
        if cls._system_trace_level > 0 and not cls._system_tracing_enabled:
            if cls._system_trace_thread is None or not cls._system_trace_thread.is_alive():
                cls._system_tracing_enabled = True
                cls._system_trace_thread = threading.Thread(
                    target=cls._instance._system_trace_worker, daemon=True
                )
                cls._system_trace_thread.start()
                cls._instance.system_trace_logger.info(
                    f"System process tracing enabled (level={cls._system_trace_level}, interval={cls._system_trace_interval}s)"
                )
        elif cls._system_trace_level == 0 and cls._system_tracing_enabled:
            # Disable tracing
            cls._system_tracing_enabled = False
            if cls._system_trace_thread and cls._system_trace_thread.is_alive():
                # Thread will terminate on its own when _system_tracing_enabled is False
                cls._instance.system_trace_logger.info("System process tracing disabled")

    @classmethod
    def disable_system_tracing(cls):
        """Disable OS-level system tracing."""
        cls.enable_system_tracing(level=0)

    @classmethod
    def register_process(cls, pid: int):
        """Register a process for monitoring."""
        if cls._instance is None:
            cls._instance = cls("mcli.out")

        if pid > 0:
            cls._system_trace_process_ids.add(pid)
            cls._instance.system_trace_logger.info(f"Registered process ID {pid} for monitoring")
            return True
        return False

    @classmethod
    def register_subprocess(cls, proc: subprocess.Popen) -> int:
        """
        Register a subprocess.Popen object for monitoring.
        Returns the process ID if successful, 0 otherwise.
        """
        if proc and proc.pid:
            if cls.register_process(proc.pid):
                return proc.pid
        return 0

    @classmethod
    def unregister_process(cls, pid: int):
        """Remove a process from monitoring."""
        if cls._instance is None:
            return

        if pid in cls._system_trace_process_ids:
            cls._system_trace_process_ids.remove(pid)
            cls._instance.system_trace_logger.info(f"Unregistered process ID {pid} from monitoring")

    @classmethod
    def disable_runtime_tracing(cls):
        """Disable Python interpreter runtime tracing."""
        cls.enable_runtime_tracing(level=0)

    def __init__(self, name="mcli.out"):
        self.name = name
        self.logger = logging.getLogger(name)
        self.trace_logger = logging.getLogger(f"{name}.trace")
        self.system_trace_logger = logging.getLogger(f"{name}.system")

        # Set to DEBUG to capture all levels in the log file
        self.logger.setLevel(logging.DEBUG)
        self.trace_logger.setLevel(logging.DEBUG)
        self.system_trace_logger.setLevel(logging.DEBUG)

        self.logger.propagate = False
        self.trace_logger.propagate = False
        self.system_trace_logger.propagate = False

        # Clear any existing handlers
        if self.logger.handlers:
            self.logger.handlers.clear()
        if self.trace_logger.handlers:
            self.trace_logger.handlers.clear()
        if self.system_trace_logger.handlers:
            self.system_trace_logger.handlers.clear()

        # Set up file handler with path resolution
        try:
            # Import paths utility for consistent path resolution
            from mcli.lib.paths import get_logs_dir

            # Get logs directory (e.g., ~/.mcli/logs)
            log_dir = get_logs_dir()

            # Create daily log file
            timestamp = datetime.now().strftime("%Y%m%d")
            log_file = log_dir / f"mcli_{timestamp}.log"
            trace_log_file = log_dir / f"mcli_trace_{timestamp}.log"
            system_trace_log_file = log_dir / f"mcli_system_{timestamp}.log"

            # Configure regular file handler
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)  # Capture all levels in the file
            file_formatter = logging.Formatter("%(asctime)s [%(levelname)s] [%(name)s] %(message)s")
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)

            # Configure trace file handler
            trace_handler = logging.FileHandler(trace_log_file)
            trace_handler.setLevel(logging.DEBUG)
            trace_formatter = logging.Formatter("%(asctime)s [TRACE] %(message)s")
            trace_handler.setFormatter(trace_formatter)
            self.trace_logger.addHandler(trace_handler)

            # Configure system trace file handler
            system_trace_handler = logging.FileHandler(system_trace_log_file)
            system_trace_handler.setLevel(logging.DEBUG)
            system_trace_formatter = logging.Formatter("%(asctime)s [SYSTEM] %(message)s")
            system_trace_handler.setFormatter(system_trace_formatter)
            self.system_trace_logger.addHandler(system_trace_handler)

            # Log the path to help with debugging
            self.logger.debug(f"Logging to: {log_file}")
            self.trace_logger.debug(f"Trace logging to: {trace_log_file}")
            self.system_trace_logger.debug(f"System trace logging to: {system_trace_log_file}")
        except Exception as e:
            # If we can't set up file logging, fall back to stderr
            # This should only happen during development or in unusual environments
            fallback_handler = logging.StreamHandler(sys.stderr)
            fallback_handler.setLevel(logging.ERROR)
            fallback_formatter = logging.Formatter(
                "[FALLBACK] %(asctime)s [%(levelname)s] %(message)s"
            )
            fallback_handler.setFormatter(fallback_formatter)
            self.logger.addHandler(fallback_handler)
            self.trace_logger.addHandler(fallback_handler)
            self.system_trace_logger.addHandler(fallback_handler)
            self.logger.error(f"Failed to set up file logging: {e}. Using stderr fallback.")

    def _should_trace(self, filename: str) -> bool:
        """Determine if a file should be traced based on exclusion rules."""
        # Skip files in standard library
        if filename.startswith(sys.prefix) or "<" in filename:
            return False

        # Get module name from filename
        module_name = os.path.basename(filename)
        if module_name.endswith(".py"):
            module_name = module_name[:-3]

        # Skip excluded modules
        for excluded in self._excluded_modules:
            if module_name.startswith(excluded):
                return False

        return True

    def _get_process_info(self, pid: int, detailed: bool = False) -> Dict[str, Any]:
        """Get information about a process given its PID."""
        try:
            # Check if process exists
            if not psutil.pid_exists(pid):
                return {"pid": pid, "status": "NOT_FOUND"}

            # Get process info
            proc = psutil.Process(pid)
            basic_info = {
                "pid": pid,
                "name": proc.name(),
                "status": proc.status(),
                "cpu_percent": proc.cpu_percent(interval=0.1),  # Quick sampling
                "memory_percent": proc.memory_percent(),
                "create_time": datetime.fromtimestamp(proc.create_time()).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "running_time": time.time() - proc.create_time(),
                "num_threads": proc.num_threads(),
                "username": proc.username(),
            }

            # Add more detailed information if requested
            if detailed:
                try:
                    # These can sometimes raise exceptions depending on permissions
                    children = proc.children(recursive=True)
                    io_counters = proc.io_counters()
                    connections = proc.connections()
                    open_files = proc.open_files()

                    detailed_info = {
                        "cmdline": " ".join(proc.cmdline()),
                        "exe": proc.exe(),
                        "cwd": proc.cwd(),
                        "nice": proc.nice(),
                        "io_counters": {
                            "read_bytes": io_counters.read_bytes,
                            "write_bytes": io_counters.write_bytes,
                        },
                        "num_fds": proc.num_fds() if hasattr(proc, "num_fds") else None,
                        "num_connections": len(connections),
                        "num_open_files": len(open_files),
                        "open_files": [f.path for f in open_files[:5]],  # First 5 files
                        "children": [
                            {"pid": child.pid, "name": child.name()} for child in children[:5]
                        ],  # First 5 children
                    }

                    basic_info.update(detailed_info)
                except Exception as e:
                    # Add error info but don't fail
                    basic_info["detailed_error"] = str(e)

            return basic_info

        except Exception as e:
            return {"pid": pid, "status": "ERROR", "error": str(e)}

    def _format_process_info(self, info: Dict[str, Any]) -> str:
        """Format process information for logging."""
        if info.get("status") == "NOT_FOUND":
            return f"Process {info['pid']} no longer exists"

        if info.get("status") == "ERROR":
            return f"Error getting info for process {info['pid']}: {info.get('error', 'Unknown error')}"

        # Format basic info
        lines = [
            f"Process {info['pid']} ({info['name']}):",
            f"  Status: {info['status']}",
            f"  CPU: {info['cpu_percent']:.1f}%, Memory: {info['memory_percent']:.1f}%",
            f"  Running time: {info['running_time']:.1f} seconds",
            f"  Threads: {info['num_threads']}",
        ]

        # Add detailed info if available
        if "cmdline" in info:
            lines.extend(
                [
                    f"  Command: {info['cmdline'][:100]}{'...' if len(info['cmdline']) > 100 else ''}",
                    f"  Working directory: {info['cwd']}",
                    f"  IO: read={info['io_counters']['read_bytes']/1024:.1f} KB, write={info['io_counters']['write_bytes']/1024:.1f} KB",
                    f"  Open files: {info['num_open_files']} (sample: {', '.join(info['open_files'][:3]) if info['open_files'] else 'none'})",
                    f"  Child processes: {len(info['children'])} (sample: child info available)",
                ]
            )

        return "\n".join(lines)

    def _system_trace_worker(self):
        """Worker thread that periodically collects and logs process information."""
        while self._system_tracing_enabled:
            try:
                # Check all registered processes
                current_pids = set(
                    self._system_trace_process_ids
                )  # Make a copy to avoid modification during iteration

                for pid in current_pids:
                    try:
                        detailed = self._system_trace_level >= 2
                        process_info = self._get_process_info(pid, detailed)

                        # Format and log the information
                        if process_info.get("status") != "NOT_FOUND":
                            formatted_info = self._format_process_info(process_info)
                            self.system_trace_logger.info(formatted_info)
                        else:
                            # Process no longer exists
                            self.system_trace_logger.info(
                                f"Process {pid} no longer exists, removing from monitoring"
                            )
                            self._system_trace_process_ids.discard(pid)

                        # Look for child processes if detailed tracing is enabled
                        if detailed and process_info.get("status") not in ["NOT_FOUND", "ERROR"]:
                            try:
                                proc = psutil.Process(pid)
                                children = proc.children(recursive=False)

                                for child in children:
                                    # If we find a child not already being monitored, add it
                                    if child.pid not in self._system_trace_process_ids:
                                        self._system_trace_process_ids.add(child.pid)
                                        self.system_trace_logger.info(
                                            f"Added child process {child.pid} ({child.name()}) to monitoring"
                                        )
                            except Exception as e:
                                self.system_trace_logger.error(
                                    f"Error getting child processes for {pid}: {e}"
                                )

                    except Exception as e:
                        self.system_trace_logger.error(
                            f"Error in system trace for process {pid}: {e}"
                        )

                # Add a separator between trace cycles for readability
                if current_pids:
                    self.system_trace_logger.info("-" * 50)

            except Exception as e:
                self.system_trace_logger.error(f"Error in system trace worker: {e}")

            # Sleep until next collection cycle
            time.sleep(self._system_trace_interval)

    def _trace_callback(self, frame: FrameType, event: str, arg: Any) -> Callable:
        """Trace callback function for sys.settrace()."""
        if self._trace_level == 0:
            return None

        try:
            filename = frame.f_code.co_filename
            lineno = frame.f_lineno
            function = frame.f_code.co_name

            # Skip if we should not trace this file
            if not self._should_trace(filename):
                return None

            # Log based on trace level and event type
            if event == "call" and self._trace_level >= 1:
                module = os.path.basename(filename)
                if module.endswith(".py"):
                    module = module[:-3]

                # Get function arguments for detailed tracing
                if self._trace_level >= 3:
                    args = inspect.getargvalues(frame)
                    args_str = []
                    for arg_name in args.args:
                        if arg_name in args.locals:
                            # Safely get string representation with limits
                            try:
                                arg_val = str(args.locals[arg_name])
                                # Truncate long values
                                if len(arg_val) > 100:
                                    arg_val = arg_val[:97] + "..."
                                args_str.append(f"{arg_name}={arg_val}")
                            except:
                                args_str.append(f"{arg_name}=<error>")
                    args_repr = ", ".join(args_str)
                    self.trace_logger.debug(
                        f"CALL {module}.{function}({args_repr}) at {filename}:{lineno}"
                    )
                else:
                    self.trace_logger.debug(f"CALL {module}.{function}() at {filename}:{lineno}")

            elif event == "line" and self._trace_level >= 2:
                # For line-by-line tracing (high volume)
                if self._trace_level >= 3:
                    # Include source line in verbose mode
                    try:
                        with open(filename, "r") as f:
                            lines = f.readlines()
                            source = (
                                lines[lineno - 1].strip()
                                if lineno <= len(lines)
                                else "<source not available>"
                            )
                        self.trace_logger.debug(f"LINE {filename}:{lineno} -> {source}")
                    except:
                        self.trace_logger.debug(f"LINE {filename}:{lineno}")
                else:
                    self.trace_logger.debug(f"LINE {filename}:{lineno}")

            elif event == "return" and self._trace_level >= 2:
                if self._trace_level >= 3:
                    # Include return value in verbose mode
                    ret_val = str(arg)
                    if len(ret_val) > 100:
                        ret_val = ret_val[:97] + "..."
                    self.trace_logger.debug(f"RETURN from {function} -> {ret_val}")
                else:
                    self.trace_logger.debug(f"RETURN from {function}")

            elif event == "exception" and self._trace_level >= 1:
                exc_type, exc_value, exc_tb = arg
                self.trace_logger.debug(
                    f"EXCEPTION in {filename}:{lineno} -> {exc_type.__name__}: {exc_value}"
                )
                if self._trace_level >= 3:
                    # Include traceback in verbose mode
                    tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
                    self.trace_logger.debug(f"Traceback:\n{tb_str}")
        except Exception as e:
            # Never let tracing errors crash the program
            try:
                self.trace_logger.error(f"Error in trace callback: {e}")
            except:
                pass
            return None

        # Continue tracing this thread if tracing is enabled
        return self._trace_callback if self._trace_level > 0 else None


# Singleton instance accessor function
def get_logger(name="mcli.out"):
    """
    Get the mcli logger instance.

    Args:
        name: Optional logger name. Defaults to "mcli.out".

    Returns:
        A configured Logger instance that logs only to file.
    """
    return McliLogger.get_logger(name)


def get_system_trace_logger():
    """
    Get the system trace logger instance.

    Returns:
        The system trace logger for OS-level process tracing.
    """
    return McliLogger.get_system_trace_logger()


def enable_runtime_tracing(level: int = 1, excluded_modules: Optional[List[str]] = None):
    """
    Enable Python interpreter runtime tracing.

    Args:
        level: Tracing detail level (0=off, 1=function calls only, 2=line by line, 3=verbose)
        excluded_modules: List of module prefixes to exclude from tracing
    """
    McliLogger.enable_runtime_tracing(level, excluded_modules)


def disable_runtime_tracing():
    """Disable Python interpreter runtime tracing."""
    McliLogger.disable_runtime_tracing()


def enable_system_tracing(level: int = 1, interval: int = 5):
    """
    Enable OS-level system tracing for process monitoring.

    Args:
        level: System trace level (0=off, 1=basic info, 2=detailed)
        interval: Monitoring interval in seconds (minimum 1 second)
    """
    McliLogger.enable_system_tracing(level, interval)


def disable_system_tracing():
    """Disable OS-level system tracing."""
    McliLogger.disable_system_tracing()


def register_process(pid: int) -> bool:
    """
    Register a process for monitoring.

    Args:
        pid: Process ID to monitor

    Returns:
        True if successfully registered, False otherwise
    """
    return McliLogger.register_process(pid)


def register_subprocess(proc: subprocess.Popen) -> int:
    """
    Register a subprocess.Popen object for monitoring.

    Args:
        proc: A subprocess.Popen object to monitor

    Returns:
        The process ID if successfully registered, 0 otherwise
    """
    return McliLogger.register_subprocess(proc)


def unregister_process(pid: int):
    """
    Remove a process from monitoring.

    Args:
        pid: Process ID to stop monitoring
    """
    McliLogger.unregister_process(pid)
