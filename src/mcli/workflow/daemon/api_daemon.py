import click
import os
import json
import sqlite3
import hashlib
import subprocess
import tempfile
import threading
import time
import signal
import sys
import asyncio
import uvicorn
from pathlib import Path
from typing import Optional, Dict, List, Any, Union, Callable
from datetime import datetime
import uuid
import shutil
import psutil
from dataclasses import dataclass, asdict
import pickle
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import logging
import requests
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import inspect
import functools

# Import existing utilities
from mcli.lib.logger.logger import get_logger
from mcli.lib.toml.toml import read_from_toml
from mcli.lib.api.api import get_api_config, find_free_port

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
        self.app = FastAPI(title="MCLI API Daemon", description="Daemon service for MCLI commands", version="1.0.0")
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
        
        logger.info(f"API Daemon initialized with config: {self.config}")
    
    def _load_config(self, config_path: Optional[str] = None) -> APIDaemonConfig:
        """Load configuration from TOML file"""
        config = APIDaemonConfig()
        
        # Try to load from config.toml files
        config_paths = [
            Path("config.toml"),  # Current directory
            Path.home() / ".config" / "mcli" / "config.toml",  # User config
            Path(__file__).parent.parent.parent.parent.parent / "config.toml"  # Project root
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
        if os.environ.get('MCLI_API_DAEMON_ENABLED', 'false').lower() in ('true', '1', 'yes'):
            config.enabled = True
        
        if os.environ.get('MCLI_API_DAEMON_HOST'):
            config.host = os.environ.get('MCLI_API_DAEMON_HOST')
        
        if os.environ.get('MCLI_API_DAEMON_PORT'):
            config.port = int(os.environ.get('MCLI_API_DAEMON_PORT'))
            config.use_random_port = False
        
        if os.environ.get('MCLI_API_DAEMON_DEBUG', 'false').lower() in ('true', '1', 'yes'):
            config.debug = True
        
        if os.environ.get('MCLI_API_DAEMON_AUTO_START', 'false').lower() in ('true', '1', 'yes'):
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
                "config": asdict(self.config)
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
                    "/daemon/start",
                    "/daemon/stop"
                ]
            }
        
        # Status endpoint
        @self.app.get("/status")
        async def status():
            return {
                "running": self.running,
                "active_commands": len(self.active_commands),
                "command_history_count": len(self.command_history),
                "config": asdict(self.config)
            }
        
        # List available commands
        @self.app.get("/commands")
        async def list_commands():
            commands = self.db.get_all_commands()
            return {
                "commands": [asdict(cmd) for cmd in commands],
                "total": len(commands)
            }
        
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
                    raise HTTPException(status_code=400, detail="Either command_id or command_name must be provided")
                
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
                    result.get("execution_time_ms")
                )
                
                return result
                
            except Exception as e:
                logger.error(f"Error executing command: {e}")
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
    
    async def _execute_command_async(self, command: 'Command', args: List[str], timeout: int) -> Dict[str, Any]:
        """Execute command asynchronously"""
        command_id = str(uuid.uuid4())
        start_time = time.time()
        
        try:
            # Add to active commands
            self.active_commands[command_id] = {
                "command": command,
                "args": args,
                "start_time": start_time,
                "status": "running"
            }
            
            # Execute command in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                self._execute_command_sync, 
                command, 
                args, 
                timeout
            )
            
            execution_time = (time.time() - start_time) * 1000
            
            # Update active commands
            self.active_commands[command_id]["status"] = "completed"
            self.active_commands[command_id]["result"] = result
            self.active_commands[command_id]["execution_time"] = execution_time
            
            # Add to history
            if self.config.enable_command_history:
                self.command_history.append({
                    "id": command_id,
                    "command": command,
                    "args": args,
                    "result": result,
                    "execution_time": execution_time,
                    "timestamp": datetime.now().isoformat()
                })
            
            result["execution_time_ms"] = int(execution_time)
            return result
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            
            # Update active commands
            self.active_commands[command_id]["status"] = "failed"
            self.active_commands[command_id]["error"] = str(e)
            
            return {
                "success": False,
                "error": str(e),
                "execution_time_ms": int(execution_time)
            }
        finally:
            # Clean up active command after timeout
            def cleanup():
                time.sleep(300)  # 5 minutes
                if command_id in self.active_commands:
                    del self.active_commands[command_id]
            
            threading.Thread(target=cleanup, daemon=True).start()
    
    def _execute_command_sync(self, command: 'Command', args: List[str], timeout: int) -> Dict[str, Any]:
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
                port=port,
                log_level="debug" if self.config.debug else "info"
            )
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        
        # Wait for server to start
        time.sleep(2)
        
        self.running = True
        logger.info(f"API daemon started on http://{self.config.host}:{port}")
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def stop(self):
        """Stop the API daemon server"""
        if not self.running:
            logger.warning("API daemon is not running")
            return
        
        self.running = False
        logger.info("API daemon stopped")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down API daemon")
        self.stop()
        sys.exit(0)
    
    def status(self) -> Dict[str, Any]:
        """Get daemon status"""
        return {
            "running": self.running,
            "config": asdict(self.config),
            "active_commands": len(self.active_commands),
            "command_history_count": len(self.command_history),
            "database_commands": len(self.db.get_all_commands())
        }

# Import the existing Command and CommandDatabase classes
from mcli.workflow.daemon.daemon import Command, CommandDatabase, CommandExecutor

@click.group(name="api-daemon")
def api_daemon():
    """API Daemon service for MCLI commands"""
    pass

@api_daemon.command()
@click.option('--config', help='Path to configuration file')
@click.option('--host', help='Host to bind to')
@click.option('--port', type=int, help='Port to bind to')
@click.option('--debug', is_flag=True, help='Enable debug mode')
def start(config: Optional[str], host: Optional[str], port: Optional[int], debug: bool):
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
    daemon.start()
    
    try:
        # Keep the main thread alive
        while daemon.running:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received interrupt, shutting down...")
        daemon.stop()

@api_daemon.command()
def stop():
    """Stop the API daemon service"""
    # Try to stop via HTTP request
    try:
        response = requests.post("http://localhost:8000/daemon/stop")
        if response.status_code == 200:
            logger.info("API daemon stopped successfully")
        else:
            logger.error("Failed to stop API daemon")
    except requests.exceptions.RequestException:
        logger.error("Could not connect to API daemon")

@api_daemon.command()
def status():
    """Show API daemon status"""
    try:
        response = requests.get("http://localhost:8000/status")
        if response.status_code == 200:
            status_data = response.json()
            logger.info(f"API Daemon Status:")
            logger.info(f"  Running: {status_data['running']}")
            logger.info(f"  Active Commands: {status_data['active_commands']}")
            logger.info(f"  Command History: {status_data['command_history_count']}")
            logger.info(f"  Config: {status_data['config']}")
        else:
            logger.error("Failed to get API daemon status")
    except requests.exceptions.RequestException:
        logger.error("Could not connect to API daemon")

@api_daemon.command()
def commands():
    """List available commands"""
    try:
        response = requests.get("http://localhost:8000/commands")
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Available Commands ({data['total']}):")
            for cmd in data['commands']:
                logger.info(f"  {cmd['name']}: {cmd['description']}")
        else:
            logger.error("Failed to get commands")
    except requests.exceptions.RequestException:
        logger.error("Could not connect to API daemon") 