"""
Main module for OpenCast Bot.

This module contains the main application logic and workflow orchestration
for content generation and publishing.
"""

import asyncio
from typing import List, Optional

from bot.config import Config, get_config
from bot.db.json_orm import JsonORM
from bot.generator import ContentGenerator
from bot.models.category import Category
from bot.models.topic import PostContent, PlatformType
from bot.publisher.telegram import TelegramPublisher, TelegramConfig
from bot.publisher.twitter import TwitterPublisher, TwitterConfig
from bot.utils import (
    get_logger, LoggerMixin, log_execution_time,
    OpenCastBotError, ConfigurationError, ValidationError,
    PublishingError, APIError, NetworkError
)


class OpenCastBot(LoggerMixin):
    """Main bot class that orchestrates content generation and publishing."""
    
    def __init__(self, config: Config) -> None:
        """
        Initialize OpenCast Bot with configuration.
        
        Args:
            config: Application configuration
        """
        super().__init__()
        self.config = config
        
        try:
            # Initialize components
            self.orm = JsonORM(config.categories_directory)
            self.generator = ContentGenerator(config)
            
            self.logger.info(
                "OpenCastBot initialized successfully",
                categories_directory=config.categories_directory,
                dry_run=config.dry_run,
                enabled_platforms=config.get_enabled_platforms()
            )
            
        except Exception as e:
            init_error = ConfigurationError(
                "Failed to initialize OpenCast Bot",
                cause=e
            )
            self.logger.error("Bot initialization failed", error=init_error)
            raise init_error
    
    @log_execution_time
    async def run(
        self, 
        category_id: str, 
        topic: str, 
        platforms: Optional[List[str]] = None
    ) -> bool:
        """
        Run the main bot workflow for a specific category and topic.
        
        Args:
            category_id: Category identifier
            topic: Topic to generate content for
            platforms: List of platforms to post to (default: all enabled)
            
        Returns:
            True if workflow completed successfully, False otherwise
        """
        try:
            self.logger.info(
                "Starting OpenCast Bot workflow",
                category_id=category_id,
                topic=topic,
                requested_platforms=platforms
            )
            
            # Load category
            category = self.orm.load_category(category_id)
            if not category:
                category_error = ValidationError(
                    f"Category '{category_id}' not found",
                    field_name="category_id",
                    field_value=category_id,
                    validation_rule="category must exist"
                )
                self.logger.error("Category not found", error=category_error)
                return False
            
            # Generate content if it doesn't exist
            entry = await self.generator.generate_content(category, topic)
            if not entry:
                self.logger.warning(
                    "No new content generated",
                    category_id=category_id,
                    topic=topic,
                    reason="content may already exist"
                )
                return False
            
            # Add entry to category and save
            category.add_entry(topic, entry)
            self.orm.save_category(category)
            
            self.logger.info(
                "Content generated and saved",
                category_id=category_id,
                topic=topic,
                content_length=len(entry.content),
                content_preview=entry.content[:50] + "..." if len(entry.content) > 50 else entry.content
            )
            
            # Determine platforms to post to
            if platforms is None:
                platforms = self.config.get_enabled_platforms()
            
            if not platforms:
                self.logger.warning(
                    "No platforms configured for posting",
                    category_id=category_id,
                    topic=topic
                )
                return True  # Content generated successfully, just not posted
            
            # Post to platforms
            success = await self._post_to_platforms(entry.content, category_id, topic, platforms)
            
            self.logger.info(
                "Bot workflow completed",
                category_id=category_id,
                topic=topic,
                success=success,
                platforms=platforms
            )
            return success
            
        except (ValidationError, ConfigurationError) as e:
            self.logger.error("Bot workflow validation error", error=e)
            return False
        except Exception as e:
            workflow_error = OpenCastBotError(
                "Unexpected error in bot workflow",
                context={
                    "category_id": category_id,
                    "topic": topic,
                    "platforms": platforms
                },
                cause=e
            )
            self.logger.error("Bot workflow failed", error=workflow_error)
            return False
    
    async def _post_to_platforms(
        self, 
        content: str, 
        category_id: str, 
        topic: str, 
        platforms: List[str]
    ) -> bool:
        """
        Post content to specified platforms.
        
        Args:
            content: Content text to post
            category_id: Category identifier
            topic: Topic name
            platforms: List of platform names
            
        Returns:
            True if all posts were successful, False otherwise
        """
        success = True
        
        for platform in platforms:
            try:
                self.logger.info(
                    "Attempting to post to platform",
                    platform=platform,
                    category_id=category_id,
                    topic=topic
                )
                
                if platform == "twitter" and self.config.validate_twitter_config():
                    platform_success = await self._post_to_twitter(content, category_id, topic)
                elif platform == "telegram" and self.config.validate_telegram_config():
                    platform_success = await self._post_to_telegram(content, category_id, topic)
                else:
                    self.logger.warning(
                        "Platform not configured or invalid",
                        platform=platform,
                        twitter_valid=self.config.validate_twitter_config(),
                        telegram_valid=self.config.validate_telegram_config()
                    )
                    platform_success = False
                
                success &= platform_success
                
                self.logger.info(
                    "Platform posting completed",
                    platform=platform,
                    success=platform_success
                )
                    
            except Exception as e:
                platform_error = PublishingError(
                    f"Error posting to {platform}",
                    platform=platform,
                    content_preview=content[:50] + "..." if len(content) > 50 else content,
                    cause=e
                )
                self.logger.error("Platform posting failed", error=platform_error)
                success = False
        
        return success
    
    def _extract_hashtags(self, content: str) -> List[str]:
        """Extract hashtags from content."""
        import re
        hashtags = re.findall(r'#\w+', content)
        return hashtags[:2] if len(hashtags) >= 2 else hashtags + ['#default'] * (2 - len(hashtags))
    
    async def _post_to_twitter(self, content: str, category_id: str, topic: str) -> bool:
        """Post content to Twitter."""
        if self.config.dry_run:
            self.logger.info(
                "DRY RUN: Twitter posting",
                content=content,
                platform="twitter"
            )
            return True
        
        try:
            # Create Twitter publisher and post
            twitter_config = TwitterConfig(
                api_key=self.config.twitter_api_key,
                api_secret=self.config.twitter_api_secret,
                access_token=self.config.twitter_access_token,
                access_token_secret=self.config.twitter_access_token_secret,
                bearer_token=self.config.twitter_bearer_token
            )
            
            # Extract hashtags from content
            hashtags = self._extract_hashtags(content)
            
            # Create PostContent object
            post_content = PostContent(
                content=content,
                category_id=category_id,
                topic=topic,
                hashtags=hashtags,
                platform=PlatformType.X
            )
            
            async with TwitterPublisher(twitter_config) as publisher:
                success = await publisher.post_content(post_content)
                
            self.logger.info(
                "Twitter posting completed",
                success=success,
                platform="twitter"
            )
            return success
            
        except Exception as e:
            twitter_error = PublishingError(
                "Twitter posting failed",
                platform="twitter",
                content_preview=content[:50] + "..." if len(content) > 50 else content,
                cause=e
            )
            self.logger.error("Twitter posting error", error=twitter_error)
            return False
    
    async def _post_to_telegram(self, content: str, category_id: str, topic: str) -> bool:
        """Post content to Telegram."""
        if self.config.dry_run:
            self.logger.info(
                "DRY RUN: Telegram posting",
                content=content,
                platform="telegram"
            )
            return True
        
        try:
            # Create Telegram publisher and post
            telegram_config = TelegramConfig(
                bot_token=self.config.telegram_bot_token,
                chat_id=self.config.telegram_chat_id
            )
            
            # Extract hashtags from content
            hashtags = self._extract_hashtags(content)
            
            # Create PostContent object
            post_content = PostContent(
                content=content,
                category_id=category_id,
                topic=topic,
                hashtags=hashtags,
                platform=PlatformType.TELEGRAM
            )
            
            async with TelegramPublisher(telegram_config) as publisher:
                success = await publisher.post_content(post_content)
                
            self.logger.info(
                "Telegram posting completed",
                success=success,
                platform="telegram"
            )
            return success
            
        except Exception as e:
            telegram_error = PublishingError(
                "Telegram posting failed",
                platform="telegram",
                content_preview=content[:50] + "..." if len(content) > 50 else content,
                cause=e
            )
            self.logger.error("Telegram posting error", error=telegram_error)
            return False


async def main() -> None:
    """Main entry point for the application."""
    try:
        # Setup logging first
        from bot.utils import setup_logging
        setup_logging(level="INFO")
        
        logger = get_logger(__name__)
        logger.info("Starting OpenCast Bot application")
        
        bot = OpenCastBot(get_config())
        
        # Example usage - this would be replaced by CLI integration
        success = await bot.run(
            category_id="dev-one-liners",
            topic="Code comments",
            platforms=["twitter", "telegram"]
        )
        
        if success:
            logger.info("Bot execution completed successfully")
        else:
            logger.error("Bot execution failed")
            
    except Exception as e:
        # Fallback logging if structured logging fails
        import logging
        logging.basicConfig(level=logging.ERROR)
        logging.error(f"Application startup failed: {e}")


if __name__ == "__main__":
    asyncio.run(main()) 