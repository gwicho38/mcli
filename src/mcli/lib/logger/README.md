# mcli Logger

## Overview

The `mcli.out` logger provides centralized logging for the MCLI application, writing logs to both the console and a file in the top-level `logs` directory.

## Usage

Import and use the logger in your modules:

```python
from mcli.lib.logger import get_logger

# Get logger instance
logger = get_logger()

# Log messages at different levels
logger.debug("Detailed information, typically of interest only when diagnosing problems")
logger.info("Confirmation that things are working as expected")
logger.warning("An indication that something unexpected happened, or may happen in the near future")
logger.error("Due to a more serious problem, the software has not been able to perform some function")
logger.critical("A serious error, indicating that the program itself may be unable to continue running")
```

## Log Levels

- **DEBUG**: Detailed information, typically of interest only when diagnosing problems
- **INFO**: Confirmation that things are working as expected
- **WARNING**: An indication that something unexpected happened, or may happen in the near future
- **ERROR**: Due to a more serious problem, the software has not been able to perform some function
- **CRITICAL**: A serious error, indicating that the program itself may be unable to continue running

## Log Output

- **Console**: Logs at INFO level and above are displayed in the console
- **File**: All logs (DEBUG and above) are written to a date-stamped file in the `/logs` directory

## File Location

Log files are stored in the top-level `logs` directory with the naming pattern `mcli_YYYYMMDD.log`.

## Tracing and Monitoring

The logger module provides two distinct types of tracing for debugging and monitoring:

1. **Python Interpreter Runtime Tracing**: Monitors the execution flow within Python code
2. **System Process Tracing**: Monitors processes at the OS level, including resource usage and state

### Python Interpreter Runtime Tracing

This feature traces Python interpreter execution for debugging and performance analysis. This is especially useful for:

- Understanding the execution flow of your application
- Identifying performance bottlenecks
- Debugging complex issues in a production environment

#### Trace Levels

Runtime tracing is controlled by the `MCLI_TRACE_LEVEL` environment variable and can be set to different levels:

- `0`: Tracing disabled (default)
- `1`: Function call tracing - logs all function entries
- `2`: Line-by-line tracing - logs each line execution (high volume)
- `3`: Verbose tracing - includes function parameters, return values, and source lines

#### Enabling Runtime Tracing

To enable tracing, set the environment variable before running the application:

```bash
# Enable function call tracing
export MCLI_TRACE_LEVEL=1
python -m mcli

# Enable verbose tracing
export MCLI_TRACE_LEVEL=3
python -m mcli
```

You can also enable tracing programmatically:

```python
from mcli.lib.logger.logger import enable_runtime_tracing, disable_runtime_tracing

# Enable function call tracing
enable_runtime_tracing(level=1)

# Enable verbose tracing
enable_runtime_tracing(level=3)

# Custom module exclusion list
enable_runtime_tracing(level=1, excluded_modules=['some_noisy_module'])

# Disable tracing
disable_runtime_tracing()
```

#### Trace Log Files

Trace logs are written to a separate log file in the logs directory:
`logs/mcli_trace_YYYYMMDD.log`

### System Process Tracing

This feature monitors OS-level processes, providing visibility into how processes are behaving at the system level. This is particularly useful for:

- Diagnosing process stalls or hangs
- Identifying resource-intensive operations
- Tracking subprocess creation and termination
- Monitoring OS resource usage (CPU, memory, I/O)
- Ensuring processes aren't locked or deadlocked

#### System Trace Levels

System tracing is controlled by the `MCLI_SYSTEM_TRACE_LEVEL` environment variable:

- `0`: System tracing disabled (default)
- `1`: Basic process monitoring - tracks process status, CPU/memory usage, and runtime
- `2`: Detailed process monitoring - adds command line arguments, open files, child processes, I/O statistics, and more

#### Configuring System Tracing

To enable system tracing, set the environment variables before running the application:

```bash
# Enable basic system tracing with default 5-second interval
export MCLI_SYSTEM_TRACE_LEVEL=1
python -m mcli

# Enable detailed system tracing with custom 10-second interval
export MCLI_SYSTEM_TRACE_LEVEL=2
export MCLI_SYSTEM_TRACE_INTERVAL=10
python -m mcli
```

You can also enable system tracing programmatically:

```python
from mcli.lib.logger.logger import enable_system_tracing, disable_system_tracing, register_process, register_subprocess

# Enable basic system tracing with default 5-second interval
enable_system_tracing(level=1)

# Enable detailed system tracing with custom 2-second interval
enable_system_tracing(level=2, interval=2)

# Register additional processes to monitor
pid = 12345  # Some external process ID
register_process(pid)

# Register a subprocess created with subprocess.Popen
proc = subprocess.Popen(['some_command', 'arg1', 'arg2'])
register_subprocess(proc)

# Disable system tracing
disable_system_tracing()
```

#### System Trace Log Files

System trace logs are written to a separate log file in the logs directory:
`logs/mcli_system_YYYYMMDD.log`

### Performance Considerations

- **Runtime tracing**, especially at levels 2 and 3, can significantly impact application performance. It's recommended to use level 1 for most troubleshooting scenarios and only use levels 2 and 3 for short periods when detailed debugging is necessary.

- **System tracing** has a much lower overhead but still consumes resources for monitoring. The interval parameter controls how frequently processes are checked; shorter intervals provide more detailed data but increase overhead.

- When using both types of tracing simultaneously, consider using lower levels of each to minimize performance impact.