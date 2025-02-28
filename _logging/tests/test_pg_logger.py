"""
Unit tests for the production-grade logging module.
"""

import os
import sys
import json
import logging
import tempfile
import threading
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path to import the module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from _logging.pg_logger import (
    PGLogger,
    PGLoggerSingleton,
    setup_log,
    bind_logger,
    info_logger,
    error_logger,
    log_method,
    get_logger,
    get_json_logger,
    JsonFormatter
)


class TestJsonFormatter:
    """Tests for the JsonFormatter class."""
    
    def test_format_basic(self):
        """Test basic formatting of log records."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test_file.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        parsed = json.loads(formatted)
        
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test_logger"
        assert parsed["file"] == "test_file.py"
        assert parsed["line"] == 42
        assert parsed["message"] == "Test message"
        assert "timestamp" in parsed
    
    def test_format_with_exception(self):
        """Test formatting of log records with exception info."""
        formatter = JsonFormatter()
        try:
            raise ValueError("Test exception")
        except ValueError:
            record = logging.LogRecord(
                name="test_logger",
                level=logging.ERROR,
                pathname="test_file.py",
                lineno=42,
                msg="Error occurred",
                args=(),
                exc_info=sys.exc_info()
            )
        
        formatted = formatter.format(record)
        parsed = json.loads(formatted)
        
        assert parsed["level"] == "ERROR"
        assert parsed["message"] == "Error occurred"
        assert "exception" in parsed
        assert parsed["exception"]["type"] == "ValueError"
        assert parsed["exception"]["message"] == "Test exception"
        assert isinstance(parsed["exception"]["traceback"], list)


class TestPGLogger:
    """Tests for the PGLogger class."""
    
    def test_get_logger_basic(self, reset_logging):
        """Test basic logger creation."""
        logger = PGLogger.get_logger("test_logger")
        
        assert logger.name == "test_logger"
        assert logger.level == logging.INFO
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], logging.StreamHandler)
    
    def test_get_logger_with_file(self, reset_logging, temp_log_file):
        """Test logger creation with file handler."""
        logger = PGLogger.get_logger(
            "test_file_logger",
            log_to_file=True,
            log_file_path=temp_log_file
        )
        
        assert logger.name == "test_file_logger"
        assert len(logger.handlers) == 2
        assert any(isinstance(h, logging.FileHandler) for h in logger.handlers)
        
        # Test logging to file
        test_message = "Test file logging"
        logger.info(test_message)
        
        with open(temp_log_file, 'r') as f:
            content = f.read()
            assert test_message in content
    
    def test_get_logger_json_format(self, reset_logging, temp_log_file):
        """Test logger creation with JSON formatting."""
        logger = PGLogger.get_logger(
            "test_json_logger",
            log_to_file=True,
            log_file_path=temp_log_file,
            use_json_format=True
        )
        
        assert logger.name == "test_json_logger"
        
        # Test JSON logging
        test_message = "Test JSON logging"
        logger.info(test_message)
        
        with open(temp_log_file, 'r') as f:
            content = f.read()
            parsed = json.loads(content)
            assert parsed["message"] == test_message
            assert parsed["level"] == "INFO"
    
    def test_logger_caching(self, reset_logging):
        """Test that loggers are cached and reused."""
        logger1 = PGLogger.get_logger("test_cache")
        logger2 = PGLogger.get_logger("test_cache")
        
        assert logger1 is logger2
    
    def test_thread_safety(self, reset_logging):
        """Test thread-safe logger creation."""
        loggers = []
        errors = []
        
        def create_logger():
            try:
                logger = PGLogger.get_logger(f"thread_test_{threading.get_ident()}")
                loggers.append(logger)
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=create_logger) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        assert len(errors) == 0
        assert len(loggers) == 10


class TestPGLoggerSingleton:
    """Tests for the PGLoggerSingleton class."""
    
    def test_singleton_pattern(self, reset_singletons):
        """Test that the singleton pattern works correctly."""
        logger1 = PGLoggerSingleton()
        logger2 = PGLoggerSingleton()
        
        assert logger1 is logger2
    
    def test_singleton_configuration(self, reset_singletons, temp_log_file):
        """Test that singleton configuration works."""
        # First instance with custom config
        logger1 = PGLoggerSingleton(
            name="custom_singleton",
            log_file_path=temp_log_file,
            log_level=logging.DEBUG
        )
        
        # Second instance with different config (should be ignored)
        logger2 = PGLoggerSingleton(
            name="ignored_name",
            log_level=logging.ERROR
        )
        
        assert logger1 is logger2
        assert logger1.name == "custom_singleton"
        assert logger1.level == logging.DEBUG
        
        # Test logging to file
        test_message = "Test singleton logging"
        logger1.info(test_message)
        
        with open(temp_log_file, 'r') as f:
            content = f.read()
            assert test_message in content


class TestUtilityFunctions:
    """Tests for utility functions."""
    
    def test_setup_log(self, reset_logging, temp_log_file):
        """Test setup_log function."""
        logger = setup_log("setup_test", temp_log_file, logging.WARNING)
        
        assert logger.name == "setup_test"
        assert logger.level == logging.WARNING
        assert any(isinstance(h, logging.FileHandler) for h in logger.handlers)
        
        # Test logging
        debug_message = "Debug message"
        warning_message = "Warning message"
        
        logger.debug(debug_message)
        logger.warning(warning_message)
        
        with open(temp_log_file, 'r') as f:
            content = f.read()
            assert debug_message not in content  # Should be filtered by level
            assert warning_message in content
    
    def test_get_logger(self, reset_logging):
        """Test get_logger convenience function."""
        logger = get_logger("convenience_test")
        
        assert logger.name == "convenience_test"
        assert isinstance(logger, logging.Logger)
    
    def test_get_json_logger(self, reset_logging, temp_log_file):
        """Test get_json_logger convenience function."""
        logger = get_json_logger(
            "json_convenience_test",
            log_to_file=True,
            log_file_path=temp_log_file
        )
        
        assert logger.name == "json_convenience_test"
        
        # Test JSON logging
        test_message = "Test JSON convenience"
        logger.info(test_message)
        
        with open(temp_log_file, 'r') as f:
            content = f.read()
            parsed = json.loads(content)
            assert parsed["message"] == test_message
    
    def test_info_logger(self, reset_logging, capsys):
        """Test info_logger function."""
        # Test with print mode
        info_logger("Test info", "test_func")
        captured = capsys.readouterr()
        assert "Test info" in captured.out
        assert "test_func" in captured.out
        
        # Test with logger
        logger = get_logger("info_test")
        with patch.object(logger, 'info') as mock_info:
            info_logger("Logger test", "test_func", logger)
            mock_info.assert_called_once()
            assert "Logger test" in mock_info.call_args[0][0]
            assert "test_func" in mock_info.call_args[0][0]
    
    def test_error_logger(self, reset_logging, capsys):
        """Test error_logger function."""
        # Test with print mode
        error_logger("test_func", "Test error")
        captured = capsys.readouterr()
        assert "Error in test_func" in captured.out
        assert "Test error" in captured.out
        
        # Test with logger
        logger = get_logger("error_test")
        with patch.object(logger, 'critical') as mock_critical:
            error_logger("test_func", "Logger error", logger)
            mock_critical.assert_called_once()
            assert "Error in test_func" in mock_critical.call_args[0][0]
            assert "Logger error" in mock_critical.call_args[0][0]
        
        # Test with different mode
        with patch.object(logger, 'info') as mock_info:
            error_logger("test_func", "Info error", logger, mode="info")
            mock_info.assert_called_once()
            assert "Error in test_func" in mock_info.call_args[0][0]
            assert "Info error" in mock_info.call_args[0][0]


class TestDecorators:
    """Tests for decorator functions."""
    
    def test_log_method_decorator(self, reset_logging, capsys):
        """Test log_method decorator."""
        class TestClass:
            def __init__(self):
                self.logger = get_logger("decorator_test")
            
            @log_method()
            def test_method(self, arg1, arg2=None):
                return f"{arg1}-{arg2}"
            
            @log_method(level="debug", include_args=False)
            def no_args_method(self):
                return "no args"
            
            @log_method(include_return=True)
            def return_method(self, value):
                return value
            
            @log_method(exclude_args=["password"])
            def sensitive_method(self, username, password):
                return "logged in"
        
        # Patch the logger to capture calls
        test_obj = TestClass()
        with patch.object(test_obj.logger, 'info') as mock_info, \
             patch.object(test_obj.logger, 'debug') as mock_debug:
            
            # Test basic method logging
            result = test_obj.test_method("test", arg2="value")
            assert result == "test-value"
            assert mock_info.call_count == 2
            assert "Entering test_method" in mock_info.call_args_list[0][0][0]
            assert "test" in mock_info.call_args_list[0][0][0]
            assert "value" in mock_info.call_args_list[0][0][0]
            assert "Exiting test_method" in mock_info.call_args_list[1][0][0]
            
            # Test no args logging
            mock_info.reset_mock()
            result = test_obj.no_args_method()
            assert result == "no args"
            assert mock_debug.call_count == 2
            assert "Entering no_args_method" in mock_debug.call_args_list[0][0][0]
            assert "with args" not in mock_debug.call_args_list[0][0][0]
            
            # Test return value logging
            mock_info.reset_mock()
            result = test_obj.return_method("return_value")
            assert result == "return_value"
            assert "Exiting return_method with result: 'return_value'" in mock_info.call_args_list[1][0][0]
            
            # Test sensitive args
            mock_info.reset_mock()
            result = test_obj.sensitive_method("admin", "secret123")
            assert result == "logged in"
            assert "admin" in mock_info.call_args_list[0][0][0]
            assert "secret123" not in mock_info.call_args_list[0][0][0]
            assert "password=***" in mock_info.call_args_list[0][0][0]
    
    def test_log_method_exception(self, reset_logging):
        """Test log_method decorator with exceptions."""
        class TestClass:
            def __init__(self):
                self.logger = get_logger("exception_test")
            
            @log_method()
            def error_method(self):
                raise ValueError("Test exception")
        
        test_obj = TestClass()
        with patch.object(test_obj.logger, 'exception') as mock_exception:
            with pytest.raises(ValueError):
                test_obj.error_method()
            
            mock_exception.assert_called_once()
            assert "Exception in error_method" in mock_exception.call_args[0][0]
            assert "Test exception" in mock_exception.call_args[0][0]
    
    def test_bind_logger_decorator(self, reset_logging):
        """Test bind_logger decorator."""
        logger = get_logger("bind_test")
        
        # Test with explicit logger
        @bind_logger(logger=logger)
        def test_func(arg, logger=None):
            return logger
        
        result = test_func("test")
        assert result is logger
        
        # Test with auto-detection
        class LoggerClass:
            def __init__(self):
                self.logger = get_logger("class_logger")
            
            @bind_logger()
            def test_method(self, logger=None):
                return logger
        
        obj = LoggerClass()
        result = obj.test_method()
        assert result is obj.logger
        
        # Test with logger in kwargs
        custom_logger = get_logger("custom_bind")
        result = test_func("test", logger=custom_logger)
        assert result is custom_logger


if __name__ == "__main__":
    pytest.main(["-v", __file__])
