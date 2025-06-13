"""
Advanced logging system for OpenCast Bot.

This module provides enhanced logging capabilities including:
- Structured logging with JSON output
- Context-aware logging
- Performance monitoring
- Error tracking and correlation
- Configurable log levels and formats
"""

import logging
import json
import sys
import time
from typing import Dict, Any, Optional, Union
from datetime import datetime, timezone
from pathlib import Path
from contextlib import contextmanager
from functools import wraps
import asyncio


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs structured JSON logs.
    
    Provides consistent, machine-readable log output with
    contextual information and metadata.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add exception information if present
        if record.exc_info and record.exc_info != (None, None, None):
            exc_type, exc_value, exc_traceback = record.exc_info
            log_entry['exception'] = {
                'type': exc_type.__name__ if exc_type else None,
                'message': str(exc_value) if exc_value else None,
                'traceback': self.formatException(record.exc_info)
            }
        
        # Add extra fields from the record
        extra_fields = {
            k: v for k, v in record.__dict__.items()
            if k not in {
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                'filename', 'module', 'lineno', 'funcName', 'created',
                'msecs', 'relativeCreated', 'thread', 'threadName',
                'processName', 'process', 'getMessage', 'exc_info',
                'exc_text', 'stack_info'
            }
        }
        
        if extra_fields:
            log_entry['extra'] = extra_fields
        
        return json.dumps(log_entry, default=str, ensure_ascii=False)


class ContextFilter(logging.Filter):
    """
    Filter that adds contextual information to log records.
    
    Automatically includes request IDs, user context, and
    other relevant metadata in log entries.
    """
    
    def __init__(self):
        super().__init__()
        self.context = {}
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add context information to log record."""
        for key, value in self.context.items():
            setattr(record, key, value)
        return True
    
    def set_context(self, **kwargs):
        """Set context information for subsequent log entries."""
        self.context.update(kwargs)
    
    def clear_context(self):
        """Clear all context information."""
        self.context.clear()


class StructuredLogger:
    """
    Enhanced logger with structured output and context management.
    
    Provides a high-level interface for structured logging with
    automatic context management and performance tracking.
    """
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.context_filter = ContextFilter()
        self.logger.addFilter(self.context_filter)
    
    def _log_with_context(self, level: int, message: str, **kwargs):
        """Log message with additional context."""
        extra = {k: v for k, v in kwargs.items() if v is not None}
        self.logger.log(level, message, extra=extra)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with context."""
        self._log_with_context(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message with context."""
        self._log_with_context(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with context."""
        self._log_with_context(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, error: Optional[Exception] = None, **kwargs):
        """Log error message with optional exception details."""
        if error:
            kwargs['error_type'] = error.__class__.__name__
            kwargs['error_message'] = str(error)
            if hasattr(error, 'to_dict'):
                kwargs['error_details'] = error.to_dict()
        
        self._log_with_context(logging.ERROR, message, **kwargs)
        
        if error:
            self.logger.error(message, exc_info=error)
    
    def critical(self, message: str, error: Optional[Exception] = None, **kwargs):
        """Log critical message with optional exception details."""
        if error:
            kwargs['error_type'] = error.__class__.__name__
            kwargs['error_message'] = str(error)
        
        self._log_with_context(logging.CRITICAL, message, **kwargs)
        
        if error:
            self.logger.critical(message, exc_info=error)
    
    def set_context(self, **kwargs):
        """Set persistent context for this logger."""
        self.context_filter.set_context(**kwargs)
    
    def clear_context(self):
        """Clear persistent context."""
        self.context_filter.clear_context()
    
    @contextmanager
    def context(self, **kwargs):
        """Temporary context manager for logging."""
        original_context = self.context_filter.context.copy()
        try:
            self.context_filter.set_context(**kwargs)
            yield self
        finally:
            self.context_filter.context = original_context
    
    def log_performance(self, operation: str, duration: float, **kwargs):
        """Log performance metrics."""
        self.info(
            f"Performance: {operation}",
            operation=operation,
            duration_ms=round(duration * 1000, 2),
            **kwargs
        )
    
    def log_api_call(
        self,
        api_name: str,
        method: str,
        url: str,
        status_code: Optional[int] = None,
        duration: Optional[float] = None,
        **kwargs
    ):
        """Log API call details."""
        self.info(
            f"API Call: {api_name} {method}",
            api_name=api_name,
            method=method,
            url=url,
            status_code=status_code,
            duration_ms=round(duration * 1000, 2) if duration else None,
            **kwargs
        )


class LoggerMixin:
    """
    Mixin class that provides structured logging capabilities.
    
    Classes that inherit from this mixin automatically get
    a configured logger instance.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")
    
    @property
    def logger(self) -> StructuredLogger:
        """Get the logger instance for this class."""
        return self._logger


def get_logger(name: str) -> StructuredLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (typically module.class)
        
    Returns:
        Configured StructuredLogger instance
    """
    return StructuredLogger(name)


def setup_logging(
    level: Optional[str] = None,
    format_type: str = "structured",
    log_file: Optional[Path] = None
) -> None:
    """
    Setup application-wide logging configuration.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Format type ("structured" or "simple")
        log_file: Optional file path for log output
    """
    log_level = level or "INFO"
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    
    if format_type == "structured":
        console_handler.setFormatter(StructuredFormatter())
    else:
        console_handler.setFormatter(
            logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        )
    
    root_logger.addHandler(console_handler)
    
    # Add file handler if specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(file_handler)
    
    # Set specific logger levels
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)


def log_execution_time(func=None, *, logger: Optional[StructuredLogger] = None):
    """
    Decorator to log function execution time.
    
    Can be used as @log_execution_time or @log_execution_time(logger=custom_logger)
    
    Args:
        func: Function to decorate (when used without parentheses)
        logger: Optional logger instance. If not provided, creates one.
    """
    def decorator(f):
        func_logger = logger or get_logger(f"{f.__module__}.{f.__name__}")
        
        if asyncio.iscoroutinefunction(f):
            @wraps(f)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                
                try:
                    result = await f(*args, **kwargs)
                    duration = time.time() - start_time
                    func_logger.log_performance(
                        operation=f.__name__,
                        duration=duration,
                        status="success"
                    )
                    return result
                except Exception as e:
                    duration = time.time() - start_time
                    func_logger.log_performance(
                        operation=f.__name__,
                        duration=duration,
                        status="error",
                        error_type=e.__class__.__name__
                    )
                    raise
            return async_wrapper
        else:
            @wraps(f)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                
                try:
                    result = f(*args, **kwargs)
                    duration = time.time() - start_time
                    func_logger.log_performance(
                        operation=f.__name__,
                        duration=duration,
                        status="success"
                    )
                    return result
                except Exception as e:
                    duration = time.time() - start_time
                    func_logger.log_performance(
                        operation=f.__name__,
                        duration=duration,
                        status="error",
                        error_type=e.__class__.__name__
                    )
                    raise
            return sync_wrapper
    
    # Handle both @log_execution_time and @log_execution_time()
    if func is None:
        return decorator
    else:
        return decorator(func)


@contextmanager
def log_context(**kwargs):
    """
    Context manager for adding context to all log messages within the block.
    
    Args:
        **kwargs: Context key-value pairs to add to log messages
    """
    # Get all current loggers and add context
    loggers = [logging.getLogger(name) for name in logging.Logger.manager.loggerDict]
    filters = []
    
    for logger in loggers:
        if hasattr(logger, 'filters'):
            for filter_obj in logger.filters:
                if isinstance(filter_obj, ContextFilter):
                    filter_obj.set_context(**kwargs)
                    filters.append(filter_obj)
    
    try:
        yield
    finally:
        # Clear context from all filters
        for filter_obj in filters:
            for key in kwargs:
                if key in filter_obj.context:
                    del filter_obj.context[key] 