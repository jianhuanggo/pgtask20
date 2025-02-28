# Production-Grade Logging for Python

This module provides a comprehensive, production-grade logging system for Python applications with the following features:

## Features

- **Multiple log levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Configurable log formats**: Standard text format and structured JSON format
- **Multiple output handlers**: Console, file, rotating file
- **Context information**: Timestamps, module names, line numbers, file names
- **Exception tracking**: Detailed exception information including stack traces
- **Thread safety**: Thread-safe logger creation and management
- **Performance optimizations**: Logger caching to avoid overhead
- **Structured logging**: JSON output format for log aggregation systems

## Logger Selection Guide

Choose the appropriate logger based on your needs:

| Logger Type | Use Case | Features | When to Use |
|-------------|----------|----------|-------------|
| `get_logger()` | General purpose | Simple setup, module name detection | For most application logging needs |
| `get_json_logger()` | Structured logging | JSON output format | When integrating with log aggregation systems (ELK, Splunk) |
| `PGLogger.get_logger()` | Advanced configuration | Full control over all options | When you need custom configuration |
| `PGLoggerSingleton()` | Application-wide logging | Shared logger instance | For global logging across your application |
| `setup_log()` | File logging with rotation | Configurable rotation settings | For production services that need log rotation |

### Detailed Usage Recommendations

1. **For Simple Applications**:
   - Use `get_logger()` for most components
   - Use `get_json_logger()` if you need structured logging

2. **For Microservices**:
   - Use `setup_log()` with appropriate rotation settings
   - Configure log levels based on environment (DEBUG in dev, INFO/WARNING in prod)

3. **For Large Applications**:
   - Use `PGLoggerSingleton()` for application-wide logging
   - Use `PGLogger.get_logger()` for components with special requirements

4. **For High-Volume Services**:
   - Always enable log rotation with appropriate `max_bytes` and `backup_count`
   - Consider using JSON logging for easier log processing

## Usage Examples

### Basic Usage

```python
from _logging import get_logger

# Create a logger with default settings
logger = get_logger("my_module")

# Log messages at different levels
logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
logger.critical("Critical message")

# Log exceptions
try:
    1/0
except Exception as e:
    logger.exception("An error occurred")
```

### JSON Logging

```python
from _logging import get_json_logger

# Create a logger that outputs in JSON format
logger = get_json_logger("my_module")

logger.info("This will be output as JSON")
```

### Method Logging Decorator

```python
from _logging import log_method, get_logger

class MyClass:
    def __init__(self):
        self.logger = get_logger("my_class")
    
    @log_method(level="info", include_args=True, include_return=True)
    def my_method(self, arg1, arg2, password=None):
        # Method implementation
        return result
```

### File Logging with Rotation

```python
from _logging import PGLogger

# Create a logger that logs to both console and file with automatic rotation
logger = PGLogger.get_logger(
    name="my_app",
    log_to_console=True,
    log_to_file=True,
    log_file_path="/var/log/my_app.log",
    max_bytes=10485760,  # 10MB - maximum size before rotation
    backup_count=10      # Keep 10 backup files (my_app.log.1, my_app.log.2, etc.)
)
```

The file logger automatically implements log rotation using Python's `RotatingFileHandler`. When the log file reaches the specified `max_bytes` size, it will be renamed with a suffix (e.g., `.1`) and a new log file will be created. This prevents log files from growing indefinitely and consuming all available disk space.

For time-based rotation instead of size-based, use the `setup_log` function with custom handlers:

```python
import logging
from logging.handlers import TimedRotatingFileHandler
from _logging import get_logger

# Create a logger
logger = get_logger("time_rotating_app")

# Add a time-rotating handler (rotate daily at midnight)
handler = TimedRotatingFileHandler(
    "/var/log/my_app.log",
    when="midnight",
    interval=1,
    backupCount=30  # Keep 30 days of logs
)
handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)
```

### Singleton Logger

```python
from _logging import PGLoggerSingleton

# Get the singleton logger instance
logger = PGLoggerSingleton()

# Log messages
logger.info("Using the singleton logger")
```

## Configuration

The default log directory can be configured through the `PG_LOG_DIR` environment variable.
If not set, it defaults to `/var/log/pgtask`.
