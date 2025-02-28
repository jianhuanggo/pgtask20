"""
Integration tests for the production-grade logging module.
"""

import os
import sys
import json
import logging
import tempfile
import pytest
from pathlib import Path

# Add parent directory to path to import the module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from _logging.pg_logger import (
    PGLogger,
    PGLoggerSingleton,
    setup_log,
    log_method,
    get_logger,
    get_json_logger
)


class TestLoggingIntegration:
    """Integration tests for the logging system."""
    
    def test_multiple_handlers(self):
        """Test using multiple handlers with the same logger."""
        with tempfile.NamedTemporaryFile(suffix=".log") as file1, \
             tempfile.NamedTemporaryFile(suffix=".log") as file2:
            
            # Create logger with file handler
            logger = PGLogger.get_logger(
                "test_multi_handler",
                log_to_file=True,
                log_file_path=file1.name
            )
            
            # Add another file handler
            handler = logging.FileHandler(file2.name)
            formatter = logging.Formatter("%(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
            # Log a message
            test_message = "Test multiple handlers"
            logger.info(test_message)
            
            # Check both files
            file1.flush()
            file2.flush()
            
            with open(file1.name, 'r') as f1, open(file2.name, 'r') as f2:
                content1 = f1.read()
                content2 = f2.read()
                
                assert test_message in content1
                assert test_message in content2
                assert "INFO" in content2  # Check custom format
    
    def test_child_logger_inheritance(self):
        """Test logger hierarchy and inheritance."""
        with tempfile.NamedTemporaryFile(suffix=".log") as temp_file:
            # Create parent logger
            parent_logger = PGLogger.get_logger(
                "test_parent",
                log_to_file=True,
                log_file_path=temp_file.name,
                log_level=logging.WARNING
            )
            
            # Create child logger
            child_logger = logging.getLogger("test_parent.child")
            
            # Log messages at different levels
            parent_logger.debug("Parent debug - should not appear")
            parent_logger.warning("Parent warning - should appear")
            
            child_logger.debug("Child debug - should not appear")
            child_logger.warning("Child warning - should appear")
            
            # Check log file
            temp_file.flush()
            with open(temp_file.name, 'r') as f:
                content = f.read()
                
                assert "Parent debug" not in content
                assert "Parent warning" in content
                assert "Child debug" not in content
                assert "Child warning" in content
    
    def test_log_method_real_class(self):
        """Test log_method decorator with a real class."""
        with tempfile.NamedTemporaryFile(suffix=".log") as temp_file:
            class TestService:
                def __init__(self):
                    self.logger = PGLogger.get_logger(
                        "test_service",
                        log_to_file=True,
                        log_file_path=temp_file.name
                    )
                
                @log_method(include_args=True, include_return=True)
                def process_data(self, data, sensitive=None):
                    return f"Processed: {data}"
                
                @log_method(level="error")
                def risky_operation(self):
                    raise ValueError("Operation failed")
            
            # Test normal operation
            service = TestService()
            result = service.process_data("test_data", sensitive="secret")
            
            # Test exception
            with pytest.raises(ValueError):
                service.risky_operation()
            
            # Check log file
            temp_file.flush()
            with open(temp_file.name, 'r') as f:
                content = f.read()
                
                # Check method entry/exit logs
                assert "Entering process_data" in content
                assert "test_data" in content
                assert "Exiting process_data" in content
                assert "Processed: test_data" in content
                
                # Check that sensitive data is not logged
                assert "secret" not in content
                
                # Check exception logging
                assert "Exception in risky_operation" in content
                assert "Operation failed" in content
    
    def test_json_logging_integration(self):
        """Test JSON logging in a realistic scenario."""
        with tempfile.NamedTemporaryFile(suffix=".log") as temp_file:
            # Create JSON logger
            logger = get_json_logger(
                "json_test",
                log_to_file=True,
                log_file_path=temp_file.name,
                log_to_console=False
            )
            
            # Log various messages
            logger.info("Information message")
            logger.warning("Warning message")
            
            try:
                raise ValueError("Test exception")
            except Exception:
                logger.exception("An error occurred")
            
            # Check log file
            temp_file.flush()
            with open(temp_file.name, 'r') as f:
                lines = f.readlines()
                
                # Parse each line as JSON
                for line in lines:
                    parsed = json.loads(line)
                    
                    # Check common fields
                    assert "timestamp" in parsed
                    assert "level" in parsed
                    assert "logger" in parsed
                    assert "file" in parsed
                    assert "line" in parsed
                    assert "message" in parsed
                
                # Check specific messages
                info_log = json.loads(lines[0])
                warning_log = json.loads(lines[1])
                error_log = json.loads(lines[2])
                
                assert info_log["level"] == "INFO"
                assert info_log["message"] == "Information message"
                
                assert warning_log["level"] == "WARNING"
                assert warning_log["message"] == "Warning message"
                
                assert error_log["level"] == "ERROR"
                assert error_log["message"] == "An error occurred"
                assert "exception" in error_log
                assert error_log["exception"]["type"] == "ValueError"
                assert error_log["exception"]["message"] == "Test exception"


if __name__ == "__main__":
    pytest.main(["-v", __file__])
