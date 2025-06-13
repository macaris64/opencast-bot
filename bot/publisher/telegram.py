"""
Telegram publisher module for OpenCast Bot.

This module handles posting content to Telegram channels/chats.
"""

import logging
from typing import Optional

import httpx
from pydantic import BaseModel

from bot.models.topic import PostContent, PostStatus

logger = logging.getLogger(__name__)


class TelegramConfig(BaseModel):
    """Configuration for Telegram Bot API integration."""
    
    bot_token: str
    chat_id: str  # Can be channel username (@channel) or numeric chat ID
    parse_mode: str = "HTML"  # HTML or Markdown


class TelegramPublisher:
    """Publisher class for posting content to Telegram."""
    
    def __init__(self, config: TelegramConfig) -> None:
        """
        Initialize Telegram publisher with bot credentials.
        
        Args:
            config: Telegram bot configuration
        """
        self.config = config
        self.client: Optional[httpx.AsyncClient] = None
        self.base_url = f"https://api.telegram.org/bot{config.bot_token}"
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    async def __aenter__(self) -> "TelegramPublisher":
        """Async context manager entry."""
        self.client = httpx.AsyncClient()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self.client:
            await self.client.aclose()
    
    async def post_content(self, content: PostContent) -> bool:
        """
        Post content to Telegram.
        
        Args:
            content: Post content to publish
            
        Returns:
            True if post was successful, False otherwise
        """
        try:
            self.logger.info(f"Posting content to Telegram: {content.content[:50]}...")
            
            success = await self._send_message(content.content)
            
            if success:
                content.mark_as_posted()
                self.logger.info("Successfully posted to Telegram")
                return True
            else:
                content.mark_as_failed()
                self.logger.error("Failed to post to Telegram")
                return False
                
        except Exception as e:
            self.logger.error(f"Error posting to Telegram: {str(e)}")
            content.mark_as_failed()
            return False
    
    async def _send_message(self, message_text: str) -> bool:
        """
        Send a message using Telegram Bot API.
        
        Args:
            message_text: Text content of the message
            
        Returns:
            True if message was sent successfully, False otherwise
        """
        if not self.client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.config.chat_id,
                "text": message_text,
                "parse_mode": self.config.parse_mode,
            }
            
            self.logger.debug(f"Posting Telegram message: {message_text}")
            
            response = await self.client.post(url, json=payload)
            
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get("ok"):
                    self.logger.info("Telegram message sent successfully")
                    return True
                else:
                    self.logger.error(f"Telegram API error: {response_data.get('description', 'Unknown error')}")
                    return False
            else:
                self.logger.error(f"Failed to send Telegram message. Status: {response.status_code}, Response: {response.text}")
                return False
            
        except Exception as e:
            self.logger.error(f"Failed to send Telegram message: {str(e)}")
            return False
    
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
            return await self._send_message(alert_text)
        except Exception as e:
            self.logger.error(f"Failed to send error alert: {str(e)}")
            return False
    
    def validate_content(self, content: PostContent) -> bool:
        """
        Validate content meets Telegram requirements.
        
        Args:
            content: Content to validate
            
        Returns:
            True if content is valid for Telegram, False otherwise
        """
        # Check character limit (Telegram supports up to 4096 characters, but PDR specifies 180-200)
        if not (180 <= len(content.content) <= 200):
            self.logger.warning(f"Content length {len(content.content)} not in range 180-200")
            return False
        
        # Check hashtag count (PDR specifies exactly 2)
        if len(content.hashtags) != 2:
            self.logger.warning(f"Expected 2 hashtags, got {len(content.hashtags)}")
            return False
        
        return True 