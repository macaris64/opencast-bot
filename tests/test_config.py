"""
Tests for configuration module in OpenCast Bot.

This module tests the Config class and environment variable handling
defined in bot/config.py.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from bot.config import Config, get_config, reset_config
from bot.utils.exceptions import ConfigurationError, ValidationError


class TestConfig:
    """Test cases for Config class."""
    
    @pytest.fixture(autouse=True)
    def reset_config_instance(self):
        """Reset config instance before each test."""
        reset_config()
        yield
        reset_config()
    
    def test_config_creation_with_defaults(self):
        """Test creating config with default values."""
        with patch.dict(os.environ, {
            'OPENAI_API_KEY': 'test-key',
            'CATEGORIES_DIRECTORY': '/tmp/test',
            'DRY_RUN': 'false',
            'LOG_LEVEL': 'INFO'
        }, clear=True):
            config = Config()
            
            assert config.openai_api_key == 'test-key'
            assert config.categories_directory == '/tmp/test'
            assert config.dry_run is False
            assert config.log_level == 'INFO'
            assert config.openai_model == 'gpt-3.5-turbo'
            assert config.openai_max_tokens == 150
            assert config.openai_temperature == 0.7
            assert config.content_min_length == 20
            assert config.content_max_length == 220
            assert config.required_hashtag_count == 2
    
    def test_config_from_env_file(self):
        """Test loading config from environment variables."""
        with patch.dict(os.environ, {
            'OPENAI_API_KEY': 'env-file-key',
            'DRY_RUN': 'true',
            'LOG_LEVEL': 'DEBUG'
        }, clear=True):
            config = Config()
            
            assert config.openai_api_key == 'env-file-key'
            assert config.dry_run is True
            assert config.log_level == 'DEBUG'
    
    def test_config_validation_api_key_present(self):
        """Test config validation with API key present."""
        # Test that config loads successfully when API key is available
        config = Config()
        # API key should be loaded from environment or .env file
        assert config.openai_api_key is not None
        assert len(config.openai_api_key) > 10  # Basic validation
        assert config.openai_api_key.startswith("sk-")  # OpenAI API key format
    
    def test_config_validation_api_key_missing(self):
        """Test config validation with missing API key."""
        # Remove OPENAI_API_KEY specifically and disable .env file
        env_without_key = {k: v for k, v in os.environ.items() if k != 'OPENAI_API_KEY'}
        with patch.dict(os.environ, env_without_key, clear=True):
            # Create config without .env file - should fail Pydantic validation
            with pytest.raises(Exception) as exc_info:  # Pydantic ValidationError
                Config(_env_file=None)
            assert "Field required" in str(exc_info.value) or "openai_api_key" in str(exc_info.value)
    
    def test_config_validation_api_key_empty(self):
        """Test config validation with empty API key."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "   "}, clear=True):
            with pytest.raises(ConfigurationError) as exc_info:
                Config()
            assert "OpenAI API key is required" in str(exc_info.value)
    
    def test_config_validation_invalid_content_length(self):
        """Test config validation with invalid content length."""
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-key",
            "CONTENT_MIN_LENGTH": "100",
            "CONTENT_MAX_LENGTH": "50"
        }, clear=True):
            with pytest.raises(ConfigurationError) as exc_info:
                Config()
            assert "Configuration initialization failed" in str(exc_info.value)
    
    def test_config_validation_negative_hashtag_count(self):
        """Test config validation with negative hashtag count."""
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-key",
            "REQUIRED_HASHTAG_COUNT": "-1"
        }, clear=True):
            with pytest.raises(ConfigurationError) as exc_info:
                Config()
            assert "Configuration initialization failed" in str(exc_info.value)
    
    def test_config_validation_negative_max_retries(self):
        """Test config validation with negative max retries."""
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-key",
            "MAX_RETRIES": "-1"
        }, clear=True):
            with pytest.raises(ConfigurationError) as exc_info:
                Config()
            assert "Configuration initialization failed" in str(exc_info.value)
    
    def test_config_validation_negative_retry_delay(self):
        """Test config validation with negative retry delay."""
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-key",
            "RETRY_DELAY": "-1.0"
        }, clear=True):
            with pytest.raises(ConfigurationError) as exc_info:
                Config()
            assert "Configuration initialization failed" in str(exc_info.value)
    
    def test_config_validation_unexpected_error(self):
        """Test config validation with unexpected error."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
            with patch.object(Config, '_validate_configuration') as mock_validate:
                mock_validate.side_effect = Exception("Unexpected error")
                
                with pytest.raises(ConfigurationError) as exc_info:
                    Config()
                assert "Configuration initialization failed" in str(exc_info.value)
    
    def test_config_initialization_logging_failure(self):
        """Test config initialization when logging setup fails."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
            with patch('bot.config.setup_logging') as mock_setup:
                mock_setup.side_effect = Exception("Logging setup failed")
                
                with pytest.raises(ConfigurationError) as exc_info:
                    Config()
                assert "Configuration initialization failed" in str(exc_info.value)
    
    def test_config_boolean_parsing(self):
        """Test boolean environment variable parsing."""
        test_cases = [
            ('true', True),
            ('True', True),
            ('TRUE', True),
            ('1', True),
            ('yes', True),
            ('false', False),
            ('False', False),
            ('FALSE', False),
            ('0', False),
            ('no', False),
        ]
        
        for env_value, expected in test_cases:
            with patch.dict(os.environ, {
                'OPENAI_API_KEY': 'test-key',
                'DRY_RUN': env_value
            }, clear=True):
                config = Config()
                assert config.dry_run == expected, f"Failed for '{env_value}'"
        
        # Test empty string separately as it should raise validation error
        with patch.dict(os.environ, {
            'OPENAI_API_KEY': 'test-key',
            'DRY_RUN': ''
        }, clear=True):
            with pytest.raises(Exception):  # Should raise validation error for empty string
                Config()
    
    def test_openai_configuration_properties(self):
        """Test OpenAI-specific configuration properties."""
        with patch.dict(os.environ, {
            'OPENAI_API_KEY': 'test-key',
            'OPENAI_MODEL': 'gpt-4',
            'OPENAI_MAX_TOKENS': '150',
            'OPENAI_TEMPERATURE': '0.8'
        }, clear=True):
            config = Config()
            
            assert config.openai_model == 'gpt-4'
            assert config.openai_max_tokens == 150
            assert config.openai_temperature == 0.8
    
    def test_platform_configuration_properties(self):
        """Test platform-specific configuration properties."""
        with patch.dict(os.environ, {
            'OPENAI_API_KEY': 'test-key',
            'TWITTER_ENABLED': 'true',
            'TELEGRAM_ENABLED': 'false',
            'TWITTER_API_KEY': 'twitter-key',
            'TELEGRAM_BOT_TOKEN': 'telegram-token'
        }, clear=True):
            config = Config()
            
            assert config.twitter_enabled is True
            assert config.telegram_enabled is False
            assert config.twitter_api_key == 'twitter-key'
            assert config.telegram_bot_token == 'telegram-token'
    
    def test_get_enabled_platforms(self):
        """Test getting list of enabled platforms."""
        with patch.dict(os.environ, {
            'OPENAI_API_KEY': 'test-key',
            'TWITTER_ENABLED': 'true',
            'TELEGRAM_ENABLED': 'true',
            'TWITTER_API_KEY': 'twitter-key',
            'TWITTER_API_SECRET': 'twitter-secret',
            'TWITTER_ACCESS_TOKEN': 'twitter-token',
            'TWITTER_ACCESS_TOKEN_SECRET': 'twitter-token-secret',
            'TELEGRAM_BOT_TOKEN': 'telegram-token',
            'TELEGRAM_CHAT_ID': 'telegram-chat-id'
        }, clear=True):
            config = Config()
            platforms = config.get_enabled_platforms()
            
            assert 'twitter' in platforms
            assert 'telegram' in platforms
            assert len(platforms) == 2
    
    def test_get_enabled_platforms_none_enabled(self):
        """Test getting enabled platforms when none are enabled."""
        with patch.dict(os.environ, {
            'OPENAI_API_KEY': 'test-key',
            'TWITTER_ENABLED': 'false',
            'TELEGRAM_ENABLED': 'false'
        }, clear=True):
            config = Config()
            platforms = config.get_enabled_platforms()
            
            assert platforms == []
    
    def test_validate_twitter_config(self):
        """Test Twitter configuration validation."""
        # Valid Twitter config
        with patch.dict(os.environ, {
            'OPENAI_API_KEY': 'test-key',
            'TWITTER_ENABLED': 'true',
            'TWITTER_API_KEY': 'key',
            'TWITTER_API_SECRET': 'secret',
            'TWITTER_ACCESS_TOKEN': 'token',
            'TWITTER_ACCESS_TOKEN_SECRET': 'token_secret'
        }, clear=True):
            config = Config()
            assert config.validate_twitter_config() is True

        # Invalid Twitter config (missing keys) - clear all env vars
        with patch.dict(os.environ, {
            'OPENAI_API_KEY': 'test-key',
            'TWITTER_ENABLED': 'true',
            'TWITTER_API_KEY': '',
            'TWITTER_API_SECRET': '',
            'TWITTER_ACCESS_TOKEN': '',
            'TWITTER_ACCESS_TOKEN_SECRET': ''
        }, clear=True):
            config = Config()
            assert config.validate_twitter_config() is False
    
    def test_validate_telegram_config(self):
        """Test Telegram configuration validation."""
        # Valid Telegram config
        with patch.dict(os.environ, {
            'OPENAI_API_KEY': 'test-key',
            'TELEGRAM_ENABLED': 'true',
            'TELEGRAM_BOT_TOKEN': 'bot-token',
            'TELEGRAM_CHAT_ID': 'chat-id'
        }, clear=True):
            config = Config()
            assert config.validate_telegram_config() is True

        # Invalid Telegram config (missing keys) - clear all env vars
        with patch.dict(os.environ, {
            'OPENAI_API_KEY': 'test-key',
            'TELEGRAM_ENABLED': 'true',
            'TELEGRAM_BOT_TOKEN': '',
            'TELEGRAM_CHAT_ID': ''
        }, clear=True):
            config = Config()
            assert config.validate_telegram_config() is False
    
    def test_setup_logging(self):
        """Test logging setup during config initialization."""
        with patch.dict(os.environ, {
            'OPENAI_API_KEY': 'test-key',
            'LOG_LEVEL': 'DEBUG'
        }, clear=True):
            with patch('bot.config.setup_logging') as mock_setup_logging:
                config = Config()
                
                # setup_logging should be called during initialization
                mock_setup_logging.assert_called_once_with(level='DEBUG')
                
                # Config should have a logger
                assert hasattr(config, 'logger')
                assert config.logger is not None
    
    def test_content_validation_properties(self):
        """Test content validation configuration properties."""
        with patch.dict(os.environ, {
            'OPENAI_API_KEY': 'test-key',
            'CONTENT_MIN_LENGTH': '150',
            'CONTENT_MAX_LENGTH': '250',
            'REQUIRED_HASHTAG_COUNT': '3'
        }, clear=True):
            config = Config()
            
            assert config.content_min_length == 150
            assert config.content_max_length == 250
            assert config.required_hashtag_count == 3
    
    def test_get_config_function(self):
        """Test get_config function."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
            config1 = get_config()
            config2 = get_config()
            
            # Should return the same instance
            assert config1 is config2
    
    def test_reset_config_function(self):
        """Test reset_config function."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
            config1 = get_config()
            reset_config()
            config2 = get_config()
            
            # Should return different instances after reset
            assert config1 is not config2
    
    def test_config_backward_compatibility(self):
        """Test backward compatibility config function."""
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-key",
            "CONTENT_MIN_LENGTH": "20",
            "CONTENT_MAX_LENGTH": "220"
        }, clear=True):
            config = Config()
            
            # Should work with current variable names
            assert config.content_min_length == 20
            assert config.content_max_length == 220 