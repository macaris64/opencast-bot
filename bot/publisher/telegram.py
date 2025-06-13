"""
Telegram publisher module for OpenCast Bot.

This module handles posting content to Telegram channels/chats.
"""

from typing import Optional

import httpx
from pydantic import BaseModel

from bot.models.topic import PostContent, PostStatus
from bot.utils import (
    get_logger, LoggerMixin, log_execution_time,
    PublishingError, APIError, ValidationError, 
    RateLimitError, AuthenticationError, AuthorizationError,
    NetworkError, NonRetryableError
)


class TelegramConfig(BaseModel):
    """Configuration for Telegram Bot API integration."""
    
    bot_token: str
    chat_id: str  # Can be channel username (@channel) or numeric chat ID
    parse_mode: str = "HTML"  # HTML or Markdown


class TelegramPublisher(LoggerMixin):
    """Publisher class for posting content to Telegram."""
    
    def __init__(self, config: TelegramConfig) -> None:
        """
        Initialize Telegram publisher with bot credentials.
        
        Args:
            config: Telegram bot configuration
        """
        super().__init__()
        self.config = config
        self.client: Optional[httpx.AsyncClient] = None
        
        try:
            # Validate configuration
            if not config.bot_token or not config.chat_id:
                raise ValidationError(
                    "Missing required Telegram configuration",
                    field_name="telegram_credentials",
                    validation_rule="bot_token and chat_id must be provided"
                )
            
            self.base_url = f"https://api.telegram.org/bot{config.bot_token}"
            
            self.logger.info(
                "TelegramPublisher initialized successfully",
                chat_id=config.chat_id,
                parse_mode=config.parse_mode,
                bot_token_length=len(config.bot_token) if config.bot_token else 0
            )
            
        except Exception as e:
            setup_error = PublishingError(
                "Failed to initialize Telegram publisher",
                platform="telegram",
                cause=e
            )
            self.logger.error("Telegram publisher initialization failed", error=setup_error)
            raise setup_error
    
    async def __aenter__(self) -> "TelegramPublisher":
        """Async context manager entry."""
        try:
            self.client = httpx.AsyncClient(timeout=30.0)
            self.logger.debug("Telegram HTTP client initialized")
            return self
        except Exception as e:
            network_error = NetworkError(
                "Failed to initialize Telegram HTTP client",
                operation="client_init",
                cause=e
            )
            self.logger.error("Telegram client initialization failed", error=network_error)
            raise network_error
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        try:
            if self.client:
                await self.client.aclose()
                self.logger.debug("Telegram HTTP client closed")
        except Exception as e:
            self.logger.warning(
                "Error closing Telegram HTTP client",
                error_message=str(e)
            )
        
        if exc_type:
            self.logger.warning(
                "TelegramPublisher context exited with exception",
                exception_type=exc_type.__name__ if exc_type else None,
                exception_message=str(exc_val) if exc_val else None
            )
    
    @log_execution_time
    async def post_content(self, content: PostContent) -> bool:
        """
        Post content to Telegram.
        
        Args:
            content: Post content to publish
            
        Returns:
            True if post was successful, False otherwise
        """
        try:
            self.logger.info(
                "Starting Telegram post",
                content_length=len(content.content),
                hashtag_count=len(content.hashtags),
                content_preview=content.content[:50] + "..." if len(content.content) > 50 else content.content,
                chat_id=self.config.chat_id
            )
            
            # Validate content before posting
            if not self.validate_content(content):
                validation_error = ValidationError(
                    "Content validation failed for Telegram",
                    field_name="content",
                    field_value=content.content[:100],
                    validation_rule="Telegram content requirements"
                )
                self.logger.error("Content validation failed", error=validation_error)
                content.mark_as_failed()
                return False
            
            success = await self._send_message(content.content)
            
            if success:
                content.mark_as_posted()
                self.logger.info(
                    "Successfully posted to Telegram",
                    content_length=len(content.content),
                    platform="telegram",
                    chat_id=self.config.chat_id
                )
                return True
            else:
                content.mark_as_failed()
                self.logger.error(
                    "Failed to post to Telegram",
                    content_preview=content.content[:50] + "...",
                    platform="telegram",
                    chat_id=self.config.chat_id
                )
                return False
                
        except (ValidationError, PublishingError) as e:
            self.logger.error("Telegram posting failed", error=e)
            content.mark_as_failed()
            return False
        except Exception as e:
            posting_error = PublishingError(
                "Unexpected error during Telegram posting",
                platform="telegram",
                content_preview=content.content[:50] + "..." if len(content.content) > 50 else content.content,
                cause=e
            )
            self.logger.error("Unexpected Telegram posting error", error=posting_error)
            content.mark_as_failed()
            return False
    
    async def _send_message(self, message_text: str) -> bool:
        """
        Send a message using Telegram Bot API.
        
        Args:
            message_text: Text content of the message
            
        Returns:
            True if message was sent successfully, False otherwise
            
        Raises:
            APIError: If API call fails
            NetworkError: If network request fails
            AuthenticationError: If bot token is invalid
            ValidationError: If message format is invalid
        """
        if not self.client:
            raise APIError(
                "Telegram client not initialized",
                api_name="telegram",
                operation="send_message"
            )
        
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.config.chat_id,
                "text": message_text,
                "parse_mode": self.config.parse_mode,
            }
            
            self.logger.debug(
                "Sending Telegram message",
                content_length=len(message_text),
                content_preview=message_text[:50] + "..." if len(message_text) > 50 else message_text,
                chat_id=self.config.chat_id,
                parse_mode=self.config.parse_mode
            )
            
            response = await self.client.post(url, json=payload)
            
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get("ok"):
                    message_id = response_data.get("result", {}).get("message_id")
                    self.logger.info(
                        "Telegram message sent successfully",
                        message_id=message_id,
                        platform="telegram",
                        chat_id=self.config.chat_id
                    )
                    return True
                else:
                    error_description = response_data.get('description', 'Unknown error')
                    error_code = response_data.get('error_code')
                    
                    # Handle specific Telegram API errors
                    if error_code == 401:
                        raise AuthenticationError(
                            f"Telegram bot token is invalid: {error_description}",
                            api_name="telegram",
                            operation="send_message"
                        )
                    elif error_code == 400:
                        raise ValidationError(
                            f"Telegram API validation error: {error_description}",
                            field_name="message",
                            field_value=message_text[:100],
                            validation_rule="Telegram API requirements"
                        )
                    elif error_code == 429:
                        raise RateLimitError(
                            f"Telegram rate limit exceeded: {error_description}",
                            api_name="telegram",
                            operation="send_message"
                        )
                    else:
                        raise APIError(
                            f"Telegram API error: {error_description}",
                            api_name="telegram",
                            operation="send_message",
                            error_code=error_code
                        )
            else:
                raise NetworkError(
                    f"HTTP error {response.status_code}: {response.text}",
                    operation="telegram_api_request",
                    status_code=response.status_code
                )
            
        except httpx.TimeoutException as e:
            timeout_error = NetworkError(
                f"Telegram API request timeout: {str(e)}",
                operation="send_message"
            )
            self.logger.error("Telegram API timeout", error=timeout_error)
            raise timeout_error
            
        except httpx.NetworkError as e:
            network_error = NetworkError(
                f"Telegram API network error: {str(e)}",
                operation="send_message"
            )
            self.logger.error("Telegram network error", error=network_error)
            raise network_error
            
        except (ValidationError, AuthenticationError, RateLimitError, APIError, NetworkError):
            raise
        except Exception as e:
            api_error = APIError(
                f"Failed to send Telegram message: {str(e)}",
                api_name="telegram",
                operation="send_message"
            )
            self.logger.error("Telegram API call failed", error=api_error)
            raise api_error
    
    async def send_error_alert(self, error_message: str) -> bool:
        """
        Send an error alert to Telegram.
        
        Args:
            error_message: Error message to send
            
        Returns:
            True if alert was sent successfully, False otherwise
        """
        try:
            alert_text = f"🚨 OpenCast Bot Error Alert 🚨\n\n{error_message}"
            
            self.logger.info(
                "Sending error alert to Telegram",
                alert_preview=error_message[:100] + "..." if len(error_message) > 100 else error_message
            )
            
            success = await self._send_message(alert_text)
            
            if success:
                self.logger.info("Error alert sent successfully to Telegram")
            else:
                self.logger.error("Failed to send error alert to Telegram")
                
            return success
            
        except Exception as e:
            alert_error = PublishingError(
                "Failed to send error alert to Telegram",
                platform="telegram",
                cause=e
            )
            self.logger.error("Error alert sending failed", error=alert_error)
            return False
    
    def validate_content(self, content: PostContent) -> bool:
        """
        Validate content meets Telegram requirements.
        
        Args:
            content: Content to validate
            
        Returns:
            True if content is valid for Telegram, False otherwise
        """
        try:
            # Check character limit (Telegram supports up to 4096 characters, but our system uses 20-220)
            content_length = len(content.content)
            if not (20 <= content_length <= 220):
                self.logger.warning(
                    "Content length validation failed",
                    content_length=content_length,
                    min_length=20,
                    max_length=220,
                    platform="telegram"
                )
                return False
            
            # Check hashtag count (our system requires exactly 2)
            hashtag_count = len(content.hashtags)
            if hashtag_count != 2:
                self.logger.warning(
                    "Hashtag count validation failed",
                    expected_hashtags=2,
                    found_hashtags=hashtag_count,
                    hashtags=content.hashtags,
                    platform="telegram"
                )
                return False
            
            self.logger.debug(
                "Content validation successful",
                content_length=content_length,
                hashtag_count=hashtag_count,
                platform="telegram"
            )
            
            return True
            
        except Exception as e:
            validation_error = ValidationError(
                "Error during content validation",
                field_name="content",
                field_value=content.content[:100],
                cause=e
            )
            self.logger.error("Content validation error", error=validation_error)
            return False 