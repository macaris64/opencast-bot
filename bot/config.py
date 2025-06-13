"""
Configuration module for OpenCast Bot.

This module handles application configuration using Pydantic settings
and environment variables.
"""

from typing import Optional

from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings

from .utils import get_logger, setup_logging, ConfigurationError, ValidationError


class Config(BaseSettings):
    """Main configuration class for OpenCast Bot."""
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # Ignore extra fields to avoid validation errors
    )
    
    # OpenAI Configuration
    openai_api_key: str = Field(env="OPENAI_API_KEY", description="OpenAI API key")
    openai_model: str = Field(default="gpt-3.5-turbo", env="OPENAI_MODEL", description="OpenAI model to use")
    openai_max_tokens: int = Field(default=150, env="OPENAI_MAX_TOKENS", description="Maximum tokens for OpenAI response")
    openai_temperature: float = Field(default=0.7, env="OPENAI_TEMPERATURE", description="Temperature for OpenAI response")
    
    # Twitter Configuration
    twitter_api_key: str = Field(default="", env="TWITTER_API_KEY", description="Twitter API key")
    twitter_api_secret: str = Field(default="", env="TWITTER_API_SECRET", description="Twitter API secret")
    twitter_access_token: str = Field(default="", env="TWITTER_ACCESS_TOKEN", description="Twitter access token")
    twitter_access_token_secret: str = Field(default="", env="TWITTER_ACCESS_TOKEN_SECRET", description="Twitter access token secret")
    twitter_bearer_token: str = Field(default="", env="TWITTER_BEARER_TOKEN", description="Twitter bearer token")
    twitter_enabled: bool = Field(default=False, env="TWITTER_ENABLED", description="Enable Twitter posting")
    
    # Telegram Configuration
    telegram_bot_token: str = Field(default="", env="TELEGRAM_BOT_TOKEN", description="Telegram bot token")
    telegram_chat_id: str = Field(default="", env="TELEGRAM_CHAT_ID", description="Telegram chat ID")
    telegram_parse_mode: str = Field(default="HTML", env="TELEGRAM_PARSE_MODE", description="Telegram message parse mode")
    telegram_enabled: bool = Field(default=False, env="TELEGRAM_ENABLED", description="Enable Telegram posting")
    
    # Content Configuration
    content_min_length: int = Field(default=20, env="CONTENT_MIN_LENGTH", description="Minimum content length")
    content_max_length: int = Field(default=220, env="CONTENT_MAX_LENGTH", description="Maximum content length")
    required_hashtag_count: int = Field(default=2, env="REQUIRED_HASHTAG_COUNT", description="Required number of hashtags")
    default_prompt_template: str = Field(
        default="Create a professional development tip about {topic}. Keep it concise and actionable. Include exactly 2 relevant hashtags.",
        env="DEFAULT_PROMPT_TEMPLATE",
        description="Default prompt template for content generation"
    )
    
    # General Configuration
    dry_run: bool = Field(default=False, env="DRY_RUN", description="Enable dry run mode")
    log_level: str = Field(default="INFO", env="LOG_LEVEL", description="Logging level")
    retry_delay: float = Field(default=1.0, env="RETRY_DELAY", description="Delay between retries in seconds")
    max_retries: int = Field(default=3, env="MAX_RETRIES", description="Maximum number of retries")
    
    # Database Configuration
    categories_directory: str = Field(default="categories", env="CATEGORIES_DIRECTORY", description="Directory containing category files")
    outputs_directory: str = Field(default="outputs", env="OUTPUTS_DIRECTORY", description="Directory for output files")
    
    def __init__(self, **kwargs):
        """Initialize configuration with enhanced logging."""
        super().__init__(**kwargs)
        
        # Initialize logger using composition instead of inheritance
        self._logger = get_logger(self.__class__.__name__)
        
        try:
            # Setup logging with configured level
            setup_logging(level=self.log_level)
            
            # Log configuration initialization
            self._logger.info(
                "Configuration initialized successfully",
                log_level=self.log_level,
                dry_run=self.dry_run,
                twitter_enabled=self.twitter_enabled,
                telegram_enabled=self.telegram_enabled
            )
            
            # Validate critical configuration
            self._validate_configuration()
            
        except Exception as e:
            # Use basic logging if structured logging fails
            import logging
            logging.basicConfig(level=logging.ERROR)
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to initialize configuration: {e}")
            raise ConfigurationError("Configuration initialization failed", cause=e)
    
    @property
    def logger(self):
        """Get logger instance."""
        return self._logger
    
    def _validate_configuration(self) -> None:
        """Validate configuration values."""
        try:
            # Validate OpenAI configuration
            if not self.openai_api_key or not self.openai_api_key.strip():
                raise ConfigurationError(
                    "OpenAI API key is required",
                    config_key="openai_api_key"
                )
            
            # Validate content length settings
            if self.content_min_length >= self.content_max_length:
                raise ValidationError(
                    "content_min_length must be less than content_max_length",
                    field_name="content_min_length",
                    field_value=self.content_min_length,
                    validation_rule="min_length < max_length"
                )
            
            # Validate hashtag count
            if self.required_hashtag_count < 0:
                raise ValidationError(
                    "required_hashtag_count must be non-negative",
                    field_name="required_hashtag_count",
                    field_value=self.required_hashtag_count,
                    validation_rule="value >= 0"
                )
            
            # Validate retry settings
            if self.max_retries < 0:
                raise ValidationError(
                    "max_retries must be non-negative",
                    field_name="max_retries",
                    field_value=self.max_retries,
                    validation_rule="value >= 0"
                )
            
            if self.retry_delay < 0:
                raise ValidationError(
                    "retry_delay must be non-negative",
                    field_name="retry_delay",
                    field_value=self.retry_delay,
                    validation_rule="value >= 0"
                )
            
            self._logger.info("Configuration validation completed successfully")
            
        except (ConfigurationError, ValidationError) as e:
            self._logger.error("Configuration validation failed", error=e)
            raise
        except Exception as e:
            config_error = ConfigurationError(
                "Unexpected error during configuration validation",
                cause=e
            )
            self._logger.error("Configuration validation failed", error=config_error)
            raise config_error
    
    def validate_twitter_config(self) -> bool:
        """
        Validate that all required Twitter configuration is present.
        
        Returns:
            True if Twitter config is valid, False otherwise
        """
        try:
            required_fields = [
                ("twitter_api_key", self.twitter_api_key),
                ("twitter_api_secret", self.twitter_api_secret),
                ("twitter_access_token", self.twitter_access_token),
                ("twitter_access_token_secret", self.twitter_access_token_secret)
            ]
            
            missing_fields = []
            for field_name, field_value in required_fields:
                if not field_value or not field_value.strip():
                    missing_fields.append(field_name)
            
            if missing_fields:
                self._logger.warning(
                    "Twitter configuration incomplete",
                    missing_fields=missing_fields,
                    platform="twitter"
                )
                return False
            
            self._logger.debug("Twitter configuration validated successfully")
            return True
            
        except Exception as e:
            self._logger.error(
                "Error validating Twitter configuration",
                error=e,
                platform="twitter"
            )
            return False
    
    def validate_telegram_config(self) -> bool:
        """
        Validate that all required Telegram configuration is present.
        
        Returns:
            True if Telegram config is valid, False otherwise
        """
        try:
            missing_fields = []
            
            if not self.telegram_bot_token or not self.telegram_bot_token.strip():
                missing_fields.append("telegram_bot_token")
            
            if not self.telegram_chat_id or not self.telegram_chat_id.strip():
                missing_fields.append("telegram_chat_id")
            
            if missing_fields:
                self._logger.warning(
                    "Telegram configuration incomplete",
                    missing_fields=missing_fields,
                    platform="telegram"
                )
                return False
            
            self._logger.debug("Telegram configuration validated successfully")
            return True
            
        except Exception as e:
            self._logger.error(
                "Error validating Telegram configuration",
                error=e,
                platform="telegram"
            )
            return False
    
    def get_enabled_platforms(self) -> list[str]:
        """
        Get list of enabled platforms based on configuration.
        
        Returns:
            List of platform names that are properly configured
        """
        platforms = []
        
        try:
            if self.twitter_enabled and self.validate_twitter_config():
                platforms.append("twitter")
                self._logger.debug("Twitter platform enabled")
            
            if self.telegram_enabled and self.validate_telegram_config():
                platforms.append("telegram")
                self._logger.debug("Telegram platform enabled")
            
            self._logger.info(
                "Platform configuration completed",
                enabled_platforms=platforms,
                platform_count=len(platforms)
            )
            
            return platforms
            
        except Exception as e:
            config_error = ConfigurationError(
                "Error determining enabled platforms",
                cause=e
            )
            self._logger.error("Platform configuration failed", error=config_error)
            raise config_error


# Global configuration instance - lazy loaded
_config_instance = None

def get_config() -> Config:
    """Get the global configuration instance (lazy loaded)."""
    global _config_instance
    if _config_instance is None:
        try:
            _config_instance = Config()
        except Exception as e:
            # Create a basic logger for this error since config failed
            logger = get_logger("config")
            logger.error("Failed to initialize configuration", error=e)
            raise
    return _config_instance

def reset_config():
    """Reset the global configuration instance (useful for testing)."""
    global _config_instance
    _config_instance = None

# For backward compatibility
def config() -> Config:
    """Get the global configuration instance."""
    return get_config() 