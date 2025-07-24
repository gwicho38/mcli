# MCLI Library Packaging Guide

This guide explains how to package and use the `mcli` project as a Python library.

## Overview

The `mcli` project is already configured as a Python library with:
- Modern `pyproject.toml` configuration
- Proper package structure in `src/mcli/`
- CLI entry points
- Comprehensive dependencies
- Build system using setuptools and wheel

## Building the Library

### 1. Build the Wheel Package

```bash
# Setup the environment
make setup

# Build the wheel package
make wheel
```

This creates a wheel file in `dist/` directory (e.g., `mcli-5.0.0-py3-none-any.whl`).

### 2. Install the Library

#### Option A: Install from Wheel
```bash
# Install the built wheel
pip install dist/mcli-5.0.0-py3-none-any.whl
```

#### Option B: Install in Development Mode
```bash
# Install in editable mode for development
pip install -e .
```

#### Option C: Install with UV
```bash
# Using UV package manager
uv pip install dist/mcli-5.0.0-py3-none-any.whl
```

## Using MCLI as a Library

### Basic Usage

Once installed, you can import and use mcli modules in your Python scripts:

```python
# Import core modules
from mcli.lib.logger.logger import get_logger
from mcli.lib.config.config import Config
from mcli.lib.fs.fs import FileSystem

# Initialize components
logger = get_logger("my_app")
config = Config()
fs = FileSystem()

# Use the functionality
logger.info("Using mcli library!")
```

### Available Modules

#### Core Library Modules (`mcli.lib.*`)
- **Logger**: `mcli.lib.logger.logger` - Structured logging
- **Config**: `mcli.lib.config.config` - Configuration management
- **File System**: `mcli.lib.fs.fs` - File system operations
- **API**: `mcli.lib.api.api` - API client functionality
- **Auth**: `mcli.lib.auth.auth` - Authentication management
- **Shell**: `mcli.lib.shell.shell` - Shell command execution
- **Watcher**: `mcli.lib.watcher.watcher` - File watching
- **TOML**: `mcli.lib.toml.toml` - TOML file handling

#### Workflow Modules (`mcli.workflow.*`)
- **Repository**: `mcli.workflow.repo.repo` - Git repository operations
- **File**: `mcli.workflow.file.file` - File processing workflows
- **Docker**: `mcli.workflow.docker.docker` - Docker operations
- **GCloud**: `mcli.workflow.gcloud.gcloud` - Google Cloud operations
- **WebApp**: `mcli.workflow.webapp.webapp` - Web application tools
- **Videos**: `mcli.workflow.videos.videos` - Video processing
- **Model Service**: `mcli.workflow.model_service.model_service` - ML model management

#### Public Modules (`mcli.public.*`)
- **OI**: `mcli.public.oi.oi` - Open Interpreter integration
- **Public**: `mcli.public.public` - Public utilities

### Example Usage Patterns

#### 1. Logging and Configuration
```python
from mcli.lib.logger.logger import get_logger
from mcli.lib.config.config import Config

# Setup logging
logger = get_logger("my_application")
config = Config()

# Use logging
logger.info("Application started")
logger.debug(f"Config loaded: {config}")
```

#### 2. File System Operations
```python
from mcli.lib.fs.fs import FileSystem

fs = FileSystem()

# File operations
if fs.file_exists("my_file.txt"):
    content = fs.read_file("my_file.txt")
    print(f"File content: {content}")
```

#### 3. Repository Operations
```python
from mcli.workflow.repo.repo import RepoWorkflow

repo = RepoWorkflow()

# Git operations
status = repo.get_status()
print(f"Repository status: {status}")
```

#### 4. API Client Usage
```python
from mcli.lib.api.api import APIClient

api = APIClient()

# Make API calls
response = api.get("/some/endpoint")
print(f"API response: {response}")
```

#### 5. Authentication
```python
from mcli.lib.auth.auth import AuthManager

auth = AuthManager()

# Handle authentication
if auth.is_authenticated():
    print("User is authenticated")
else:
    print("Authentication required")
```

## Distribution Options

### 1. Local Installation
```bash
# Install locally for development
pip install -e .
```

### 2. Wheel Distribution
```bash
# Build wheel
make wheel

# Distribute wheel file
# Share the .whl file with others
```

### 3. PyPI Distribution (Future)
```bash
# Build and upload to PyPI
make wheel
twine upload dist/*
```

### 4. Private Repository
```bash
# Upload to private PyPI server
twine upload --repository-url https://your-private-pypi.com/ dist/*
```

## Package Structure

The mcli package structure:

```
mcli/
├── __init__.py              # Package initialization
├── app/                     # Main application
│   ├── main.py             # CLI entry point
│   ├── globals.py          # Global variables
│   └── model/              # Model-related functionality
├── lib/                     # Core library modules
│   ├── logger/             # Logging functionality
│   ├── config/             # Configuration management
│   ├── fs/                 # File system operations
│   ├── api/                # API client
│   ├── auth/               # Authentication
│   └── shell/              # Shell operations
├── workflow/                # Workflow modules
│   ├── repo/               # Repository operations
│   ├── file/               # File processing
│   ├── docker/             # Docker operations
│   └── webapp/             # Web application tools
└── public/                  # Public modules
    ├── oi/                 # Open Interpreter
    └── public.py           # Public utilities
```

## Dependencies

The library includes comprehensive dependencies for:
- **CLI**: Click, IPython, ptpython
- **Data Processing**: Pandas, NumPy, scikit-learn
- **ML/AI**: Transformers, Torch, Keras
- **Web**: Flask, FastAPI, uvicorn
- **Cloud**: Docker, Google Cloud
- **Utilities**: Rich, tqdm, humanize

## Testing the Library

### Run the Example
```bash
# Test the library usage example
python example_library_usage.py
```

### Test Individual Modules
```python
# Test specific functionality
from mcli.lib.logger.logger import get_logger
logger = get_logger("test")
logger.info("Library test successful!")
```

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Ensure the package is installed
   pip install -e .
   
   # Check Python path
   python -c "import mcli; print(mcli.__file__)"
   ```

2. **Missing Dependencies**
   ```bash
   # Install all dependencies
   make setup
   ```

3. **Version Conflicts**
   ```bash
   # Check installed version
   pip show mcli
   
   # Reinstall if needed
   pip uninstall mcli
   pip install -e .
   ```

## Best Practices

### 1. Import Specific Modules
```python
# Good: Import specific modules
from mcli.lib.logger.logger import get_logger

# Avoid: Import everything
from mcli import *
```

### 2. Handle Import Errors
```python
try:
    from mcli.lib.logger.logger import get_logger
    logger = get_logger("my_app")
except ImportError:
    # Fallback logging
    import logging
    logger = logging.getLogger("my_app")
```

### 3. Use Configuration
```python
from mcli.lib.config.config import Config

config = Config()
# Use configuration for settings
```

### 4. Error Handling
```python
from mcli.lib.fs.fs import FileSystem

fs = FileSystem()
try:
    content = fs.read_file("file.txt")
except FileNotFoundError:
    print("File not found")
```

## Integration Examples

### 1. Web Application Integration
```python
from flask import Flask
from mcli.lib.logger.logger import get_logger
from mcli.lib.config.config import Config

app = Flask(__name__)
logger = get_logger("webapp")
config = Config()

@app.route('/')
def home():
    logger.info("Home page accessed")
    return "Hello from mcli-powered app!"
```

### 2. Data Processing Pipeline
```python
from mcli.lib.logger.logger import get_logger
from mcli.workflow.file.file import FileWorkflow

logger = get_logger("pipeline")
file_workflow = FileWorkflow()

def process_data():
    logger.info("Starting data processing")
    # Use file workflow for processing
    result = file_workflow.process_files("data/")
    logger.info(f"Processing complete: {result}")
```

### 3. CLI Tool Integration
```python
import click
from mcli.lib.logger.logger import get_logger

logger = get_logger("cli_tool")

@click.command()
@click.option('--input', '-i', help='Input file')
def process(input):
    logger.info(f"Processing input: {input}")
    # Your processing logic here
```

## Conclusion

The `mcli` project is designed to be used both as a CLI tool and as a Python library. The modular structure allows you to import and use specific functionality as needed, while the comprehensive dependency management ensures all required packages are available.

For more information, see:
- `pyproject.toml` - Package configuration
- `MANIFEST.in` - Package file inclusion
- `example_library_usage.py` - Usage examples
- `Makefile` - Build targets 