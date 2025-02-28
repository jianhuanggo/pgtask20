"""
Production-grade logging module for Python applications.

This module provides a comprehensive logging system with the following features:
- Multiple log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Configurable log formats
- Multiple output handlers (console, file, rotating file, etc.)
- Context information (timestamps, module names, line numbers)
- Exception tracking
- Thread safety
- Performance considerations
- Structured logging support (JSON)
"""

import logging
import os
import sys
import json
import traceback
import threading
import functools
import datetime
from typing import Dict, Any, Optional, Union, Callable, TypeVar, List, Tuple
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path

# Type variables for function decorators
RT = TypeVar('RT')  # Return type

# Default log format with detailed context information
DEFAULT_FORMAT = "%(asctime)s - %(levelname)s - [%(name)s:%(filename)s:%(lineno)d] - %(message)s"
# JSON format for structured logging
JSON_FORMAT = '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "file": "%(filename)s", "line": %(lineno)d, "message": "%(message)s"}'

# Default log directory
DEFAULT_LOG_DIR = os.environ.get("PG_LOG_DIR", "/var/log/pgtask")


class JsonFormatter(logging.Formatter):
    """
    Custom formatter that outputs log records as JSON objects.
    Useful for log aggregation systems like ELK stack.
    """
    def __init__(self, fmt=None, datefmt=None, style='%', ensure_ascii=False):
        super().__init__(fmt, datefmt, style)
        self.ensure_ascii = ensure_ascii

    def format(self, record):
        log_record = {}
        
        # Standard log record attributes
        log_record["timestamp"] = self.formatTime(record, self.datefmt)
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["file"] = record.filename
        log_record["line"] = record.lineno
        log_record["message"] = record.getMessage()
        
        # Add exception info if available
        if record.exc_info:
            log_record["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields from record
        if hasattr(record, "extra") and record.extra:
            log_record.update(record.extra)
        
        return json.dumps(log_record, ensure_ascii=self.ensure_ascii)


class PGLogger:
    """
    Production-grade logger class that provides enhanced logging capabilities.
    """
    _loggers = {}  # Class-level cache of logger instances
    _lock = threading.RLock()  # Thread-safe lock for logger creation
    
    @classmethod
    def get_logger(cls, 
                  name: str, 
                  log_level: int = logging.INFO, 
                  log_format: str = DEFAULT_FORMAT,
                  log_to_console: bool = True,
                  log_to_file: bool = False,
                  log_file_path: Optional[str] = None,
                  max_bytes: int = 10485760,  # 10MB
                  backup_count: int = 10,
                  use_json_format: bool = False,
                  propagate: bool = False) -> logging.Logger:
        """
        Get or create a logger with the specified configuration.
        
        Args:
            name: Name of the logger
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_format: Format string for log messages
            log_to_console: Whether to log to console
            log_to_file: Whether to log to file
            log_file_path: Path to log file (if None, uses DEFAULT_LOG_DIR/name.log)
            max_bytes: Maximum size of log file before rotation
            backup_count: Number of backup files to keep
            use_json_format: Whether to use JSON formatting for logs
            propagate: Whether to propagate logs to parent loggers
            
        Returns:
            Configured logger instance
        """
        # Use the fully qualified name as the logger name
        logger_name = name
        
        # Check if logger already exists in cache
        with cls._lock:
            if logger_name in cls._loggers:
                return cls._loggers[logger_name]
            
            # Create new logger
            logger = logging.getLogger(logger_name)
            
            # Clear any existing handlers
            if logger.handlers:
                logger.handlers.clear()
            
            # Set log level
            logger.setLevel(log_level)
            
            # Set propagation
            logger.propagate = propagate
            
            # Create formatter
            if use_json_format:
                formatter = JsonFormatter()
            else:
                formatter = logging.Formatter(log_format)
            
            # Add console handler if requested
            if log_to_console:
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setFormatter(formatter)
                logger.addHandler(console_handler)
            
            # Add file handler if requested
            if log_to_file:
                if not log_file_path:
                    # Create default log directory if it doesn't exist
                    os.makedirs(DEFAULT_LOG_DIR, exist_ok=True)
                    log_file_path = os.path.join(DEFAULT_LOG_DIR, f"{name}.log")
                else:
                    # Ensure directory exists
                    log_dir = os.path.dirname(log_file_path)
                    if log_dir:
                        os.makedirs(log_dir, exist_ok=True)
                
                file_handler = RotatingFileHandler(
                    log_file_path,
                    maxBytes=max_bytes,
                    backupCount=backup_count
                )
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)
            
            # Cache the logger
            cls._loggers[logger_name] = logger
            
            return logger


class PGLoggerSingleton:
    """
    Singleton class for accessing a default logger instance.
    """
    _instance = None
    _lock = threading.RLock()
    
    def __new__(cls, 
                name: str = "pgtask", 
                log_file_path: Optional[str] = None,
                log_level: int = logging.INFO,
                log_to_console: bool = True,
                log_to_file: bool = True,
                use_json_format: bool = False):
        with cls._lock:
            if cls._instance is None:
                cls._instance = PGLogger.get_logger(
                    name=name,
                    log_level=log_level,
                    log_to_console=log_to_console,
                    log_to_file=log_to_file,
                    log_file_path=log_file_path,
                    use_json_format=use_json_format
                )
            return cls._instance


def setup_log(log_name: str, log_filepath: str, 
              log_level: int = logging.INFO,
              max_bytes: int = 10485760,  # 10MB
              backup_count: int = 10,
              log_to_console: bool = True,
              use_json_format: bool = False) -> logging.Logger:
    """
    Set up a logger with rotation.
    
    Args:
        log_name: Name of the logger
        log_filepath: Path to the log file
        log_level: Logging level
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
        log_to_console: Whether to log to console
        use_json_format: Whether to use JSON formatting
        
    Returns:
        Configured logger instance
    """
    return PGLogger.get_logger(
        name=log_name,
        log_level=log_level,
        log_to_console=log_to_console,
        log_to_file=True,
        log_file_path=log_filepath,
        max_bytes=max_bytes,
        backup_count=backup_count,
        use_json_format=use_json_format
    )


def log_method(level: str = "info", 
               include_args: bool = True, 
               include_return: bool = False,
               exclude_args: List[str] = None):
    """
    Decorator for logging method calls with arguments and return values.
    
    Args:
        level: Log level to use (debug, info, warning, error, critical)
        include_args: Whether to include arguments in the log
        include_return: Whether to include return value in the log
        exclude_args: List of argument names to exclude from logging (e.g., passwords)
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get logger from first argument (self) if it's a method
            logger = None
            if args and hasattr(args[0], "__class__"):
                # Try to find a logger attribute in the instance
                for attr_name in dir(args[0]):
                    attr = getattr(args[0], attr_name)
                    if isinstance(attr, logging.Logger):
                        logger = attr
                        break
            
            # If no logger found, create a default one
            if logger is None:
                logger = PGLogger.get_logger(func.__module__)
            
            # Get log method based on level
            log_func = getattr(logger, level.lower(), logger.info)
            
            # Format arguments for logging
            arg_str = ""
            if include_args:
                arg_parts = []
                
                # Add positional args (skipping self)
                for i, arg in enumerate(args):
                    if i == 0 and hasattr(args[0], "__class__"):
                        continue  # Skip self
                    arg_parts.append(repr(arg))
                
                # Add keyword args
                for k, v in kwargs.items():
                    if exclude_args and k in exclude_args:
                        arg_parts.append(f"{k}=***")
                    else:
                        arg_parts.append(f"{k}={repr(v)}")
                
                if arg_parts:
                    arg_str = f" with args: {', '.join(arg_parts)}"
            
            # Log method entry
            log_func(f"Entering {func.__qualname__}{arg_str}")
            
            try:
                # Call the original function
                result = func(*args, **kwargs)
                
                # Log method exit with return value if requested
                if include_return:
                    log_func(f"Exiting {func.__qualname__} with result: {repr(result)}")
                else:
                    log_func(f"Exiting {func.__qualname__}")
                
                return result
            except Exception as e:
                # Log exception
                logger.exception(f"Exception in {func.__qualname__}: {str(e)}")
                raise
        
        return wrapper
    
    return decorator


def info_logger(message: str = "",
                func_str: str = "",
                logger: Optional[logging.Logger] = None,
                addition_msg: str = "") -> None:
    """
    Log an info message.
    
    Args:
        message: Message to log
        func_str: Function name or context
        logger: Logger instance to use
        addition_msg: Additional message to append
    """
    try:
        if func_str:
            message = f"{func_str}: {message}"
        
        if logger:
            logger.info(f"{message} {addition_msg}")
        else:
            print(f"{message} {addition_msg}")
    except Exception as err:
        raise err


def error_logger(func_str: str, 
                 error,
                 logger: Optional[logging.Logger] = None,
                 addition_msg: str = "",
                 mode: str = "critical",
                 ignore_flag: bool = True,
                 set_trace: bool = False) -> None:
    """
    Log an error message.
    
    Args:
        func_str: Function name or context
        error: Error object or message
        logger: Logger instance to use
        addition_msg: Additional message to append
        mode: Log level to use (critical, debug, error, info)
        ignore_flag: Whether to continue execution after logging
        set_trace: Whether to include traceback
    """
    def _not_found(*args, **kwargs):
        raise ValueError("error mode should be 'critical', 'debug', 'error' and 'info'")
    
    if logger:
        _logger_mode = {
            "critical": logger.critical,
            "debug": logger.debug,
            "error": logger.error,
            "info": logger.info
        }
    
    try:
        if logger:
            log_func = _logger_mode.get(mode, _not_found)
            log_func(f"Error in {func_str} {addition_msg} {error}")
            if set_trace:
                logger.exception("trace")
        else:
            print(f"Error in {func_str} {addition_msg} {error}")
        
        return None if ignore_flag else exit(99)
    except Exception as err:
        raise err


def bind_logger(_func: Callable[..., RT] = None,
                *,
                logger: Union[logging.Logger, str] = "auto",
                variable_name: str = "logger") -> Callable[[Callable[..., RT]], Callable[..., RT]]:
    """
    Decorator to bind a logger to a function.
    
    Args:
        _func: Function to decorate
        logger: Logger instance or "auto" to auto-detect
        variable_name: Name of the parameter to bind the logger to
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Check if logger is already provided in args or kwargs
            func_params = func.__code__.co_varnames
            session_in_args = variable_name in func_params and func_params.index(variable_name) < len(args)
            session_in_kwargs = variable_name in kwargs
            
            if (session_in_args or session_in_kwargs) and isinstance(kwargs.get(variable_name), logging.Logger):
                return func(*args, **kwargs)
            else:
                if logger != "auto" and isinstance(logger, logging.Logger):
                    kwargs[variable_name] = logger
                else:
                    # Try to find a logger in args or kwargs
                    first_args = next(iter(args), None)
                    _logger_params = [
                        x for x in kwargs.values() if isinstance(x, logging.Logger)
                    ] + [
                        x for x in args if isinstance(x, logging.Logger)
                    ]
                    
                    # Check if first arg is an object with a logger attribute
                    if hasattr(first_args, "__dict__"):
                        _logger_params += [
                            x for x in first_args.__dict__.values() if isinstance(x, logging.Logger)
                        ]
                    
                    # Use the first logger found or create a default one
                    if _logger_params:
                        kwargs[variable_name] = next(iter(_logger_params))
                    else:
                        kwargs[variable_name] = PGLoggerSingleton() if logger is not None else None
                
                return func(*args, **kwargs)
        
        return wrapper
    
    return decorator if _func is None else decorator(_func)


# Convenience functions for creating loggers
def get_logger(name: str = None, **kwargs) -> logging.Logger:
    """
    Get a logger with the specified configuration.
    
    Args:
        name: Name of the logger (defaults to module name)
        **kwargs: Additional configuration options for PGLogger.get_logger
        
    Returns:
        Configured logger instance
    """
    if name is None:
        # Get the caller's module name
        frame = sys._getframe(1)
        name = frame.f_globals.get('__name__', 'root')
    
    return PGLogger.get_logger(name, **kwargs)


def get_json_logger(name: str = None, **kwargs) -> logging.Logger:
    """
    Get a logger that outputs in JSON format.
    
    Args:
        name: Name of the logger (defaults to module name)
        **kwargs: Additional configuration options for PGLogger.get_logger
        
    Returns:
        Configured logger instance with JSON formatting
    """
    if name is None:
        # Get the caller's module name
        frame = sys._getframe(1)
        name = frame.f_globals.get('__name__', 'root')
    
    return PGLogger.get_logger(name, use_json_format=True, **kwargs)
