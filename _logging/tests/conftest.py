"""
Pytest configuration for logging tests.
"""

import os
import sys
import logging
import tempfile
import pytest
from pathlib import Path

# Add parent directory to path to import the module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


@pytest.fixture
def temp_log_file():
    """Fixture to provide a temporary log file."""
    with tempfile.NamedTemporaryFile(suffix=".log") as temp_file:
        yield temp_file.name


@pytest.fixture
def reset_logging():
    """Fixture to reset the logging system between tests."""
    # Store original loggers
    original_loggers = logging.root.manager.loggerDict.copy()
    original_handlers = logging.root.handlers.copy()
    
    yield
    
    # Reset logging
    logging.root.handlers = original_handlers
    for logger_name in list(logging.root.manager.loggerDict.keys()):
        if logger_name not in original_loggers:
            del logging.root.manager.loggerDict[logger_name]


@pytest.fixture(autouse=True)
def reset_singletons():
    """Fixture to reset singleton instances between tests."""
    from _logging.pg_logger import PGLoggerSingleton
    
    # Store original state
    original_instance = PGLoggerSingleton._instance
    
    yield
    
    # Reset to original state
    PGLoggerSingleton._instance = original_instance
