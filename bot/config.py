"""
Configuration module for OpenCast Bot.

This module handles application configuration using Pydantic settings
and environment variables.
"""

import logging
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """Main configuration class for OpenCast Bot."""
    
    # OpenAI Configuration
    openai_api_key: str = Field(env="OPENAI_API_KEY", description="OpenAI API key")
    openai_model: str = Field(default="gpt-3.5-turbo", env="OPENAI_MODEL", description="OpenAI model to use")
    openai_max_tokens: int = Field(default=150, env="OPENAI_MAX_TOKENS", description="Maximum tokens for OpenAI response")
    openai_temperature: float = Field(default=0.7, env="OPENAI_TEMPERATURE", description="Temperature for OpenAI generation")
    
    # Twitter/X Configuration
    twitter_enabled: bool = Field(default=False, env="TWITTER_ENABLED", description="Enable Twitter/X publishing")
    twitter_api_key: Optional[str] = Field(None, env="TWITTER_API_KEY", description="Twitter API key")
    twitter_api_secret: Optional[str] = Field(None, env="TWITTER_API_SECRET", description="Twitter API secret")
    twitter_access_token: Optional[str] = Field(None, env="TWITTER_ACCESS_TOKEN", description="Twitter access token")
    twitter_access_token_secret: Optional[str] = Field(None, env="TWITTER_ACCESS_TOKEN_SECRET", description="Twitter access token secret")
    twitter_bearer_token: Optional[str] = Field(None, env="TWITTER_BEARER_TOKEN", description="Twitter bearer token")
    
    # Telegram Configuration
    telegram_enabled: bool = Field(default=False, env="TELEGRAM_ENABLED", description="Enable Telegram publishing")
    telegram_bot_token: Optional[str] = Field(None, env="TELEGRAM_BOT_TOKEN", description="Telegram bot token")
    telegram_chat_id: Optional[str] = Field(None, env="TELEGRAM_CHAT_ID", description="Telegram chat/channel ID")
    telegram_parse_mode: str = Field(default="HTML", env="TELEGRAM_PARSE_MODE", description="Telegram message parse mode")
    
    # Application Configuration
    data_directory: str = Field(default="categories", env="DATA_DIRECTORY", description="Directory for category JSON files")
    output_directory: str = Field(default="outputs", env="OUTPUT_DIRECTORY", description="Directory for output files")
    log_level: str = Field(default="INFO", env="LOG_LEVEL", description="Logging level")
    dry_run: bool = Field(default=False, env="DRY_RUN", description="Enable dry-run mode (no actual posting)")
    
    # Content Generation Settings
    content_min_length: int = Field(default=20, env="CONTENT_MIN_LENGTH", description="Minimum content length")
    content_max_length: int = Field(default=220, env="CONTENT_MAX_LENGTH", description="Maximum content length")
    required_hashtag_count: int = Field(default=2, env="REQUIRED_HASHTAG_COUNT", description="Required number of hashtags")
    default_language: str = Field(default="tr", env="DEFAULT_LANGUAGE", description="Default content language")
    
    # Category Configuration
    default_prompt_template: str = Field(
        default="Create a concise tip about {topic}. Write 2-3 sentences with practical advice. End with exactly 2 hashtags. Keep total length between 20-220 characters.",
        env="DEFAULT_PROMPT_TEMPLATE",
        description="Default prompt template for categories"
    )
    category_config_override: bool = Field(default=True, env="CATEGORY_CONFIG_OVERRIDE", description="Allow categories to override global settings")
    enforce_global_validation: bool = Field(default=True, env="ENFORCE_GLOBAL_VALIDATION", description="Enforce global validation rules even if category has custom settings")
    
    # Rate Limiting and Retry Settings
    max_retries: int = Field(default=3, env="MAX_RETRIES", description="Maximum retry attempts for API calls")
    retry_delay: float = Field(default=1.0, env="RETRY_DELAY", description="Delay between retry attempts in seconds")
    rate_limit_delay: float = Field(default=0.5, env="RATE_LIMIT_DELAY", description="Delay between API calls to avoid rate limits")
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    def setup_logging(self) -> None:
        """Setup logging configuration based on log level."""
        logging.basicConfig(
            level=getattr(logging, self.log_level.upper()),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    def validate_twitter_config(self) -> bool:
        """
        Validate that all required Twitter configuration is present.
        
        Returns:
            True if Twitter config is valid, False otherwise
        """
        required_fields = [
            self.twitter_api_key,
            self.twitter_api_secret,
            self.twitter_access_token,
            self.twitter_access_token_secret
        ]
        return all(field is not None and field.strip() != "" for field in required_fields)
    
    def validate_telegram_config(self) -> bool:
        """
        Validate that all required Telegram configuration is present.
        
        Returns:
            True if Telegram config is valid, False otherwise
        """
        return (
            self.telegram_bot_token is not None and 
            self.telegram_bot_token.strip() != "" and
            self.telegram_chat_id is not None and
            self.telegram_chat_id.strip() != ""
        )
    
    def get_enabled_platforms(self) -> list[str]:
        """
        Get list of enabled platforms based on configuration.
        
        Returns:
            List of platform names that are properly configured
        """
        platforms = []
        
        if self.twitter_enabled and self.validate_twitter_config():
            platforms.append("twitter")
        
        if self.telegram_enabled and self.validate_telegram_config():
            platforms.append("telegram")
        
        return platforms


# Global configuration instance - lazy loaded
_config_instance = None

def get_config() -> Config:
    """Get the global configuration instance (lazy loaded)."""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance

def reset_config():
    """Reset the global configuration instance (useful for testing)."""
    global _config_instance
    _config_instance = None

# For backward compatibility
def config() -> Config:
    """Get the global configuration instance."""
    return get_config() 