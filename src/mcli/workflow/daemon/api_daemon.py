import asyncio
import functools
import hashlib
import inspect
import json
import logging
import os
import pickle
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

import click
import psutil
import requests
import uvicorn
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from mcli.lib.api.api import find_free_port, get_api_config

# Import existing utilities
from mcli.lib.logger.logger import get_logger
from mcli.lib.toml.toml import read_from_toml

from .process_manager import ProcessManager

logger = get_logger(__name__)


@dataclass
class APIDaemonConfig:
    """Configuration for API Daemon"""

    enabled: bool = False
    host: str = "0.0.0.0"
    port: Optional[int] = None
    use_random_port: bool = True
    debug: bool = False
    auto_start: bool = False
    command_timeout: int = 300  # 5 minutes
    max_concurrent_commands: int = 10
    enable_command_caching: bool = True
    enable_command_history: bool = True


class APIDaemonService:
    """Daemon service that listens for API commands and executes them"""

    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.app = FastAPI(
            title="MCLI API Daemon", description="Daemon service for MCLI commands", version="1.0.0"
        )
        self.server = None
        self.server_thread = None
        self.running = False
        self.command_executors = {}
        self.command_history = []
        self.active_commands = {}

        # Setup FastAPI app
        self._setup_fastapi_app()

        # Load command database
        self.db = CommandDatabase()

        # Initialize process manager
        self.process_manager = ProcessManager()

        logger.info(f"API Daemon initialized with config: {self.config}")

    def _load_config(self, config_path: Optional[str] = None) -> APIDaemonConfig:
        """Load configuration from TOML file"""
        config = APIDaemonConfig()

        # Try to load from config.toml files
        config_paths = [
            Path("config.toml"),  # Current directory
            Path.home() / ".config" / "mcli" / "config.toml",  # User config
            Path(__file__).parent.parent.parent.parent.parent / "config.toml",  # Project root
        ]

        if config_path:
            config_paths.insert(0, Path(config_path))

        for path in config_paths:
            if path.exists():
                try:
                    daemon_config = read_from_toml(str(path), "api_daemon")
                    if daemon_config:
                        for key, value in daemon_config.items():
                            if hasattr(config, key):
                                setattr(config, key, value)
                        logger.debug(f"Loaded API daemon config from {path}")
                        break
                except Exception as e:
                    logger.debug(f"Could not load API daemon config from {path}: {e}")

        # Override with environment variables
        if os.environ.get("MCLI_API_DAEMON_ENABLED", "false").lower() in ("true", "1", "yes"):
            config.enabled = True

        if os.environ.get("MCLI_API_DAEMON_HOST"):
            config.host = os.environ.get("MCLI_API_DAEMON_HOST")

        if os.environ.get("MCLI_API_DAEMON_PORT"):
            config.port = int(os.environ.get("MCLI_API_DAEMON_PORT"))
            config.use_random_port = False

        if os.environ.get("MCLI_API_DAEMON_DEBUG", "false").lower() in ("true", "1", "yes"):
            config.debug = True

        if os.environ.get("MCLI_API_DAEMON_AUTO_START", "false").lower() in ("true", "1", "yes"):
            config.auto_start = True

        return config

    def _setup_fastapi_app(self):
        """Setup FastAPI application with endpoints"""
        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Health check endpoint
        @self.app.get("/health")
        async def health_check():
            return {
                "status": "healthy",
                "service": "MCLI API Daemon",
                "timestamp": datetime.now().isoformat(),
                "active_commands": len(self.active_commands),
                "config": asdict(self.config),
            }

        # Root endpoint
        @self.app.get("/")
        async def root():
            return {
                "service": "MCLI API Daemon",
                "version": "1.0.0",
                "status": "running" if self.running else "stopped",
                "endpoints": [
                    "/health",
                    "/status",
                    "/commands",
                    "/execute",
                    "/processes",
                    "/processes/{process_id}",
                    "/processes/{process_id}/start",
                    "/processes/{process_id}/stop",
                    "/processes/{process_id}/logs",
                    "/daemon/start",
                    "/daemon/stop",
                ],
            }

        # Status endpoint
        @self.app.get("/status")
        async def status():
            return {
                "running": self.running,
                "active_commands": len(self.active_commands),
                "command_history_count": len(self.command_history),
                "config": asdict(self.config),
            }

        # List available commands
        @self.app.get("/commands")
        async def list_commands():
            commands = self.db.get_all_commands()
            return {"commands": [asdict(cmd) for cmd in commands], "total": len(commands)}

        # Execute command endpoint
        @self.app.post("/execute")
        async def execute_command(request: Request, background_tasks: BackgroundTasks):
            try:
                body = await request.json()
                command_id = body.get("command_id")
                command_name = body.get("command_name")
                args = body.get("args", [])
                timeout = body.get("timeout", self.config.command_timeout)

                if not command_id and not command_name:
                    raise HTTPException(
                        status_code=400, detail="Either command_id or command_name must be provided"
                    )

                # Get command from database
                command = None
                if command_id:
                    command = self.db.get_command(command_id)
                elif command_name:
                    commands = self.db.search_commands(command_name, limit=1)
                    if commands:
                        command = commands[0]

                if not command:
                    raise HTTPException(status_code=404, detail="Command not found")

                # Execute command
                result = await self._execute_command_async(command, args, timeout)

                # Record execution
                self.db.record_execution(
                    command.id,
                    "success" if result["success"] else "failed",
                    result.get("output"),
                    result.get("error"),
                    result.get("execution_time_ms"),
                )

                return result

            except Exception as e:
                logger.error(f"Error executing command: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        # Process management endpoints (Docker-like API)
        @self.app.get("/processes")
        async def list_processes(request: Request):
            """List all processes (like 'docker ps')"""
            all_processes = request.query_params.get("all", "false").lower() == "true"
            processes = self.process_manager.list_processes(all_processes=all_processes)
            return {"processes": processes, "total": len(processes)}

        @self.app.post("/processes")
        async def create_process(request: Request):
            """Create a new process container"""
            try:
                body = await request.json()
                name = body.get("name", "unnamed")
                command = body.get("command")
                args = body.get("args", [])
                working_dir = body.get("working_dir")
                environment = body.get("environment")
                auto_start = body.get("auto_start", False)

                if not command:
                    raise HTTPException(status_code=400, detail="Command is required")

                process_id = self.process_manager.create(
                    name=name,
                    command=command,
                    args=args,
                    working_dir=working_dir,
                    environment=environment,
                )

                if auto_start:
                    self.process_manager.start(process_id)

                return {
                    "id": process_id,
                    "name": name,
                    "status": "created" if not auto_start else "starting",
                }

            except Exception as e:
                logger.error(f"Error creating process: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/processes/{process_id}")
        async def inspect_process(process_id: str):
            """Get detailed information about a process (like 'docker inspect')"""
            info = self.process_manager.inspect(process_id)
            if info is None:
                raise HTTPException(status_code=404, detail="Process not found")
            return info

        @self.app.post("/processes/{process_id}/start")
        async def start_process(process_id: str):
            """Start a process container"""
            success = self.process_manager.start(process_id)
            if not success:
                raise HTTPException(status_code=404, detail="Process not found or failed to start")
            return {"status": "started"}

        @self.app.post("/processes/{process_id}/stop")
        async def stop_process(process_id: str, request: Request):
            """Stop a process container"""
            body = (
                await request.json()
                if request.headers.get("content-type") == "application/json"
                else {}
            )
            timeout = body.get("timeout", 10)

            success = self.process_manager.stop(process_id, timeout)
            if not success:
                raise HTTPException(status_code=404, detail="Process not found")
            return {"status": "stopped"}

        @self.app.post("/processes/{process_id}/kill")
        async def kill_process(process_id: str):
            """Kill a process container"""
            success = self.process_manager.kill(process_id)
            if not success:
                raise HTTPException(status_code=404, detail="Process not found")
            return {"status": "killed"}

        @self.app.delete("/processes/{process_id}")
        async def remove_process(process_id: str, request: Request):
            """Remove a process container"""
            force = request.query_params.get("force", "false").lower() == "true"
            success = self.process_manager.remove(process_id, force)
            if not success:
                raise HTTPException(status_code=404, detail="Process not found")
            return {"status": "removed"}

        @self.app.get("/processes/{process_id}/logs")
        async def get_process_logs(process_id: str, request: Request):
            """Get logs from a process container (like 'docker logs')"""
            lines = request.query_params.get("lines")
            if lines:
                try:
                    lines = int(lines)
                except ValueError:
                    lines = None

            logs = self.process_manager.logs(process_id, lines)
            if logs is None:
                raise HTTPException(status_code=404, detail="Process not found")
            return logs

        @self.app.post("/processes/run")
        async def run_process(request: Request):
            """Create and start a process in one step (like 'docker run')"""
            try:
                body = await request.json()
                name = body.get("name", "unnamed")
                command = body.get("command")
                args = body.get("args", [])
                working_dir = body.get("working_dir")
                environment = body.get("environment")
                detach = body.get("detach", True)

                if not command:
                    raise HTTPException(status_code=400, detail="Command is required")

                process_id = self.process_manager.run(
                    name=name,
                    command=command,
                    args=args,
                    working_dir=working_dir,
                    environment=environment,
                    detach=detach,
                )

                return {"id": process_id, "name": name, "status": "running"}

            except Exception as e:
                logger.error(f"Error running process: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        # Daemon control endpoints
        @self.app.post("/daemon/start")
        async def start_daemon():
            if self.running:
                return {"status": "already_running"}

            self.start()
            return {"status": "started", "url": f"http://{self.config.host}:{self.config.port}"}

        @self.app.post("/daemon/stop")
        async def stop_daemon():
            if not self.running:
                return {"status": "already_stopped"}

            self.stop()
            return {"status": "stopped"}

    async def _execute_command_async(
        self, command: "Command", args: List[str], timeout: int
    ) -> Dict[str, Any]:
        """Execute command asynchronously"""
        command_id = str(uuid.uuid4())
        start_time = time.time()

        try:
            # Add to active commands
            self.active_commands[command_id] = {
                "command": command,
                "args": args,
                "start_time": start_time,
                "status": "running",
            }

            # Execute command in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, self._execute_command_sync, command, args, timeout
            )

            execution_time = (time.time() - start_time) * 1000

            # Update active commands
            self.active_commands[command_id]["status"] = "completed"
            self.active_commands[command_id]["result"] = result
            self.active_commands[command_id]["execution_time"] = execution_time

            # Add to history
            if self.config.enable_command_history:
                self.command_history.append(
                    {
                        "id": command_id,
                        "command": command,
                        "args": args,
                        "result": result,
                        "execution_time": execution_time,
                        "timestamp": datetime.now().isoformat(),
                    }
                )

            result["execution_time_ms"] = int(execution_time)
            return result

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000

            # Update active commands
            self.active_commands[command_id]["status"] = "failed"
            self.active_commands[command_id]["error"] = str(e)

            return {"success": False, "error": str(e), "execution_time_ms": int(execution_time)}
        finally:
            # Clean up active command after timeout
            def cleanup():
                time.sleep(300)  # 5 minutes
                if command_id in self.active_commands:
                    del self.active_commands[command_id]

            threading.Thread(target=cleanup, daemon=True).start()

    def _execute_command_sync(
        self, command: "Command", args: List[str], timeout: int
    ) -> Dict[str, Any]:
        """Execute command synchronously"""
        executor = CommandExecutor()
        return executor.execute_command(command, args)

    def start(self):
        """Start the API daemon server"""
        if self.running:
            logger.warning("API daemon is already running")
            return

        # Determine port
        port = self.config.port
        if port is None and self.config.use_random_port:
            port = find_free_port()
            self.config.port = port

        if port is None:
            port = 8000

        # Start server in background thread
        def run_server():
            uvicorn.run(
                self.app,
                host=self.config.host,
                port=int(port),
                log_level="error",  # Suppress info messages
                access_log=False,  # Suppress access logs
            )

        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()

        # Wait for server to be ready by checking health endpoint
        server_url = f"http://{self.config.host}:{port}"
        max_wait = 10  # Maximum wait time in seconds
        wait_interval = 0.5  # Check every 0.5 seconds

        for attempt in range(int(max_wait / wait_interval)):
            time.sleep(wait_interval)
            try:
                response = requests.get(f"{server_url}/health", timeout=1)
                if response.status_code == 200:
                    self.running = True
                    logger.info(f"API daemon started on {server_url}")
                    return
            except requests.exceptions.RequestException:
                continue  # Server not ready yet

        # If we get here, the server didn't start properly
        logger.error(f"Failed to start API daemon on {server_url} after {max_wait} seconds")
        self.running = False

    def stop(self):
        """Stop the API daemon server"""
        if not self.running:
            logger.warning("API daemon is not running")
            return

        self.running = False
        logger.info("API daemon stopped")

    def status(self) -> Dict[str, Any]:
        """Get daemon status"""
        return {
            "running": self.running,
            "config": asdict(self.config),
            "active_commands": len(self.active_commands),
            "command_history_count": len(self.command_history),
            "database_commands": len(self.db.get_all_commands()),
        }


# Import the existing Command and CommandDatabase classes
from mcli.workflow.daemon.commands import Command, CommandDatabase, CommandExecutor


@click.group(name="api-daemon")
def api_daemon():
    """API Daemon service for MCLI commands"""
    pass


@api_daemon.command()
@click.option("--config", help="Path to configuration file")
@click.option("--host", help="Host to bind to")
@click.option("--port", type=int, help="Port to bind to")
@click.option("--debug", is_flag=True, help="Enable debug mode")
@click.option("--background", "-b", is_flag=True, help="Run daemon in background")
@click.option("--pid-file", help="Path to PID file for background daemon")
def start(
    config: Optional[str],
    host: Optional[str],
    port: Optional[int],
    debug: bool,
    background: bool,
    pid_file: Optional[str],
):
    """Start the API daemon service"""
    daemon = APIDaemonService(config)

    # Override config with command line options
    if host:
        daemon.config.host = host
    if port:
        daemon.config.port = port
        daemon.config.use_random_port = False
    if debug:
        daemon.config.debug = debug

    logger.info("Starting API daemon service...")

    if background:
        # Run in background
        import os
        import sys

        # Fork the process
        try:
            pid = os.fork()
            if pid > 0:
                # Parent process - exit
                logger.info(f"API daemon started in background with PID {pid}")
                if pid_file:
                    with open(pid_file, "w") as f:
                        f.write(str(pid))
                    logger.info(f"PID written to {pid_file}")
                sys.exit(0)
            else:
                # Child process - run daemon
                # Detach from terminal
                os.setsid()
                os.chdir("/")
                os.umask(0)

                # Redirect output to /dev/null
                sys.stdout.flush()
                sys.stderr.flush()
                with open("/dev/null", "r") as dev_null_r:
                    os.dup2(dev_null_r.fileno(), sys.stdin.fileno())
                with open("/dev/null", "a+") as dev_null_w:
                    os.dup2(dev_null_w.fileno(), sys.stdout.fileno())
                    os.dup2(dev_null_w.fileno(), sys.stderr.fileno())

                # Start daemon
                daemon.start()

                # Keep running in background
                try:
                    while daemon.running:
                        time.sleep(1)
                except KeyboardInterrupt:
                    logger.info("Received interrupt, shutting down...")
                    daemon.stop()
        except OSError as e:
            logger.error(f"Failed to start daemon in background: {e}")
            sys.exit(1)
    else:
        # Run in foreground
        daemon.start()

        try:
            # Keep the main thread alive
            while daemon.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received interrupt, shutting down...")
            daemon.stop()


@api_daemon.command()
@click.option("--pid-file", help="Path to PID file for background daemon")
def restart(pid_file: Optional[str]):
    """Restart the API daemon service"""
    logger.info("Restarting API daemon service...")

    # Stop the daemon
    stop(pid_file)

    # Wait a moment for shutdown
    time.sleep(2)

    # Start the daemon again
    # Note: This will start in foreground mode
    # For background restart, user should use: start --background --pid-file <file>
    logger.info("Starting daemon in foreground mode...")
    daemon = APIDaemonService()
    daemon.start()

    try:
        while daemon.running:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received interrupt, shutting down...")
        daemon.stop()


@api_daemon.command()
@click.option("--pid-file", help="Path to PID file for background daemon")
def stop(pid_file: Optional[str]):
    """Stop the API daemon service"""
    # Try to stop via HTTP request first
    try:
        response = requests.post("http://localhost:8000/daemon/stop")
        if response.status_code == 200:
            logger.info("API daemon stopped successfully via HTTP")
            return
    except requests.exceptions.RequestException:
        logger.debug("Could not connect to API daemon via HTTP")

    # If HTTP stop failed, try PID file method
    if pid_file and Path(pid_file).exists():
        try:
            with open(pid_file, "r") as f:
                pid = int(f.read().strip())

            # Send SIGTERM to the process
            os.kill(pid, signal.SIGTERM)
            logger.info(f"Sent SIGTERM to daemon process {pid}")

            # Wait a moment and check if process is still running
            time.sleep(2)
            try:
                os.kill(pid, 0)  # Check if process exists
                # Process still running, send SIGKILL
                os.kill(pid, signal.SIGKILL)
                logger.info(f"Sent SIGKILL to daemon process {pid}")
            except OSError:
                # Process already terminated
                pass

            # Remove PID file
            Path(pid_file).unlink()
            logger.info(f"Removed PID file {pid_file}")

        except (ValueError, OSError) as e:
            logger.error(f"Failed to stop daemon using PID file: {e}")
    else:
        logger.error("Could not stop API daemon - no PID file provided and HTTP connection failed")


@api_daemon.command()
@click.option("--pid-file", help="Path to PID file for background daemon")
def status(pid_file: Optional[str]):
    """Show API daemon status"""
    # Check if daemon is running via HTTP
    try:
        response = requests.get("http://localhost:8000/status")
        if response.status_code == 200:
            status_data = response.json()
            logger.info(f"API Daemon Status:")
            logger.info(f"  Running: {status_data['running']}")
            logger.info(f"  Active Commands: {status_data['active_commands']}")
            logger.info(f"  Command History: {status_data['command_history_count']}")
            logger.info(f"  Config: {status_data['config']}")
            return
    except requests.exceptions.RequestException:
        logger.debug("Could not connect to API daemon via HTTP")

    # Check if background daemon is running via PID file
    if pid_file and Path(pid_file).exists():
        try:
            with open(pid_file, "r") as f:
                pid = int(f.read().strip())

            # Check if process is running
            try:
                os.kill(pid, 0)  # Check if process exists
                logger.info(f"API Daemon Status:")
                logger.info(f"  Running: True (PID: {pid})")
                logger.info(f"  PID File: {pid_file}")
                logger.info(f"  Note: Daemon is running in background mode")
                return
            except OSError:
                logger.info(f"API Daemon Status:")
                logger.info(f"  Running: False")
                logger.info(f"  Note: PID file exists but process is not running")
                # Remove stale PID file
                Path(pid_file).unlink()
                logger.info(f"  Removed stale PID file {pid_file}")
                return
        except (ValueError, OSError) as e:
            logger.error(f"Failed to read PID file: {e}")

    logger.info("API Daemon Status:")
    logger.info("  Running: False")
    logger.info("  Note: No daemon process found")


@api_daemon.command()
@click.option("--command-name", help="Name of the command to execute")
@click.option("--command-id", help="ID of the command to execute")
@click.option("--args", "-a", multiple=True, help="Command arguments")
@click.option("--timeout", type=int, help="Command timeout in seconds")
def execute(
    command_name: Optional[str], command_id: Optional[str], args: tuple, timeout: Optional[int]
):
    """Execute a command via the API daemon"""
    if not command_name and not command_id:
        logger.error("Either --command-name or --command-id must be provided")
        return

    try:
        # Try to execute via HTTP API
        response = requests.post(
            "http://localhost:8000/execute",
            json={
                "command_name": command_name,
                "command_id": command_id,
                "args": list(args),
                "timeout": timeout,
            },
        )

        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                logger.info("✅ Command executed successfully")
                if result.get("output"):
                    logger.info("Output:")
                    print(result["output"])
            else:
                logger.error("❌ Command execution failed")
                if result.get("error"):
                    logger.error(f"Error: {result['error']}")
        else:
            logger.error(f"Failed to execute command: {response.status_code}")

    except requests.exceptions.RequestException as e:
        logger.error(f"Could not connect to API daemon: {e}")
        logger.error("Make sure the API daemon is running")
        logger.error("Start it with: python -m mcli workflow api-daemon start")


@api_daemon.command()
def commands():
    """List available commands"""
    try:
        response = requests.get("http://localhost:8000/commands")
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Available Commands ({data['total']}):")
            for cmd in data["commands"]:
                logger.info(f"  {cmd['name']}: {cmd['description']}")
        else:
            logger.error("Failed to get commands")
    except requests.exceptions.RequestException:
        logger.error("Could not connect to API daemon")
