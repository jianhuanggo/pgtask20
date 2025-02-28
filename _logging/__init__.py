"""
Production-grade logging module for Python applications.

This module provides a comprehensive logging system with features for production environments.
"""

from .pg_logger import (
    PGLogger,
    PGLoggerSingleton,
    setup_log,
    bind_logger,
    info_logger,
    error_logger,
    log_method,
    get_logger,
    get_json_logger,
    JsonFormatter,
)

# Export standard logging levels for convenience
import logging
DEBUG = logging.DEBUG
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL

__all__ = [
    # Production-grade logging
    'PGLogger',
    'PGLoggerSingleton',
    'setup_log',
    'bind_logger',
    'info_logger',
    'error_logger',
    'log_method',
    'get_logger',
    'get_json_logger',
    'JsonFormatter',
    
    # Standard logging levels
    'DEBUG',
    'INFO',
    'WARNING',
    'ERROR',
    'CRITICAL',
]
