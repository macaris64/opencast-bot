"""
Tests for the enhanced exception system.

This module tests the custom exception hierarchy and
error handling capabilities.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock

from bot.utils.exceptions import (
    OpenCastBotError,
    ConfigurationError,
    ContentGenerationError,
    PublishingError,
    APIError,
    ValidationError,
    RetryableError,
    NonRetryableError,
    RateLimitError,
    NetworkError,
    TemporaryAPIError,
    AuthenticationError,
    AuthorizationError,
    InvalidDataError,
    ResourceNotFoundError,
    CategoryNotFoundError,
    InvalidCategoryError
)


class TestOpenCastBotError:
    """Test the base exception class."""
    
    def test_basic_exception_creation(self):
        """Test basic exception creation."""
        error = OpenCastBotError("Test error message")
        
        assert str(error) == "[OpenCastBotError] Test error message"
        assert error.message == "Test error message"
        assert error.error_code == "OpenCastBotError"
        assert error.context == {}
        assert error.cause is None
        assert isinstance(error.timestamp, datetime)
    
    def test_exception_with_context(self):
        """Test exception creation with context."""
        context = {"user_id": "123", "operation": "test"}
        error = OpenCastBotError("Test error", context=context)
        
        assert error.context == context
        assert "user_id=123" in str(error)
        assert "operation=test" in str(error)
    
    def test_exception_with_cause(self):
        """Test exception creation with cause."""
        cause = ValueError("Original error")
        error = OpenCastBotError("Test error", cause=cause)
        
        assert error.cause == cause
        assert "Caused by: Original error" in str(error)
    
    def test_exception_with_custom_error_code(self):
        """Test exception with custom error code."""
        error = OpenCastBotError("Test error", error_code="CUSTOM_ERROR")
        
        assert error.error_code == "CUSTOM_ERROR"
        assert str(error) == "[CUSTOM_ERROR] Test error"
    
    def test_to_dict_method(self):
        """Test exception serialization to dictionary."""
        context = {"key": "value"}
        cause = ValueError("Original error")
        error = OpenCastBotError(
            "Test error",
            error_code="TEST_ERROR",
            context=context,
            cause=cause
        )
        
        error_dict = error.to_dict()
        
        assert error_dict['error_type'] == 'OpenCastBotError'
        assert error_dict['error_code'] == 'TEST_ERROR'
        assert error_dict['message'] == 'Test error'
        assert error_dict['context'] == context
        assert error_dict['cause'] == 'Original error'
        assert 'timestamp' in error_dict
        assert 'traceback' in error_dict


class TestSpecificExceptions:
    """Test specific exception types."""
    
    def test_configuration_error(self):
        """Test ConfigurationError."""
        error = ConfigurationError("Invalid config", config_key="api_key")
        
        assert isinstance(error, OpenCastBotError)
        assert error.context['config_key'] == "api_key"
    
    def test_content_generation_error(self):
        """Test ContentGenerationError."""
        error = ContentGenerationError(
            "Generation failed",
            category_id="test-category",
            topic="test topic"
        )
        
        assert isinstance(error, OpenCastBotError)
        assert error.context['category_id'] == "test-category"
        assert error.context['topic'] == "test topic"
    
    def test_publishing_error(self):
        """Test PublishingError."""
        content = "This is a long content that should be truncated in the preview"
        error = PublishingError(
            "Publishing failed",
            platform="twitter",
            content_preview=content
        )
        
        assert isinstance(error, OpenCastBotError)
        assert error.context['platform'] == "twitter"
        assert len(error.context['content_preview']) <= 53  # 50 + "..."
    
    def test_api_error(self):
        """Test APIError."""
        response_data = "A" * 300  # Long response
        error = APIError(
            "API call failed",
            api_name="OpenAI",
            status_code=500,
            response_data=response_data
        )
        
        assert isinstance(error, OpenCastBotError)
        assert error.context['api_name'] == "OpenAI"
        assert error.context['status_code'] == 500
        assert len(error.context['response_data']) <= 203  # 200 + "..."
    
    def test_validation_error(self):
        """Test ValidationError."""
        error = ValidationError(
            "Validation failed",
            field_name="content",
            field_value="test value",
            validation_rule="min_length"
        )
        
        assert isinstance(error, OpenCastBotError)
        assert error.context['field_name'] == "content"
        assert error.context['field_value'] == "test value"
        assert error.context['validation_rule'] == "min_length"
    
    def test_retryable_error(self):
        """Test RetryableError."""
        error = RetryableError("Temporary failure", retry_after=5.0)
        
        assert isinstance(error, OpenCastBotError)
        assert error.context['retry_after'] == 5.0
    
    def test_non_retryable_error(self):
        """Test NonRetryableError."""
        error = NonRetryableError("Permanent failure")
        
        assert isinstance(error, OpenCastBotError)


class TestSpecificErrorTypes:
    """Test specific error type implementations."""
    
    def test_rate_limit_error(self):
        """Test RateLimitError."""
        error = RateLimitError("Rate limit exceeded", retry_after=60.0)
        
        assert isinstance(error, RetryableError)
        assert isinstance(error, OpenCastBotError)
        assert error.context['retry_after'] == 60.0
    
    def test_network_error(self):
        """Test NetworkError."""
        error = NetworkError("Connection timeout")
        
        assert isinstance(error, RetryableError)
        assert isinstance(error, OpenCastBotError)
    
    def test_temporary_api_error(self):
        """Test TemporaryAPIError."""
        error = TemporaryAPIError("Service unavailable")
        
        assert isinstance(error, RetryableError)
        assert isinstance(error, OpenCastBotError)
    
    def test_authentication_error(self):
        """Test AuthenticationError."""
        error = AuthenticationError("Invalid credentials")
        
        assert isinstance(error, NonRetryableError)
        assert isinstance(error, OpenCastBotError)
    
    def test_authorization_error(self):
        """Test AuthorizationError."""
        error = AuthorizationError("Access denied")
        
        assert isinstance(error, NonRetryableError)
        assert isinstance(error, OpenCastBotError)
    
    def test_invalid_data_error(self):
        """Test InvalidDataError."""
        error = InvalidDataError("Malformed data")
        
        assert isinstance(error, NonRetryableError)
        assert isinstance(error, OpenCastBotError)
    
    def test_resource_not_found_error(self):
        """Test ResourceNotFoundError."""
        error = ResourceNotFoundError("Resource not found")
        
        assert isinstance(error, NonRetryableError)
        assert isinstance(error, OpenCastBotError)


class TestLegacyExceptions:
    """Test legacy exception compatibility."""
    
    def test_category_not_found_error(self):
        """Test CategoryNotFoundError."""
        error = CategoryNotFoundError("test-category")
        
        assert isinstance(error, ResourceNotFoundError)
        assert isinstance(error, OpenCastBotError)
        assert error.context['category_id'] == "test-category"
        assert "Category 'test-category' not found" in str(error)
    
    def test_invalid_category_error(self):
        """Test InvalidCategoryError."""
        error = InvalidCategoryError("Invalid category data")
        
        assert isinstance(error, ValidationError)
        assert isinstance(error, OpenCastBotError)


class TestExceptionInheritance:
    """Test exception inheritance hierarchy."""
    
    def test_retryable_error_hierarchy(self):
        """Test that retryable errors inherit correctly."""
        errors = [RateLimitError("test"), NetworkError("test"), TemporaryAPIError("test")]
        
        for error in errors:
            assert isinstance(error, RetryableError)
            assert isinstance(error, OpenCastBotError)
            assert not isinstance(error, NonRetryableError)
    
    def test_non_retryable_error_hierarchy(self):
        """Test that non-retryable errors inherit correctly."""
        errors = [
            AuthenticationError("test"),
            AuthorizationError("test"),
            InvalidDataError("test"),
            ResourceNotFoundError("test")
        ]
        
        for error in errors:
            assert isinstance(error, NonRetryableError)
            assert isinstance(error, OpenCastBotError)
            assert not isinstance(error, RetryableError)
    
    def test_specific_error_hierarchy(self):
        """Test that specific errors inherit correctly."""
        config_error = ConfigurationError("test")
        content_error = ContentGenerationError("test")
        publish_error = PublishingError("test")
        api_error = APIError("test")
        validation_error = ValidationError("test")
        
        for error in [config_error, content_error, publish_error, api_error, validation_error]:
            assert isinstance(error, OpenCastBotError)


class TestExceptionUsage:
    """Test practical exception usage scenarios."""
    
    def test_exception_chaining(self):
        """Test exception chaining with cause."""
        original_error = ValueError("Original problem")
        
        try:
            raise original_error
        except ValueError as e:
            wrapped_error = APIError("API call failed", cause=e)
            
            assert wrapped_error.cause == original_error
            assert "Caused by: Original problem" in str(wrapped_error)
    
    def test_exception_context_building(self):
        """Test building rich context information."""
        error = ContentGenerationError(
            "Failed to generate content",
            category_id="test-category",
            topic="test topic",
            context={
                "attempt": 3,
                "max_retries": 5,
                "model": "gpt-3.5-turbo"
            }
        )
        
        assert error.context['category_id'] == "test-category"
        assert error.context['topic'] == "test topic"
        assert error.context['attempt'] == 3
        assert error.context['max_retries'] == 5
        assert error.context['model'] == "gpt-3.5-turbo"
    
    def test_exception_serialization(self):
        """Test exception serialization for logging."""
        error = PublishingError(
            "Failed to publish",
            platform="twitter",
            content_preview="Test content",
            context={"retry_count": 2}
        )
        
        error_dict = error.to_dict()
        
        # Verify all required fields are present
        required_fields = [
            'error_type', 'error_code', 'message', 'context', 
            'timestamp', 'cause', 'traceback'
        ]
        
        for field in required_fields:
            assert field in error_dict
        
        # Verify context is properly merged
        assert error_dict['context']['platform'] == "twitter"
        assert error_dict['context']['content_preview'] == "Test content"
        assert error_dict['context']['retry_count'] == 2 