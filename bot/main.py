"""
Main module for OpenCast Bot.

This module contains the main application logic and workflow orchestration
for content generation and publishing.
"""

import asyncio
import logging
from typing import List, Optional

from bot.config import Config, config
from bot.db.json_orm import JsonORM
from bot.generator import ContentGenerator
from bot.models.category import Category
from bot.models.topic import PostContent, PlatformType
from bot.publisher.telegram import TelegramPublisher, TelegramConfig
from bot.publisher.twitter import TwitterPublisher, TwitterConfig


class OpenCastBot:
    """Main bot class that orchestrates content generation and publishing."""
    
    def __init__(self, config: Config) -> None:
        """
        Initialize OpenCast Bot with configuration.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Initialize components
        self.orm = JsonORM(config.data_directory)
        self.generator = ContentGenerator(config)
        
        # Setup logging
        config.setup_logging()
    
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
            self.logger.info(f"Starting OpenCast Bot for category '{category_id}', topic '{topic}'")
            
            # Load category
            category = self.orm.load_category(category_id)
            if not category:
                self.logger.error(f"Category '{category_id}' not found")
                return False
            
            # Generate content if it doesn't exist
            entry = await self.generator.generate_content(category, topic)
            if not entry:
                self.logger.warning(f"No new content generated for topic '{topic}'")
                return False
            
            # Add entry to category and save
            category.add_entry(topic, entry)
            self.orm.save_category(category)
            
            # Determine platforms to post to
            if platforms is None:
                platforms = self.config.get_enabled_platforms()
            
            if not platforms:
                self.logger.warning("No platforms configured for posting")
                return True  # Content generated successfully, just not posted
            
            # Post to platforms
            success = await self._post_to_platforms(entry.content, category_id, topic, platforms)
            
            self.logger.info(f"Bot workflow completed {'successfully' if success else 'with errors'}")
            return success
            
        except Exception as e:
            self.logger.error(f"Error in bot workflow: {str(e)}")
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
                if platform == "twitter" and self.config.validate_twitter_config():
                    success &= await self._post_to_twitter(content, category_id, topic)
                elif platform == "telegram" and self.config.validate_telegram_config():
                    success &= await self._post_to_telegram(content, category_id, topic)
                else:
                    self.logger.warning(f"Platform '{platform}' not configured or invalid")
                    
            except Exception as e:
                self.logger.error(f"Error posting to {platform}: {str(e)}")
                success = False
        
        return success
    
    async def _post_to_twitter(self, content: str, category_id: str, topic: str) -> bool:
        """Post content to Twitter."""
        if self.config.dry_run:
            self.logger.info(f"DRY RUN: Would post to Twitter: {content}")
            return True
        
        try:
            # TODO: Implement actual Twitter posting
            self.logger.info("Twitter posting placeholder - implementation needed")
            return True
        except Exception as e:
            self.logger.error(f"Twitter posting failed: {str(e)}")
            return False
    
    async def _post_to_telegram(self, content: str, category_id: str, topic: str) -> bool:
        """Post content to Telegram."""
        if self.config.dry_run:
            self.logger.info(f"DRY RUN: Would post to Telegram: {content}")
            return True
        
        try:
            # TODO: Implement actual Telegram posting
            self.logger.info("Telegram posting placeholder - implementation needed")
            return True
        except Exception as e:
            self.logger.error(f"Telegram posting failed: {str(e)}")
            return False


async def main() -> None:
    """Main entry point for the application."""
    bot = OpenCastBot(config)
    
    # Example usage - this would be replaced by CLI integration
    success = await bot.run(
        category_id="dev-one-liners",
        topic="Code comments",
        platforms=["twitter", "telegram"]
    )
    
    if success:
        logging.info("Bot execution completed successfully")
    else:
        logging.error("Bot execution failed")


if __name__ == "__main__":
    asyncio.run(main()) 