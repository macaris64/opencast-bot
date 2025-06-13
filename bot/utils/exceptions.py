"""
Custom exception classes for OpenCast Bot.

This module defines a comprehensive exception hierarchy that provides
clear error categorization and enhanced error handling capabilities.
"""

from typing import Optional, Dict, Any
import traceback
from datetime import datetime, timezone


class OpenCastBotError(Exception):
    """
    Base exception class for all OpenCast Bot errors.
    
    Provides enhanced error information including:
    - Error categorization
    - Contextual information
    - Timestamp tracking
    - Structured error data
    """
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.context = context or {}
        self.cause = cause
        self.timestamp = datetime.now(timezone.utc)
        self.traceback_str = traceback.format_exc() if cause else None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to structured dictionary."""
        return {
            'error_type': self.__class__.__name__,
            'error_code': self.error_code,
            'message': self.message,
            'context': self.context,
            'timestamp': self.timestamp.isoformat(),
            'cause': str(self.cause) if self.cause else None,
            'traceback': self.traceback_str
        }
    
    def __str__(self) -> str:
        """Enhanced string representation."""
        base_msg = f"[{self.error_code}] {self.message}"
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            base_msg += f" (Context: {context_str})"
        if self.cause:
            base_msg += f" (Caused by: {self.cause})"
        return base_msg


class ConfigurationError(OpenCastBotError):
    """Raised when there are configuration-related errors."""
    
    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs):
        context = kwargs.get('context', {})
        if config_key:
            context['config_key'] = config_key
        super().__init__(message, context=context, **kwargs)


class ContentGenerationError(OpenCastBotError):
    """Raised when content generation fails."""
    
    def __init__(
        self,
        message: str,
        category_id: Optional[str] = None,
        topic: Optional[str] = None,
        **kwargs
    ):
        context = kwargs.pop('context', {})
        if category_id:
            context['category_id'] = category_id
        if topic:
            context['topic'] = topic
        super().__init__(message, context=context, **kwargs)


class PublishingError(OpenCastBotError):
    """Raised when content publishing fails."""
    
    def __init__(
        self,
        message: str,
        platform: Optional[str] = None,
        content_preview: Optional[str] = None,
        **kwargs
    ):
        context = kwargs.pop('context', {})
        if platform:
            context['platform'] = platform
        if content_preview:
            context['content_preview'] = content_preview[:50] + "..." if len(content_preview) > 50 else content_preview
        super().__init__(message, context=context, **kwargs)


class APIError(OpenCastBotError):
    """Raised when external API calls fail."""
    
    def __init__(
        self,
        message: str,
        api_name: Optional[str] = None,
        operation: Optional[str] = None,
        status_code: Optional[int] = None,
        response_data: Optional[str] = None,
        error_code: Optional[str] = None,
        **kwargs
    ):
        context = kwargs.pop('context', {})
        if api_name:
            context['api_name'] = api_name
        if operation:
            context['operation'] = operation
        if status_code:
            context['status_code'] = status_code
        if response_data:
            context['response_data'] = response_data[:200] + "..." if len(response_data) > 200 else response_data
        super().__init__(message, context=context, error_code=error_code, **kwargs)


class ValidationError(OpenCastBotError):
    """Raised when data validation fails."""
    
    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        field_value: Optional[Any] = None,
        validation_rule: Optional[str] = None,
        **kwargs
    ):
        context = kwargs.pop('context', {})
        if field_name:
            context['field_name'] = field_name
        if field_value is not None:
            context['field_value'] = str(field_value)[:100]
        if validation_rule:
            context['validation_rule'] = validation_rule
        super().__init__(message, context=context, **kwargs)


class RetryableError(OpenCastBotError):
    """
    Base class for errors that can be retried.
    
    These errors indicate temporary failures that might succeed
    if the operation is attempted again.
    """
    
    def __init__(self, message: str, retry_after: Optional[float] = None, **kwargs):
        context = kwargs.pop('context', {})
        if retry_after:
            context['retry_after'] = retry_after
        super().__init__(message, context=context, **kwargs)


class NonRetryableError(OpenCastBotError):
    """
    Base class for errors that should not be retried.
    
    These errors indicate permanent failures that will not
    succeed even if retried.
    """
    pass


# Specific retryable errors
class RateLimitError(RetryableError):
    """Raised when API rate limits are exceeded."""
    
    def __init__(
        self,
        message: str,
        api_name: Optional[str] = None,
        operation: Optional[str] = None,
        retry_after: Optional[float] = None,
        **kwargs
    ):
        context = kwargs.pop('context', {})
        if api_name:
            context['api_name'] = api_name
        if operation:
            context['operation'] = operation
        super().__init__(message, retry_after=retry_after, context=context, **kwargs)


class NetworkError(RetryableError):
    """Raised when network connectivity issues occur."""
    
    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        status_code: Optional[int] = None,
        **kwargs
    ):
        context = kwargs.pop('context', {})
        if operation:
            context['operation'] = operation
        if status_code:
            context['status_code'] = status_code
        super().__init__(message, context=context, **kwargs)


class TemporaryAPIError(RetryableError):
    """Raised when APIs return temporary error responses."""
    pass


# Specific non-retryable errors
class AuthenticationError(NonRetryableError):
    """Raised when authentication fails."""
    
    def __init__(
        self,
        message: str,
        api_name: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        context = kwargs.pop('context', {})
        if api_name:
            context['api_name'] = api_name
        if operation:
            context['operation'] = operation
        super().__init__(message, context=context, **kwargs)


class AuthorizationError(NonRetryableError):
    """Raised when authorization is denied."""
    
    def __init__(
        self,
        message: str,
        api_name: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        context = kwargs.pop('context', {})
        if api_name:
            context['api_name'] = api_name
        if operation:
            context['operation'] = operation
        super().__init__(message, context=context, **kwargs)


class InvalidDataError(NonRetryableError):
    """Raised when data is fundamentally invalid."""
    
    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        field_value: Optional[Any] = None,
        data_type: Optional[str] = None,
        validation_rule: Optional[str] = None,
        **kwargs
    ):
        context = kwargs.pop('context', {})
        if field_name:
            context['field_name'] = field_name
        if field_value is not None:
            context['field_value'] = str(field_value)[:100]
        if data_type:
            context['data_type'] = data_type
        if validation_rule:
            context['validation_rule'] = validation_rule
        super().__init__(message, context=context, **kwargs)


class ResourceNotFoundError(NonRetryableError):
    """Raised when a required resource is not found."""
    pass


# Legacy exception compatibility
class CategoryNotFoundError(ResourceNotFoundError):
    """Legacy exception for category not found errors."""
    
    def __init__(self, category_id: str):
        self.category_id = category_id
        super().__init__(
            f"Category '{category_id}' not found",
            context={'category_id': category_id}
        )


class InvalidCategoryError(ValidationError):
    """Legacy exception for invalid category data."""
    pass 