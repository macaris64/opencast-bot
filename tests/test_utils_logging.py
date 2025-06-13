"""
Tests for the enhanced logging system.

This module tests the structured logging capabilities,
context management, and performance monitoring.
"""

import pytest
import json
import logging
import time
import asyncio
from unittest.mock import Mock, patch
from io import StringIO
from pathlib import Path
import tempfile

from bot.utils.logging import (
    StructuredFormatter,
    ContextFilter,
    StructuredLogger,
    LoggerMixin,
    get_logger,
    setup_logging,
    log_execution_time,
    log_context
)
from bot.utils.exceptions import OpenCastBotError


class TestStructuredFormatter:
    """Test the structured JSON formatter."""
    
    def test_basic_formatting(self):
        """Test basic log record formatting."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.module = "test_module"
        record.funcName = "test_function"
        
        formatted = formatter.format(record)
        log_data = json.loads(formatted)
        
        assert log_data['level'] == 'INFO'
        assert log_data['logger'] == 'test.logger'
        assert log_data['message'] == 'Test message'
        assert log_data['module'] == 'test_module'
        assert log_data['function'] == 'test_function'
        assert log_data['line'] == 42
        assert 'timestamp' in log_data
    
    def test_formatting_with_exception(self):
        """Test formatting with exception information."""
        formatter = StructuredFormatter()
        
        try:
            raise ValueError("Test exception")
        except ValueError as e:
            import sys
            record = logging.LogRecord(
                name="test.logger",
                level=logging.ERROR,
                pathname="/test/path.py",
                lineno=42,
                msg="Error occurred",
                args=(),
                exc_info=sys.exc_info()
            )
            record.module = "test_module"
            record.funcName = "test_function"
            
            formatted = formatter.format(record)
            log_data = json.loads(formatted)
            
            assert 'exception' in log_data
            assert log_data['exception']['type'] == 'ValueError'
            assert log_data['exception']['message'] == 'Test exception'
            assert 'traceback' in log_data['exception']
    
    def test_formatting_with_extra_fields(self):
        """Test formatting with extra fields."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.module = "test_module"
        record.funcName = "test_function"
        record.user_id = "123"
        record.operation = "test_op"
        
        formatted = formatter.format(record)
        log_data = json.loads(formatted)
        
        assert 'extra' in log_data
        assert log_data['extra']['user_id'] == "123"
        assert log_data['extra']['operation'] == "test_op"


class TestContextFilter:
    """Test the context filter."""
    
    def test_context_addition(self):
        """Test adding context to log records."""
        filter_obj = ContextFilter()
        filter_obj.set_context(user_id="123", operation="test")
        
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        result = filter_obj.filter(record)
        
        assert result is True
        assert hasattr(record, 'user_id')
        assert hasattr(record, 'operation')
        assert record.user_id == "123"
        assert record.operation == "test"
    
    def test_context_clearing(self):
        """Test clearing context."""
        filter_obj = ContextFilter()
        filter_obj.set_context(user_id="123")
        
        assert filter_obj.context == {"user_id": "123"}
        
        filter_obj.clear_context()
        
        assert filter_obj.context == {}


class TestStructuredLogger:
    """Test the structured logger."""
    
    def setup_method(self):
        """Setup test logger."""
        self.logger = StructuredLogger("test.logger")
        self.handler = Mock()
        self.handler.level = logging.DEBUG  # Set level attribute for Mock
        self.handler.handle = Mock()
        self.logger.logger.addHandler(self.handler)
        self.logger.logger.setLevel(logging.DEBUG)
    
    def test_basic_logging_methods(self):
        """Test basic logging methods."""
        self.logger.debug("Debug message")
        self.logger.info("Info message")
        self.logger.warning("Warning message")
        self.logger.error("Error message")
        self.logger.critical("Critical message")
        
        assert self.handler.handle.call_count == 5
    
    def test_logging_with_context(self):
        """Test logging with additional context."""
        self.logger.info("Test message", user_id="123", operation="test")
        
        call_args = self.handler.handle.call_args[0][0]
        assert hasattr(call_args, 'user_id')
        assert hasattr(call_args, 'operation')
        assert call_args.user_id == "123"
        assert call_args.operation == "test"
    
    def test_error_logging_with_exception(self):
        """Test error logging with exception details."""
        error = OpenCastBotError("Test error", context={"key": "value"})
        
        self.logger.error("Error occurred", error=error)
        
        # Check that handle was called twice (once for structured log, once for exc_info)
        assert self.handler.handle.call_count == 2
        
        # Check the first call (structured log with error details)
        first_call_args = self.handler.handle.call_args_list[0][0][0]
        assert hasattr(first_call_args, 'error_type')
        assert hasattr(first_call_args, 'error_message')
        assert first_call_args.error_type == "OpenCastBotError"
        assert first_call_args.error_message == "[OpenCastBotError] Test error (Context: key=value)"
    
    def test_context_management(self):
        """Test context management."""
        self.logger.set_context(user_id="123")
        self.logger.info("Test message")
        
        call_args = self.handler.handle.call_args[0][0]
        assert hasattr(call_args, 'user_id')
        assert call_args.user_id == "123"
        
        self.logger.clear_context()
        self.logger.info("Another message")
        
        call_args = self.handler.handle.call_args[0][0]
        assert not hasattr(call_args, 'user_id')
    
    def test_context_manager(self):
        """Test temporary context manager."""
        with self.logger.context(user_id="123", operation="test"):
            self.logger.info("Inside context")
            
            call_args = self.handler.handle.call_args[0][0]
            assert hasattr(call_args, 'user_id')
            assert call_args.user_id == "123"
        
        self.logger.info("Outside context")
        call_args = self.handler.handle.call_args[0][0]
        assert not hasattr(call_args, 'user_id')
    
    def test_performance_logging(self):
        """Test performance logging."""
        self.logger.log_performance("test_operation", 1.5, status="success")
        
        call_args = self.handler.handle.call_args[0][0]
        assert hasattr(call_args, 'operation')
        assert hasattr(call_args, 'duration_ms')
        assert hasattr(call_args, 'status')
        assert call_args.operation == "test_operation"
        assert call_args.duration_ms == 1500.0
        assert call_args.status == "success"
    
    def test_api_call_logging(self):
        """Test API call logging."""
        self.logger.log_api_call(
            api_name="OpenAI",
            method="POST",
            url="https://api.openai.com/v1/chat/completions",
            status_code=200,
            duration=2.3
        )
        
        call_args = self.handler.handle.call_args[0][0]
        assert hasattr(call_args, 'api_name')
        assert hasattr(call_args, 'method')
        assert hasattr(call_args, 'url')
        assert hasattr(call_args, 'status_code')
        assert hasattr(call_args, 'duration_ms')
        assert call_args.api_name == "OpenAI"
        assert call_args.method == "POST"
        assert call_args.status_code == 200
        assert call_args.duration_ms == 2300.0


class TestLoggerMixin:
    """Test the logger mixin."""
    
    def test_mixin_provides_logger(self):
        """Test that mixin provides logger property."""
        
        class TestClass(LoggerMixin):
            def __init__(self):
                super().__init__()
        
        instance = TestClass()
        
        assert hasattr(instance, 'logger')
        assert isinstance(instance.logger, StructuredLogger)
        assert instance.logger.logger.name.endswith('TestClass')


class TestLoggingSetup:
    """Test logging setup functionality."""
    
    def test_setup_logging_basic(self):
        """Test basic logging setup."""
        setup_logging(level="INFO")
        
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO
        assert len(root_logger.handlers) > 0
    
    def test_setup_logging_with_file(self):
        """Test logging setup with file output."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            
            setup_logging(level="DEBUG", log_file=log_file)
            
            root_logger = logging.getLogger()
            assert len(root_logger.handlers) == 2  # Console + file
            assert log_file.exists()
    
    def test_setup_logging_simple_format(self):
        """Test logging setup with simple format."""
        setup_logging(level="INFO", format_type="simple")
        
        root_logger = logging.getLogger()
        handler = root_logger.handlers[0]
        assert not isinstance(handler.formatter, StructuredFormatter)


class TestExecutionTimeDecorator:
    """Test the execution time logging decorator."""
    
    def test_sync_function_decoration(self):
        """Test decorating synchronous functions."""
        logger = Mock()
        
        @log_execution_time(logger=logger)
        def test_function():
            time.sleep(0.1)
            return "result"
        
        result = test_function()
        
        assert result == "result"
        logger.log_performance.assert_called_once()
        call_args = logger.log_performance.call_args[1]
        assert call_args['operation'] == 'test_function'
        assert call_args['status'] == 'success'
        assert call_args['duration'] >= 0.1
    
    def test_sync_function_with_exception(self):
        """Test decorating function that raises exception."""
        logger = Mock()
        
        @log_execution_time(logger=logger)
        def test_function():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            test_function()
        
        logger.log_performance.assert_called_once()
        call_args = logger.log_performance.call_args[1]
        assert call_args['operation'] == 'test_function'
        assert call_args['status'] == 'error'
        assert call_args['error_type'] == 'ValueError'
    
    @pytest.mark.asyncio
    async def test_async_function_decoration(self):
        """Test decorating asynchronous functions."""
        logger = Mock()
        
        @log_execution_time(logger=logger)
        async def test_async_function():
            await asyncio.sleep(0.1)
            return "async_result"
        
        result = await test_async_function()
        
        assert result == "async_result"
        logger.log_performance.assert_called_once()
        call_args = logger.log_performance.call_args[1]
        assert call_args['operation'] == 'test_async_function'
        assert call_args['status'] == 'success'


class TestLogContext:
    """Test the log context manager."""
    
    def test_log_context_manager(self):
        """Test the log context manager functionality."""
        # This test is more complex due to the global nature of logging
        # We'll test the basic functionality
        
        logger = get_logger("test.context")
        handler = Mock()
        handler.level = logging.DEBUG  # Set level attribute for Mock
        handler.handle = Mock()
        logger.logger.addHandler(handler)
        logger.logger.setLevel(logging.DEBUG)
        
        with log_context(user_id="123", operation="test"):
            logger.info("Test message")
        
        # The context should be applied to the log message
        # This is a simplified test - in practice, the context manager
        # affects all loggers in the application
        assert handler.handle.called


class TestGetLogger:
    """Test the get_logger function."""
    
    def test_get_logger_returns_structured_logger(self):
        """Test that get_logger returns StructuredLogger instance."""
        logger = get_logger("test.module")
        
        assert isinstance(logger, StructuredLogger)
        assert logger.logger.name == "test.module"
    
    def test_get_logger_caching(self):
        """Test that get_logger returns same instance for same name."""
        logger1 = get_logger("test.module")
        logger2 = get_logger("test.module")
        
        # They should use the same underlying logger
        assert logger1.logger is logger2.logger


class TestIntegration:
    """Integration tests for the logging system."""
    
    def test_full_logging_workflow(self):
        """Test complete logging workflow."""
        # Setup logging
        setup_logging(level="DEBUG", format_type="structured")
        
        # Create logger with mock handler
        logger = get_logger("test.integration")
        handler = Mock()
        handler.level = logging.DEBUG
        handler.handle = Mock()
        logger.logger.addHandler(handler)
        logger.logger.setLevel(logging.DEBUG)
        
        # Log with context
        logger.set_context(user_id="123")
        logger.info("Test message", operation="test_op")
        
        # Log error with exception
        error = OpenCastBotError("Test error")
        logger.error("Error occurred", error=error)
        
        # Log performance
        logger.log_performance("test_operation", 1.5)
        
        # Verify that logging methods were called
        assert handler.handle.call_count >= 3  # Should have at least 3 log entries
        
        # Verify structured logging worked
        calls = handler.handle.call_args_list
        assert len(calls) >= 3
        
        # Check that different log levels were used
        levels = [call[0][0].levelname for call in calls]
        assert 'INFO' in levels
        assert 'ERROR' in levels 