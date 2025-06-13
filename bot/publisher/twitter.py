"""
Twitter (X) publisher module for OpenCast Bot.

This module handles posting content to X (formerly Twitter) platform using tweepy.
"""

import logging
from typing import Optional

import tweepy
from pydantic import BaseModel

from bot.models.topic import PostContent, PostStatus

logger = logging.getLogger(__name__)


class TwitterConfig(BaseModel):
    """Configuration for Twitter API integration."""
    
    api_key: str
    api_secret: str
    access_token: str
    access_token_secret: str
    bearer_token: Optional[str] = None


class TwitterPublisher:
    """Publisher class for posting content to X (Twitter) using tweepy."""
    
    def __init__(self, config: TwitterConfig) -> None:
        """
        Initialize Twitter publisher with API credentials.
        
        Args:
            config: Twitter API configuration
        """
        self.config = config
        self.client: Optional[tweepy.Client] = None
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._setup_client()
    
    def _setup_client(self) -> None:
        """Setup the Twitter API client using tweepy."""
        try:
            # Setup API v2 client with OAuth 1.0a
            self.client = tweepy.Client(
                consumer_key=self.config.api_key,
                consumer_secret=self.config.api_secret,
                access_token=self.config.access_token,
                access_token_secret=self.config.access_token_secret,
                wait_on_rate_limit=True
            )
            
            self.logger.info("Twitter API client initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to setup Twitter API client: {str(e)}")
            raise
    
    async def __aenter__(self) -> "TwitterPublisher":
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        # tweepy client doesn't need explicit cleanup
        pass
    
    async def post_content(self, content: PostContent) -> bool:
        """
        Post content to Twitter.
        
        Args:
            content: Post content to publish
            
        Returns:
            True if post was successful, False otherwise
        """
        try:
            self.logger.info(f"Posting content to Twitter: {content.content[:50]}...")
            
            success = await self._send_tweet(content.content)
            
            if success:
                content.mark_as_posted()
                self.logger.info("Successfully posted to Twitter")
                return True
            else:
                content.mark_as_failed()
                self.logger.error("Failed to post to Twitter")
                return False
                
        except Exception as e:
            self.logger.error(f"Error posting to Twitter: {str(e)}")
            content.mark_as_failed()
            return False
    
    async def _send_tweet(self, tweet_text: str) -> bool:
        """
        Send a tweet using Twitter API v2 with tweepy.
        
        Args:
            tweet_text: Text content of the tweet
            
        Returns:
            True if tweet was sent successfully, False otherwise
        """
        if not self.client:
            raise RuntimeError("Twitter client not initialized.")
        
        try:
            self.logger.debug(f"Posting tweet: {tweet_text}")
            
            # Use tweepy's create_tweet method
            response = self.client.create_tweet(text=tweet_text)
            
            if response.data:
                tweet_id = response.data["id"]
                self.logger.info(f"Tweet posted successfully with ID: {tweet_id}")
                return True
            else:
                self.logger.error("Failed to post tweet: No response data")
                return False
                
        except tweepy.TooManyRequests as e:
            self.logger.error(f"Twitter rate limit exceeded: {str(e)}")
            return False
        except tweepy.Forbidden as e:
            self.logger.error(f"Twitter API forbidden error: {str(e)}")
            return False
        except tweepy.Unauthorized as e:
            self.logger.error(f"Twitter API unauthorized error: {str(e)}")
            return False
        except tweepy.BadRequest as e:
            self.logger.error(f"Twitter API bad request: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Failed to send tweet: {str(e)}")
            return False
    
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
                self.logger.info(f"Twitter API connection test successful. Username: {user.data.username}")
                return True
            else:
                self.logger.error("Twitter API connection test failed: No user data")
                return False
                
        except Exception as e:
            self.logger.error(f"Twitter API connection test failed: {str(e)}")
            return False
    
    def validate_content(self, content: PostContent) -> bool:
        """
        Validate content meets Twitter requirements.
        
        Args:
            content: Content to validate
            
        Returns:
            True if content is valid for Twitter, False otherwise
        """
        # Check character limit (280 for Twitter, but our system uses 20-220)
        if not (20 <= len(content.content) <= 220):
            self.logger.warning(f"Content length {len(content.content)} not in range 20-220")
            return False
        
        # Check hashtag count (our system requires exactly 2)
        if len(content.hashtags) != 2:
            self.logger.warning(f"Expected 2 hashtags, got {len(content.hashtags)}")
            return False
        
        return True 