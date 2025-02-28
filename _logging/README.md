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

### File Logging

```python
from _logging import PGLogger

# Create a logger that logs to both console and file
logger = PGLogger.get_logger(
    name="my_app",
    log_to_console=True,
    log_to_file=True,
    log_file_path="/var/log/my_app.log",
    max_bytes=10485760,  # 10MB
    backup_count=10
)
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
