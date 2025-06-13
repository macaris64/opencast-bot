"""
Twitter (X) publisher module for OpenCast Bot.

This module handles posting content to X (formerly Twitter) platform using tweepy.
"""

from typing import Optional

import tweepy
from pydantic import BaseModel

from bot.models.topic import PostContent, PostStatus
from bot.utils import (
    get_logger, LoggerMixin, log_execution_time,
    PublishingError, APIError, ValidationError, 
    RateLimitError, AuthenticationError, AuthorizationError,
    NetworkError, NonRetryableError
)


class TwitterConfig(BaseModel):
    """Configuration for Twitter API integration."""
    
    api_key: str
    api_secret: str
    access_token: str
    access_token_secret: str
    bearer_token: Optional[str] = None


class TwitterPublisher(LoggerMixin):
    """Publisher class for posting content to X (Twitter) using tweepy."""
    
    def __init__(self, config: TwitterConfig) -> None:
        """
        Initialize Twitter publisher with API credentials.
        
        Args:
            config: Twitter API configuration
        """
        super().__init__()
        self.config = config
        self.client: Optional[tweepy.Client] = None
        
        try:
            self._setup_client()
            self.logger.info(
                "TwitterPublisher initialized successfully",
                api_key_length=len(config.api_key) if config.api_key else 0,
                has_bearer_token=bool(config.bearer_token)
            )
        except Exception as e:
            setup_error = PublishingError(
                "Failed to initialize Twitter publisher",
                platform="twitter",
                cause=e
            )
            self.logger.error("Twitter publisher initialization failed", error=setup_error)
            raise setup_error
    
    def _setup_client(self) -> None:
        """Setup the Twitter API client using tweepy."""
        try:
            # Validate configuration
            if not all([self.config.api_key, self.config.api_secret, 
                       self.config.access_token, self.config.access_token_secret]):
                raise ValidationError(
                    "Missing required Twitter API credentials",
                    field_name="twitter_credentials",
                    validation_rule="all credentials must be provided"
                )
            
            # Setup API v2 client with OAuth 1.0a
            self.client = tweepy.Client(
                consumer_key=self.config.api_key,
                consumer_secret=self.config.api_secret,
                access_token=self.config.access_token,
                access_token_secret=self.config.access_token_secret,
                wait_on_rate_limit=True
            )
            
            self.logger.debug("Twitter API client configured successfully")
            
        except ValidationError:
            raise
        except Exception as e:
            api_error = APIError(
                f"Failed to setup Twitter API client: {str(e)}",
                api_name="twitter",
                operation="client_setup"
            )
            self.logger.error("Twitter client setup failed", error=api_error)
            raise api_error
    
    async def __aenter__(self) -> "TwitterPublisher":
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        # tweepy client doesn't need explicit cleanup
        if exc_type:
            self.logger.warning(
                "TwitterPublisher context exited with exception",
                exception_type=exc_type.__name__ if exc_type else None,
                exception_message=str(exc_val) if exc_val else None
            )
    
    @log_execution_time
    async def post_content(self, content: PostContent) -> bool:
        """
        Post content to Twitter.
        
        Args:
            content: Post content to publish
            
        Returns:
            True if post was successful, False otherwise
        """
        try:
            self.logger.info(
                "Starting Twitter post",
                content_length=len(content.content),
                hashtag_count=len(content.hashtags),
                content_preview=content.content[:50] + "..." if len(content.content) > 50 else content.content
            )
            
            # Validate content before posting
            if not self.validate_content(content):
                validation_error = ValidationError(
                    "Content validation failed for Twitter",
                    field_name="content",
                    field_value=content.content[:100],
                    validation_rule="Twitter content requirements"
                )
                self.logger.error("Content validation failed", error=validation_error)
                content.mark_as_failed()
                return False
            
            success = await self._send_tweet(content.content)
            
            if success:
                content.mark_as_posted()
                self.logger.info(
                    "Successfully posted to Twitter",
                    content_length=len(content.content),
                    platform="twitter"
                )
                return True
            else:
                content.mark_as_failed()
                self.logger.error(
                    "Failed to post to Twitter",
                    content_preview=content.content[:50] + "...",
                    platform="twitter"
                )
                return False
                
        except (ValidationError, PublishingError) as e:
            self.logger.error("Twitter posting failed", error=e)
            content.mark_as_failed()
            return False
        except Exception as e:
            posting_error = PublishingError(
                "Unexpected error during Twitter posting",
                platform="twitter",
                content_preview=content.content[:50] + "..." if len(content.content) > 50 else content.content,
                cause=e
            )
            self.logger.error("Unexpected Twitter posting error", error=posting_error)
            content.mark_as_failed()
            return False
    
    async def _send_tweet(self, tweet_text: str) -> bool:
        """
        Send a tweet using Twitter API v2 with tweepy.
        
        Args:
            tweet_text: Text content of the tweet
            
        Returns:
            True if tweet was sent successfully, False otherwise
            
        Raises:
            APIError: If API call fails
            RateLimitError: If rate limit is exceeded
            AuthenticationError: If authentication fails
            AuthorizationError: If authorization fails
        """
        if not self.client:
            raise APIError(
                "Twitter client not initialized",
                api_name="twitter",
                operation="send_tweet"
            )
        
        try:
            self.logger.debug(
                "Sending tweet",
                content_length=len(tweet_text),
                content_preview=tweet_text[:50] + "..." if len(tweet_text) > 50 else tweet_text
            )
            
            # Use tweepy's create_tweet method
            response = self.client.create_tweet(text=tweet_text)
            
            if response.data:
                tweet_id = response.data["id"]
                self.logger.info(
                    "Tweet posted successfully",
                    tweet_id=tweet_id,
                    platform="twitter"
                )
                return True
            else:
                raise APIError(
                    "Failed to post tweet: No response data",
                    api_name="twitter",
                    operation="create_tweet"
                )
                
        except tweepy.TooManyRequests as e:
            rate_limit_error = RateLimitError(
                f"Twitter rate limit exceeded: {str(e)}",
                api_name="twitter",
                operation="create_tweet",
                retry_after=getattr(e, 'retry_after', None)
            )
            self.logger.error("Twitter rate limit exceeded", error=rate_limit_error)
            raise rate_limit_error
            
        except tweepy.Forbidden as e:
            auth_error = AuthorizationError(
                f"Twitter API forbidden error: {str(e)}",
                api_name="twitter",
                operation="create_tweet"
            )
            self.logger.error("Twitter API authorization failed", error=auth_error)
            raise auth_error
            
        except tweepy.Unauthorized as e:
            auth_error = AuthenticationError(
                f"Twitter API unauthorized error: {str(e)}",
                api_name="twitter",
                operation="create_tweet"
            )
            self.logger.error("Twitter API authentication failed", error=auth_error)
            raise auth_error
            
        except tweepy.BadRequest as e:
            validation_error = ValidationError(
                f"Twitter API bad request: {str(e)}",
                field_name="tweet_content",
                field_value=tweet_text[:100],
                validation_rule="Twitter API requirements"
            )
            self.logger.error("Twitter API bad request", error=validation_error)
            raise validation_error
            
        except Exception as e:
            api_error = APIError(
                f"Failed to send tweet: {str(e)}",
                api_name="twitter",
                operation="create_tweet"
            )
            self.logger.error("Twitter API call failed", error=api_error)
            raise api_error
    
    def test_connection(self) -> bool:
        """
        Test the Twitter API connection.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            self.logger.info("Testing Twitter API connection")
            
            # Try to get user information
            user = self.client.get_me()
            
            if user.data:
                self.logger.info(
                    "Twitter API connection test successful",
                    username=user.data.username,
                    user_id=user.data.id,
                    platform="twitter"
                )
                return True
            else:
                self.logger.error(
                    "Twitter API connection test failed: No user data",
                    platform="twitter"
                )
                return False
                
        except Exception as e:
            connection_error = APIError(
                f"Twitter API connection test failed: {str(e)}",
                api_name="twitter",
                operation="get_me"
            )
            self.logger.error("Twitter connection test failed", error=connection_error)
            return False
    
    def validate_content(self, content: PostContent) -> bool:
        """
        Validate content meets Twitter requirements.
        
        Args:
            content: Content to validate
            
        Returns:
            True if content is valid for Twitter, False otherwise
        """
        try:
            # Check character limit (280 for Twitter, but our system uses 20-220)
            content_length = len(content.content)
            if not (20 <= content_length <= 220):
                self.logger.warning(
                    "Content length validation failed",
                    content_length=content_length,
                    min_length=20,
                    max_length=220,
                    platform="twitter"
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
                    platform="twitter"
                )
                return False
            
            self.logger.debug(
                "Content validation successful",
                content_length=content_length,
                hashtag_count=hashtag_count,
                platform="twitter"
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