"""
Tests for configuration module in OpenCast Bot.

This module tests the Config class and environment variable handling
defined in bot/config.py.
"""

import os
import tempfile
from unittest.mock import patch, MagicMock

import pytest

from bot.config import Config


class TestConfig:
    """Test cases for Config class."""
    
    def test_config_creation_with_defaults(self):
        """Test creating config with default values."""
        with patch.dict(os.environ, {
            'OPENAI_API_KEY': 'test-key',
            'DATA_DIRECTORY': '/tmp/test',
            'DRY_RUN': 'false',
            'LOG_LEVEL': 'INFO'
        }, clear=True):
            config = Config()
            
            assert config.openai_api_key == 'test-key'
            assert config.data_directory == '/tmp/test'
            assert config.dry_run is False
            assert config.log_level == 'INFO'
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
    
    @patch('bot.config.logging.basicConfig')
    def test_setup_logging(self, mock_basic_config):
        """Test logging setup."""
        with patch.dict(os.environ, {
            'OPENAI_API_KEY': 'test-key',
            'LOG_LEVEL': 'DEBUG'
        }, clear=True):
            config = Config()
            config.setup_logging()
            
            mock_basic_config.assert_called_once()
            call_args = mock_basic_config.call_args
            assert 'level' in call_args.kwargs
            assert 'format' in call_args.kwargs
    
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
        from bot.config import get_config, reset_config
        
        # Reset first
        reset_config()
        
        # Get config
        config1 = get_config()
        config2 = get_config()
        
        # Should return same instance
        assert config1 is config2
        assert isinstance(config1, Config)
    
    def test_reset_config_function(self):
        """Test reset_config function."""
        from bot.config import get_config, reset_config
        
        # Get initial config
        config1 = get_config()
        
        # Reset and get new config
        reset_config()
        config2 = get_config()
        
        # Should be different instances
        assert config1 is not config2
        assert isinstance(config2, Config)
    
    def test_config_backward_compatibility(self):
        """Test backward compatibility config function."""
        from bot.config import config
        
        # Should return Config instance
        result = config()
        assert isinstance(result, Config) 