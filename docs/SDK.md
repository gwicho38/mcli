# MCLI Framework SDK Documentation

Complete guide to using `mcli-framework` as a Python library for building custom workflow commands, automation tools, and CLI applications.

## Table of Contents

1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [Core Modules](#core-modules)
4. [Creating Custom Commands](#creating-custom-commands)
5. [Workflow Management](#workflow-management)
6. [Scheduler & Automation](#scheduler--automation)
7. [Database Operations](#database-operations)
8. [Performance & Monitoring](#performance--monitoring)
9. [Advanced Patterns](#advanced-patterns)
10. [API Reference](#api-reference)

---

## Installation

```bash
# Install from PyPI
pip install mcli-framework

# Or with UV (recommended)
uv pip install mcli-framework

# Install with specific feature sets
pip install mcli-framework[ml]    # ML/data pipeline features
pip install mcli-framework[all]   # All features (default in 8.x)
```

---

## Quick Start

### Example 1: Simple Workflow Command

```python
from mcli.lib.custom_commands import get_command_manager

# Get the command manager
manager = get_command_manager(global_mode=True)

# Create a custom command
code = """
import click

@click.command()
@click.argument('name', default='World')
def greet(name):
    '''Greet someone by name'''
    click.echo(f'Hello, {name}!')
"""

# Save the command
manager.save_command(
    name="greet",
    code=code,
    description="A friendly greeting command",
    group="utils",
    metadata={"author": "Your Name", "version": "1.0"}
)

print("✅ Command created! Run with: mcli workflow greet World")
```

### Example 2: Command Discovery

```python
from mcli.lib.discovery.command_discovery import ClickCommandDiscovery

# Discover all available commands
discovery = ClickCommandDiscovery()
commands = discovery.discover_all_commands()

# Print command information
for cmd in commands[:5]:
    print(f"{cmd.full_name}: {cmd.description}")
    print(f"  Module: {cmd.module_name}")
    print(f"  Parameters: {[p['name'] for p in cmd.parameters]}")
```

### Example 3: Schedule a Task

```python
from mcli.workflow.scheduler.cron_scheduler import CronScheduler
from datetime import datetime

# Create scheduler
scheduler = CronScheduler()

# Define a task
def backup_data():
    print(f"Running backup at {datetime.now()}")
    # Your backup logic here

# Schedule daily backup at 2 AM
job_id = scheduler.schedule_job(
    name="daily_backup",
    schedule="0 2 * * *",  # Cron syntax
    command=backup_data
)

print(f"✅ Backup scheduled with ID: {job_id}")
```

---

## Core Modules

### Custom Commands (`mcli.lib.custom_commands`)

Manage user-created workflow commands with JSON storage and lockfile versioning.

```python
from mcli.lib.custom_commands import (
    CustomCommandManager,
    get_command_manager,
    load_custom_commands
)

# Get singleton manager
manager = get_command_manager(global_mode=True)  # ~/.mcli/commands/
# or
manager = get_command_manager(global_mode=False)  # .mcli/commands/ (local repo)

# Load all commands
commands = manager.load_all_commands()

# Load specific command
cmd = manager.load_command(Path("~/.mcli/commands/my_cmd.json"))

# Save new command
manager.save_command(
    name="data_processor",
    code="import click\n...",
    description="Process data files",
    group="data",
    metadata={"tags": ["etl", "pipeline"]}
)

# Delete command
manager.delete_command("data_processor")

# Export/Import
manager.export_commands(Path("./my-commands.json"))
manager.import_commands(Path("./my-commands.json"), overwrite=False)

# Lockfile management
manager.update_lockfile()
is_valid, report = manager.verify_lockfile()
```

### Path Management (`mcli.lib.paths`)

```python
from mcli.lib.paths import (
    get_custom_commands_dir,
    get_lockfile_path,
    get_git_root,
    is_git_repository
)

# Get commands directory
commands_dir = get_custom_commands_dir(global_mode=True)  # ~/.mcli/commands/
local_dir = get_custom_commands_dir(global_mode=False)    # .mcli/commands/

# Check if in git repo
if is_git_repository():
    git_root = get_git_root()
    print(f"Git root: {git_root}")

# Get lockfile path
lockfile = get_lockfile_path(global_mode=True)
```

### Logger (`mcli.lib.logger.logger`)

```python
from mcli.lib.logger.logger import get_logger, register_subprocess

# Get logger instance
logger = get_logger()

logger.info("Starting workflow")
logger.debug("Debug information")
logger.warning("Warning message")
logger.error("Error occurred")

# Register subprocess for monitoring
process = register_subprocess(
    "data_import",
    ["python", "import_data.py"],
    capture_output=True
)
```

### UI Styling (`mcli.lib.ui.styling`)

```python
from mcli.lib.ui.styling import success, error, info, warning

# Colored output
success("Operation completed successfully!")
error("Something went wrong")
info("Processing data...")
warning("This is deprecated")

# Rich tables and formatting
from rich.table import Table
from rich.console import Console

console = Console()
table = Table(title="Workflow Status")
table.add_column("Name", style="cyan")
table.add_column("Status", style="green")
table.add_row("backup", "✅ Complete")
console.print(table)
```

---

## Creating Custom Commands

### Method 1: Programmatic Creation

```python
from mcli.lib.custom_commands import get_command_manager
from pathlib import Path

manager = get_command_manager()

# Multi-level command group
code = """
import click
from pathlib import Path

@click.group(name='data')
def data_group():
    '''Data processing commands'''
    pass

@data_group.command('import')
@click.argument('source', type=click.Path(exists=True))
@click.option('--format', type=click.Choice(['csv', 'json', 'parquet']), default='csv')
def import_data(source, format):
    '''Import data from source file'''
    click.echo(f'Importing {format} data from {source}')
    # Your import logic here

@data_group.command('export')
@click.argument('destination', type=click.Path())
@click.option('--format', type=click.Choice(['csv', 'json', 'parquet']), default='csv')
def export_data(destination, format):
    '''Export data to destination'''
    click.echo(f'Exporting to {destination} as {format}')
    # Your export logic here
"""

manager.save_command(
    name="data",
    code=code,
    description="Data import/export utilities",
    group="etl",
    metadata={
        "author": "Data Team",
        "requires": ["pandas", "pyarrow"],
        "tags": ["data", "etl", "import", "export"]
    }
)
```

### Method 2: Load from Script Files

```python
from mcli.workflow.script_sync import ScriptSyncSystem
from pathlib import Path

# Initialize sync system
sync_system = ScriptSyncSystem(
    scripts_dir=Path("./my_scripts"),
    commands_dir=Path("~/.mcli/commands").expanduser()
)

# Create a script with metadata
script_content = """#!/usr/bin/env python3
# @description: Process log files and extract errors
# @version: 1.2.0
# @requires: re, datetime
# @tags: logs, analysis, debugging

import re
import click
from pathlib import Path

@click.command()
@click.argument('logfile', type=click.Path(exists=True))
@click.option('--pattern', default=r'ERROR|CRITICAL')
def analyze_logs(logfile, pattern):
    '''Analyze log files for errors'''
    with open(logfile) as f:
        errors = [line for line in f if re.search(pattern, line)]
    click.echo(f'Found {len(errors)} errors')
"""

# Save script
script_path = Path("./my_scripts/analyze_logs.py")
script_path.write_text(script_content)

# Sync to JSON (auto-converts to workflow command)
sync_system.sync_all_scripts()
```

### Method 3: Use Templates

```python
from mcli.lib.custom_commands import get_command_manager

manager = get_command_manager()

# List available templates
templates = {
    "standalone": """
import click

@click.command()
def {name}():
    '''Description here'''
    click.echo('Hello from {name}')
""",
    "group": """
import click

@click.group(name='{name}')
def {name}_group():
    '''Description here'''
    pass

@{name}_group.command('action')
def action():
    '''Subcommand description'''
    click.echo('Running action')
"""
}

# Create from template
manager.save_command(
    name="my_tool",
    code=templates["standalone"].format(name="my_tool"),
    description="My custom tool",
)
```

---

## Workflow Management

### Workflow Discovery

```python
from mcli.workflow.workflow import WorkflowGroup

# Get workflow group (loads from ~/.mcli/workflows/)
workflow = WorkflowGroup()

# List available workflows
workflows = workflow.list_commands(None)
print(f"Available workflows: {workflows}")

# Get specific workflow command
cmd = workflow.get_command(None, "backup")
if cmd:
    # Execute the workflow
    ctx = click.Context(cmd)
    cmd.invoke(ctx)
```

### Notebook Workflows

```python
from mcli.workflow.notebook.command_loader import NotebookCommandLoader
from pathlib import Path

# Load Jupyter notebook as workflow
notebook_path = Path("~/.mcli/workflows/data_pipeline.ipynb").expanduser()

# Load notebook command group
group = NotebookCommandLoader.load_group_from_file(
    notebook_path,
    group_name="data_pipeline"
)

# List commands in notebook
for cmd_name in group.commands:
    print(f"Command: {cmd_name}")
```

### Workflow Execution

```python
import subprocess
from mcli.lib.logger.logger import register_subprocess

# Execute workflow as subprocess
def run_workflow(name: str, *args):
    '''Run a workflow command'''
    cmd = ["mcli", "workflow", name] + list(args)

    # Register and monitor
    process = register_subprocess(
        f"workflow_{name}",
        cmd,
        capture_output=True
    )

    stdout, stderr = process.communicate()

    if process.returncode == 0:
        print(f"✅ Workflow '{name}' completed successfully")
        return stdout.decode()
    else:
        print(f"❌ Workflow '{name}' failed")
        raise RuntimeError(stderr.decode())

# Usage
output = run_workflow("backup", "--dest", "/mnt/backup")
```

---

## Scheduler & Automation

### Cron Scheduling

```python
from mcli.workflow.scheduler.cron_scheduler import CronScheduler
from datetime import datetime

scheduler = CronScheduler()

# Schedule command
job_id = scheduler.schedule_job(
    name="hourly_sync",
    schedule="0 * * * *",  # Every hour
    command=["mcli", "workflow", "sync_data"]
)

# Schedule Python function
def send_report():
    print(f"Sending report at {datetime.now()}")
    # Your logic

job_id = scheduler.schedule_job(
    name="daily_report",
    schedule="0 9 * * *",  # 9 AM daily
    command=send_report
)

# List scheduled jobs
jobs = scheduler.list_jobs()
for job in jobs:
    print(f"{job['name']}: {job['schedule']}")

# Remove job
scheduler.remove_job(job_id)
```

### Daemon Management

```python
from mcli.workflow.daemon.async_process_manager import AsyncProcessManager
from pathlib import Path

async def manage_daemons():
    # Create process manager
    manager = AsyncProcessManager(db_path=Path("~/.mcli/processes.db").expanduser())

    # Start a daemon process
    await manager.start_process(
        name="worker",
        command=["python", "worker.py"],
        env={"LOG_LEVEL": "INFO"}
    )

    # List running processes
    processes = await manager.list_processes(status="running")
    for proc in processes:
        print(f"{proc.name}: PID {proc.pid}")

    # Stop daemon
    await manager.stop_process("worker")

# Run async
import asyncio
asyncio.run(manage_daemons())
```

---

## Database Operations

### Supabase Integration

```python
from mcli.ml.database.supabase_client import get_supabase_client

# Get client (uses env vars SUPABASE_URL, SUPABASE_ANON_KEY)
supabase = get_supabase_client()

# Query data
response = supabase.table('workflows').select('*').execute()
workflows = response.data

# Insert data
new_workflow = {
    'name': 'etl_pipeline',
    'description': 'Extract, Transform, Load pipeline',
    'status': 'active'
}
supabase.table('workflows').insert(new_workflow).execute()

# Update data
supabase.table('workflows').update({'status': 'inactive'}).eq('name', 'old_pipeline').execute()

# Delete data
supabase.table('workflows').delete().eq('name', 'deprecated').execute()
```

### SQLAlchemy Models

```python
from mcli.ml.database.models import Base, WorkflowRun
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Create engine
engine = create_engine('sqlite:///workflows.db')
Base.metadata.create_all(engine)

# Create session
Session = sessionmaker(bind=engine)
session = Session()

# Create workflow run record
run = WorkflowRun(
    workflow_name="data_import",
    status="running",
    started_at=datetime.now()
)
session.add(run)
session.commit()

# Query runs
runs = session.query(WorkflowRun).filter_by(status="completed").all()
```

---

## Performance & Monitoring

### Performance Optimization

```python
from mcli.lib.performance.optimizer import PerformanceOptimizer
from mcli.lib.performance.cache import CacheManager

# Enable auto-optimization
optimizer = PerformanceOptimizer()
optimizer.enable_auto_optimize()

# Caching
cache = CacheManager()

@cache.cached(ttl=3600)  # Cache for 1 hour
def expensive_operation(param):
    # Your expensive computation
    return result

# Clear cache
cache.clear()
```

### Monitoring & Metrics

```python
from prometheus_client import Counter, Histogram
import time

# Define metrics
workflow_runs = Counter('workflow_runs_total', 'Total workflow executions')
workflow_duration = Histogram('workflow_duration_seconds', 'Workflow execution time')

# Instrument your code
@workflow_duration.time()
def run_workflow():
    workflow_runs.inc()
    # Your workflow logic
    time.sleep(2)

# Expose metrics (for Prometheus scraping)
from prometheus_client import start_http_server
start_http_server(8000)
```

---

## Advanced Patterns

### Plugin System

```python
from mcli.lib.custom_commands import get_command_manager
from pathlib import Path

class WorkflowPlugin:
    '''Base class for workflow plugins'''

    def __init__(self, name: str):
        self.name = name
        self.manager = get_command_manager()

    def register(self):
        '''Register plugin commands'''
        raise NotImplementedError

    def unregister(self):
        '''Remove plugin commands'''
        self.manager.delete_command(self.name)

class DataProcessingPlugin(WorkflowPlugin):
    def register(self):
        code = """
import click

@click.group(name='dataproc')
def dataproc():
    '''Data processing plugin'''
    pass

@dataproc.command('clean')
def clean():
    click.echo('Cleaning data...')
"""
        self.manager.save_command(
            name=self.name,
            code=code,
            description="Data processing utilities"
        )

# Use plugin
plugin = DataProcessingPlugin("dataproc")
plugin.register()
```

### Workflow Composition

```python
from typing import List, Callable

class WorkflowPipeline:
    '''Chain multiple workflows together'''

    def __init__(self, name: str):
        self.name = name
        self.steps: List[Callable] = []

    def add_step(self, step: Callable):
        '''Add workflow step'''
        self.steps.append(step)
        return self

    def execute(self, data):
        '''Execute pipeline'''
        result = data
        for i, step in enumerate(self.steps):
            print(f"Step {i+1}/{len(self.steps)}: {step.__name__}")
            result = step(result)
        return result

# Create pipeline
pipeline = WorkflowPipeline("etl")
pipeline.add_step(extract_data)
pipeline.add_step(transform_data)
pipeline.add_step(load_data)

# Execute
result = pipeline.execute(input_data)
```

### Event-Driven Workflows

```python
from typing import Dict, Callable, Any

class EventBus:
    '''Simple event bus for workflow coordination'''

    def __init__(self):
        self.handlers: Dict[str, List[Callable]] = {}

    def subscribe(self, event: str, handler: Callable):
        '''Subscribe to event'''
        if event not in self.handlers:
            self.handlers[event] = []
        self.handlers[event].append(handler)

    def publish(self, event: str, data: Any):
        '''Publish event'''
        if event in self.handlers:
            for handler in self.handlers[event]:
                handler(data)

# Usage
bus = EventBus()

def on_data_imported(data):
    print(f"Processing imported data: {len(data)} records")

def on_data_processed(data):
    print(f"Storing processed data")

bus.subscribe("data.imported", on_data_imported)
bus.subscribe("data.processed", on_data_processed)

# Trigger events
bus.publish("data.imported", {"records": 1000})
bus.publish("data.processed", {"records": 950})
```

---

## Internal Utilities & Services

These are powerful internal modules not directly exposed via CLI but available for library use.

### File System Operations (`mcli.lib.fs`)

```python
from mcli.lib.fs.fs import (
    safe_write,
    safe_read,
    atomic_write,
    ensure_directory
)

# Atomic file writes (prevents corruption)
atomic_write(Path("./config.json"), json.dumps(config))

# Safe read with fallback
content = safe_read(Path("./data.txt"), default="")

# Ensure directory exists
ensure_directory(Path("~/.mcli/data"))
```

### Configuration Management (`mcli.lib.config`)

```python
from mcli.lib.config.config import (
    get_config,
    save_config,
    load_config_file
)

# Load configuration
config = get_config()

# Access config values
debug_mode = config.get("debug", False)
workflows_dir = config.get("workflows_dir", "~/.mcli/workflows")

# Save configuration
save_config({"debug": True, "log_level": "INFO"})

# Load from specific file
custom_config = load_config_file(Path("./my-config.toml"))
```

### TOML Parsing (`mcli.lib.toml`)

```python
from mcli.lib.toml.toml import (
    load_toml,
    save_toml,
    parse_toml_string
)

# Load TOML file
config = load_toml(Path("./pyproject.toml"))

# Parse TOML string
data = parse_toml_string("""
[tool.mcli]
version = "1.0"
enabled = true
""")

# Save TOML
save_toml(Path("./output.toml"), {"project": {"name": "my-app"}})
```

### Script Synchronization (`mcli.lib.script_sync`)

```python
from mcli.workflow.script_sync import (
    ScriptSyncSystem,
    detect_script_language,
    extract_metadata
)

# Initialize sync system
sync = ScriptSyncSystem(
    scripts_dir=Path("./scripts"),
    commands_dir=Path("~/.mcli/commands").expanduser()
)

# Sync all scripts to JSON
synced_count = sync.sync_all_scripts()
print(f"Synced {synced_count} script(s)")

# Sync single script
sync.sync_single_script(Path("./scripts/backup.sh"))

# Detect language from file
language = detect_script_language(Path("./script.py"))  # Returns: "python"

# Extract metadata from script
metadata = extract_metadata(script_content)
# Returns: {"description": "...", "version": "...", "requires": [...], ...}

# Watch for changes (real-time sync)
sync.start_watch()  # Requires MCLI_WATCH_SCRIPTS=true
```

### File Watching (`mcli.lib.watcher`)

```python
from mcli.lib.watcher.watcher import FileWatcher
from pathlib import Path

def on_file_changed(path: Path):
    print(f"File changed: {path}")

def on_file_created(path: Path):
    print(f"File created: {path}")

# Create watcher
watcher = FileWatcher(
    watch_dir=Path("~/.mcli/workflows").expanduser(),
    on_modified=on_file_changed,
    on_created=on_file_created
)

# Start watching
watcher.start()

# Stop watching
watcher.stop()
```

### Package.json Workflow Integration (`mcli.lib.packagejson_workflows`)

```python
from mcli.lib.packagejson_workflows import (
    PackageJsonWorkflowManager,
    detect_package_json
)

# Detect package.json in current directory
package_json = detect_package_json()

if package_json:
    # Load npm scripts as workflows
    manager = PackageJsonWorkflowManager(package_json)

    # List available scripts
    scripts = manager.list_scripts()
    for name, command in scripts.items():
        print(f"{name}: {command}")

    # Execute npm script via mcli
    manager.run_script("test", args=["--verbose"])
```

### Authentication & Credentials (`mcli.lib.auth`)

```python
from mcli.lib.auth.auth import (
    authenticate_user,
    get_current_user,
    validate_token
)
from mcli.lib.auth.key_manager import KeyManager
from mcli.lib.auth.credential_manager import CredentialManager
from mcli.lib.auth.token_manager import TokenManager

# Key management
key_mgr = KeyManager()
api_key = key_mgr.get_key("openai")
key_mgr.set_key("anthropic", "sk-ant-xxx")
key_mgr.delete_key("old_service")

# Credential management
cred_mgr = CredentialManager()
cred_mgr.store_credential("database", {
    "host": "localhost",
    "username": "admin",
    "password": "secret"
})
db_creds = cred_mgr.get_credential("database")

# Token management (JWT, OAuth)
token_mgr = TokenManager()
token = token_mgr.generate_token(user_id="123", exp_hours=24)
is_valid = token_mgr.validate_token(token)
payload = token_mgr.decode_token(token)
```

### Entity Relationship Diagrams (`mcli.lib.erd`)

```python
from mcli.lib.erd.erd import generate_erd
from mcli.lib.erd.generate_graph import create_graph

# Generate ERD from SQLAlchemy models
from mcli.ml.database.models import Base

# Create ERD graph
graph = generate_erd(Base)

# Save as image
graph.render("database_schema", format="png")

# Or create custom graph
from graphviz import Digraph

dot = create_graph()
dot.node("User", "User\n- id\n- name\n- email")
dot.node("Workflow", "Workflow\n- id\n- name\n- status")
dot.edge("User", "Workflow", "owns")
dot.render("custom_diagram")
```

### Performance Optimization (`mcli.lib.performance`)

```python
from mcli.lib.performance.optimizer import (
    PerformanceOptimizer,
    enable_optimizations,
    profile_function
)
from mcli.lib.performance.uvloop_config import use_uvloop
from mcli.lib.performance.rust_bridge import (
    rust_tfidf_vectorize,
    rust_file_hash
)

# Enable performance optimizations
optimizer = PerformanceOptimizer()
optimizer.enable_auto_optimize()

# Use uvloop for async operations
use_uvloop()

# Profile function performance
@profile_function
def expensive_operation():
    # Your code
    pass

# Use Rust-accelerated operations
# TF-IDF vectorization (fast text analysis)
vectors = rust_tfidf_vectorize([
    "first document",
    "second document with more words"
])

# Fast file hashing
file_hash = rust_file_hash(Path("./large_file.dat"))
```

### Redis Service Integration (`mcli.lib.services.redis_service`)

```python
from mcli.lib.services.redis_service import (
    RedisService,
    get_redis_client,
    cache_result
)

# Get Redis client
redis = get_redis_client()

# Basic operations
redis.set("key", "value", ex=3600)  # Expire in 1 hour
value = redis.get("key")

# Use as cache decorator
@cache_result(ttl=300)  # Cache for 5 minutes
def expensive_query(param):
    # Your expensive operation
    return result

# Redis service wrapper
service = RedisService()

# Pub/Sub
service.publish("channel", "message")
for message in service.subscribe("channel"):
    print(message)

# Distributed lock
with service.lock("resource_name", timeout=10):
    # Critical section
    pass
```

### LSH Client Integration (`mcli.lib.services.lsh_client`)

```python
from mcli.lib.services.lsh_client import LSHClient

# Connect to LSH service
lsh = LSHClient(base_url="http://localhost:3000")

# Store secret
lsh.set_secret("API_KEY", "your-secret-value")

# Retrieve secret
api_key = lsh.get_secret("API_KEY")

# List secrets
secrets = lsh.list_secrets()

# Delete secret
lsh.delete_secret("OLD_KEY")
```

### Data Pipeline Services (`mcli.lib.services.data_pipeline`)

```python
from mcli.lib.services.data_pipeline import (
    DataPipeline,
    PipelineStage,
    create_pipeline
)

# Define pipeline stages
class ExtractStage(PipelineStage):
    def process(self, data):
        # Extract logic
        return extracted_data

class TransformStage(PipelineStage):
    def process(self, data):
        # Transform logic
        return transformed_data

class LoadStage(PipelineStage):
    def process(self, data):
        # Load logic
        return loaded_data

# Create and run pipeline
pipeline = create_pipeline([
    ExtractStage(),
    TransformStage(),
    LoadStage()
])

result = pipeline.run(input_data)
```

### API Decorators (`mcli.lib.api.mcli_decorators`)

```python
from mcli.lib.api.mcli_decorators import (
    rate_limit,
    require_auth,
    log_execution,
    retry_on_failure
)

# Rate limiting
@rate_limit(max_calls=100, period=60)  # 100 calls per minute
def api_endpoint():
    pass

# Authentication required
@require_auth
def protected_endpoint():
    pass

# Execution logging
@log_execution
def important_function():
    pass

# Auto-retry on failure
@retry_on_failure(max_retries=3, backoff=2)
def flaky_operation():
    pass
```

### Daemon Client (`mcli.lib.api.daemon_client`)

```python
from mcli.lib.api.daemon_client import DaemonClient
from mcli.lib.api.daemon_client_local import LocalDaemonClient

# Connect to daemon
client = DaemonClient(host="localhost", port=8000)

# Or use local client
local_client = LocalDaemonClient()

# Start workflow via daemon
job_id = client.start_workflow("backup", args=["--dest", "/mnt/backup"])

# Check status
status = client.get_status(job_id)

# Stop workflow
client.stop_workflow(job_id)

# List running workflows
workflows = client.list_workflows()
```

### Visual Effects (`mcli.lib.ui.visual_effects`)

```python
from mcli.lib.ui.visual_effects import (
    spinner,
    progress_bar,
    animate_text,
    show_banner
)

# Spinner for long operations
with spinner("Processing..."):
    # Your long operation
    time.sleep(5)

# Progress bar
for i in progress_bar(range(100), description="Loading"):
    time.sleep(0.1)

# Animated text
animate_text("MCLI Framework", style="wave")

# Show banner
show_banner("Workflow Complete!", style="success")
```

### Optional Dependencies Management (`mcli.lib.optional_deps`)

```python
from mcli.lib.optional_deps import (
    check_optional_dependency,
    import_optional,
    get_missing_dependencies
)

# Check if optional dependency is available
if check_optional_dependency("redis"):
    import redis
    # Use Redis

# Import with fallback
torch = import_optional("torch", fallback=None)
if torch:
    # Use PyTorch

# Get list of missing optional dependencies
missing = get_missing_dependencies(["redis", "torch", "opencv"])
if missing:
    print(f"Missing: {', '.join(missing)}")
```

---

## API Reference

### Core Classes

#### `CustomCommandManager`
- `save_command(name, code, description, group=None, metadata=None)` - Save workflow command
- `load_command(command_file)` - Load command from JSON file
- `load_all_commands()` - Load all commands
- `delete_command(name)` - Delete command
- `update_lockfile()` - Update lockfile
- `verify_lockfile()` - Verify lockfile integrity
- `export_commands(path)` - Export commands to JSON
- `import_commands(path, overwrite=False)` - Import commands from JSON

#### `ClickCommandDiscovery`
- `discover_all_commands()` - Discover all Click commands
- `discover_from_module(module_name)` - Discover commands from module
- `get_command_info(cmd)` - Get command metadata

#### `CronScheduler`
- `schedule_job(name, schedule, command)` - Schedule cron job
- `list_jobs()` - List all scheduled jobs
- `remove_job(job_id)` - Remove scheduled job
- `get_job(job_id)` - Get job details

#### `AsyncProcessManager`
- `start_process(name, command, env=None)` - Start daemon process
- `stop_process(name)` - Stop running process
- `list_processes(status=None)` - List processes
- `get_process_info(name)` - Get process details

### Utility Functions

```python
from mcli.lib.paths import (
    get_custom_commands_dir,
    get_lockfile_path,
    get_git_root,
    is_git_repository
)

from mcli.lib.logger.logger import (
    get_logger,
    register_subprocess
)

from mcli.lib.ui.styling import (
    success, error, info, warning
)
```

---

## Complete Example: ETL Pipeline

```python
#!/usr/bin/env python3
"""
Complete example: Build an ETL pipeline using mcli-framework
"""

import click
from pathlib import Path
from mcli.lib.custom_commands import get_command_manager
from mcli.lib.logger.logger import get_logger
from mcli.workflow.scheduler.cron_scheduler import CronScheduler

logger = get_logger()

# Define ETL workflow
etl_code = """
import click
import pandas as pd
from pathlib import Path
from datetime import datetime

@click.group(name='etl')
def etl_group():
    '''ETL Pipeline Commands'''
    pass

@etl_group.command('extract')
@click.argument('source', type=click.Path(exists=True))
@click.option('--output', type=click.Path(), default='./data/raw.csv')
def extract(source, output):
    '''Extract data from source'''
    click.echo(f'Extracting from {source}...')
    # Your extraction logic
    df = pd.read_csv(source)
    df.to_csv(output, index=False)
    click.echo(f'✅ Extracted {len(df)} records to {output}')

@etl_group.command('transform')
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--output', type=click.Path(), default='./data/transformed.csv')
def transform(input_file, output):
    '''Transform data'''
    click.echo(f'Transforming {input_file}...')
    df = pd.read_csv(input_file)
    # Your transformation logic
    df['processed_at'] = datetime.now().isoformat()
    df.to_csv(output, index=False)
    click.echo(f'✅ Transformed {len(df)} records to {output}')

@etl_group.command('load')
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--table', required=True)
def load(input_file, table):
    '''Load data to database'''
    click.echo(f'Loading {input_file} to table {table}...')
    df = pd.read_csv(input_file)
    # Your loading logic (database insert)
    click.echo(f'✅ Loaded {len(df)} records to {table}')

@etl_group.command('run')
@click.argument('source', type=click.Path(exists=True))
@click.option('--table', required=True)
def run_pipeline(source, table):
    '''Run complete ETL pipeline'''
    from click.testing import CliRunner

    runner = CliRunner()

    # Extract
    result = runner.invoke(extract, [source])
    if result.exit_code != 0:
        raise RuntimeError('Extract failed')

    # Transform
    result = runner.invoke(transform, ['./data/raw.csv'])
    if result.exit_code != 0:
        raise RuntimeError('Transform failed')

    # Load
    result = runner.invoke(load, ['./data/transformed.csv', '--table', table])
    if result.exit_code != 0:
        raise RuntimeError('Load failed')

    click.echo('✅ Pipeline completed successfully')
"""

def main():
    # Create command manager
    manager = get_command_manager(global_mode=True)

    # Register ETL workflow
    logger.info("Registering ETL workflow...")
    manager.save_command(
        name="etl",
        code=etl_code,
        description="Extract, Transform, Load pipeline",
        group="data",
        metadata={
            "author": "Data Team",
            "version": "1.0.0",
            "requires": ["pandas"],
            "tags": ["etl", "data", "pipeline"]
        }
    )

    # Schedule daily run
    logger.info("Scheduling daily ETL run...")
    scheduler = CronScheduler()
    scheduler.schedule_job(
        name="daily_etl",
        schedule="0 2 * * *",  # 2 AM daily
        command=["mcli", "workflow", "etl", "run", "/data/source.csv", "--table", "analytics"]
    )

    logger.info("✅ ETL Pipeline setup complete!")
    logger.info("Run with: mcli workflow etl run <source> --table <table>")
    logger.info("Or individual steps:")
    logger.info("  mcli workflow etl extract <source>")
    logger.info("  mcli workflow etl transform <input>")
    logger.info("  mcli workflow etl load <input> --table <table>")

if __name__ == "__main__":
    main()
```

---

## Support & Resources

- **GitHub**: https://github.com/gwicho38/mcli
- **Issues**: https://github.com/gwicho38/mcli/issues
- **PyPI**: https://pypi.org/project/mcli-framework/
- **Documentation**: https://github.com/gwicho38/mcli/tree/main/docs

For detailed examples, see the [examples/](https://github.com/gwicho38/mcli/tree/main/examples) directory.
