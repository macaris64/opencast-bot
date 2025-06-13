"""
Command Line Interface for OpenCast Bot.

This module provides CLI commands for managing categories, generating content,
and posting to social media platforms.
"""

import asyncio
import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from bot.config import Config
from bot.db.json_orm import JSONCategoryManager
from bot.generator import ContentGenerator
from bot.models.category import Category
from bot.models.topic import PostContent, PostStatus
from bot.utils.exceptions import (
    OpenCastBotError,
    ConfigurationError,
    ResourceNotFoundError,
    ContentGenerationError,
    PublishingError
)
from bot.utils.logging import get_logger, LoggerMixin

# Initialize CLI app and logger
app = typer.Typer(help="OpenCast Bot - Social Media Content Generator")
console = Console()
logger = get_logger(__name__)


class CLIHandler(LoggerMixin):
    """CLI command handler with logging and error handling."""
    
    def __init__(self):
        """Initialize CLI handler."""
        super().__init__()
        self.logger.info("CLI handler initialized")
    
    def handle_error(self, error: Exception, context: str = "") -> None:
        """Handle CLI errors with proper logging and user feedback."""
        if isinstance(error, ResourceNotFoundError):
            console.print(f"❌ {error.message}", style="red")
            self.logger.error("Resource not found", extra={
                "error": str(error),
                "context": context
            })
        elif isinstance(error, ConfigurationError):
            console.print(f"❌ Configuration error: {error.message}", style="red")
            self.logger.error("Configuration error", extra={
                "error": str(error),
                "context": context
            })
        elif isinstance(error, ContentGenerationError):
            console.print(f"❌ Content generation failed: {error.message}", style="red")
            self.logger.error("Content generation error", extra={
                "error": str(error),
                "context": context
            })
        elif isinstance(error, PublishingError):
            console.print(f"❌ Publishing failed: {error.message}", style="red")
            self.logger.error("Publishing error", extra={
                "error": str(error),
                "context": context
            })
        elif isinstance(error, OpenCastBotError):
            console.print(f"❌ Error: {error.message}", style="red")
            self.logger.error("OpenCast bot error", extra={
                "error": str(error),
                "context": context
            })
        else:
            console.print(f"❌ Unexpected error: {str(error)}", style="red")
            self.logger.error("Unexpected error", extra={
                "error": str(error),
                "context": context,
                "error_type": type(error).__name__
            })


# Global CLI handler instance
cli_handler = CLIHandler()


@app.command()
def generate(
    category_id: str = typer.Argument(..., help="Category identifier"),
    topic: str = typer.Argument(..., help="Topic to generate content for")
) -> None:
    """Generate new content for a topic in a category."""
    
    async def _generate():
        try:
            cli_handler.logger.info("Starting content generation", extra={
                "category_id": category_id,
                "topic": topic
            })
            
            config = Config()
            manager = JSONCategoryManager(config.categories_directory)
            generator = ContentGenerator(config)
            
            # Load category
            try:
                category = manager.load_category(category_id)
            except FileNotFoundError:
                raise ResourceNotFoundError(f"Category '{category_id}' not found")
            
            # Check if content already exists
            if category.has_content_for_topic(topic):
                console.print(f"⚠️  Content already exists for topic '{topic}' in category '{category_id}'")
                if not typer.confirm("Do you want to generate new content anyway?"):
                    console.print("Operation cancelled.")
                    return
            
            # Generate new content
            console.print(f"🔄 Generating content for '{topic}'...")
            entry = await generator.generate_content(category, topic)
            
            if not entry:
                console.print("Content already exists for this topic")
                return
            
            # Add entry to category and save
            category.add_entry(topic, entry)
            manager.save_category(category)
            
            console.print("✅ Content generated successfully!")
            console.print(f"📝 Generated: {entry.content}")
            
            cli_handler.logger.info("Content generation completed successfully", extra={
                "category_id": category_id,
                "topic": topic,
                "content_length": len(entry.content)
            })
            
        except Exception as e:
            cli_handler.handle_error(e, f"generate command for {category_id}/{topic}")
            raise typer.Exit(1)
    
    # Run async function
    asyncio.run(_generate())


@app.command()
def list_categories() -> None:
    """List all available categories."""
    try:
        cli_handler.logger.info("Listing categories")
        
        config = Config()
        manager = JSONCategoryManager(config.categories_directory)
        categories = manager.list_categories()
        
        if not categories:
            console.print("No categories found")
            return
        
        console.print("Available categories:")
        for category_id in categories:
            try:
                category = manager.load_category(category_id)
                console.print(f"  • {category_id} - {category.name}")
            except Exception:
                console.print(f"  • {category_id}")
                
        cli_handler.logger.info("Categories listed successfully", extra={
            "category_count": len(categories)
        })
        
    except Exception as e:
        cli_handler.handle_error(e, "list-categories command")
        raise typer.Exit(1)


@app.command()
def show_category(
    category_id: str = typer.Argument(..., help="Category identifier to display")
) -> None:
    """Show details of a specific category."""
    try:
        cli_handler.logger.info("Showing category details", extra={
            "category_id": category_id
        })
        
        config = Config()
        manager = JSONCategoryManager(config.categories_directory)
        
        try:
            category = manager.load_category(category_id)
        except FileNotFoundError:
            raise ResourceNotFoundError(f"Category '{category_id}' not found")
        
        console.print(f"Category: {category.name}")
        console.print(f"ID: {category.category_id}")
        console.print(f"Description: {category.description}")
        console.print(f"Language: {category.language}")
        console.print(f"Topics: {len(category.topics)}")
        
        if category.topics:
            console.print("\nTopics:")
            for topic_data in category.topics:
                entry_count = len(topic_data.entries)
                console.print(f"  • {topic_data.topic} ({entry_count} entries)")
        
        cli_handler.logger.info("Category details shown successfully", extra={
            "category_id": category_id,
            "topic_count": len(category.topics)
        })
                
    except Exception as e:
        cli_handler.handle_error(e, f"show-category command for {category_id}")
        raise typer.Exit(1)


@app.command()
def validate_config() -> None:
    """Validate the current configuration."""
    try:
        cli_handler.logger.info("Validating configuration")
        
        config = Config()
        
        # Check OpenAI configuration
        if config.openai_api_key and config.openai_api_key != "sk-placeholder-for-development":
            console.print("✅ OpenAI API key configured")
        else:
            console.print("⚠️  Using placeholder OpenAI API key")
        
        # Check platform configurations
        platforms = config.get_enabled_platforms()
        
        if "twitter" in platforms:
            console.print("✅ Twitter configuration valid")
        else:
            console.print("⚠️  Twitter configuration incomplete or missing")
        
        if "telegram" in platforms:
            console.print("✅ Telegram configuration valid")
        else:
            console.print("⚠️  Telegram configuration incomplete or missing")
        
        console.print("✅ Configuration is valid")
        
        if platforms:
            console.print(f"\nEnabled platforms: {', '.join(platforms)}")
        else:
            console.print("\nNo platforms configured for posting")
        
        cli_handler.logger.info("Configuration validation completed", extra={
            "enabled_platforms": platforms
        })
            
    except Exception as e:
        cli_handler.handle_error(e, "validate-config command")
        raise typer.Exit(1)


@app.command()
def post(
    category_id: str = typer.Argument(..., help="Category identifier"),
    topic: str = typer.Argument(..., help="Topic to generate and post content for")
) -> None:
    """Generate new content and post it to social media platforms."""
    
    async def _post():
        try:
            cli_handler.logger.info("Starting post command", extra={
                "category_id": category_id,
                "topic": topic
            })
            
            config = Config()
            manager = JSONCategoryManager(config.categories_directory)
            generator = ContentGenerator(config)
            
            # Load category
            try:
                category = manager.load_category(category_id)
            except FileNotFoundError:
                raise ResourceNotFoundError(f"Category '{category_id}' not found")
            
            # Generate new content
            console.print(f"🔄 Generating content for '{topic}'...")
            entry = await generator.generate_content(category, topic)
            
            if not entry:
                raise ContentGenerationError(f"Failed to generate content for topic '{topic}'")
            
            # Add entry to category and save
            category.add_entry(topic, entry)
            manager.save_category(category)
            console.print(f"📝 Generated: {entry.content}")
            
            if config.dry_run:
                console.print(f"🔍 DRY RUN - Would post: {entry.content}")
                return
            
            # Post to enabled platforms
            platforms = config.get_enabled_platforms()
            success_count = 0
            
            if "twitter" in platforms:
                try:
                    from bot.publisher.twitter import TwitterPublisher, TwitterConfig
                    twitter_config = TwitterConfig(
                        api_key=config.twitter_api_key,
                        api_secret=config.twitter_api_secret,
                        access_token=config.twitter_access_token,
                        access_token_secret=config.twitter_access_token_secret,
                        bearer_token=config.twitter_bearer_token
                    )
                    
                    # Create Twitter-specific PostContent
                    twitter_post_content = PostContent(
                        content=entry.content,
                        platform="x",
                        category_id=category_id,
                        topic=topic,
                        hashtags=entry.metadata.tags,
                        status=PostStatus.PENDING
                    )
                    
                    async with TwitterPublisher(twitter_config) as twitter:
                        if await twitter.post_content(twitter_post_content):
                            success_count += 1
                            console.print("✅ Posted to Twitter")
                        else:
                            console.print("❌ Failed to post to Twitter")
                except Exception as e:
                    cli_handler.logger.error("Twitter posting failed", extra={
                        "error": str(e),
                        "category_id": category_id,
                        "topic": topic
                    })
                    console.print("❌ Failed to post to Twitter")
            
            if "telegram" in platforms:
                try:
                    from bot.publisher.telegram import TelegramPublisher, TelegramConfig
                    telegram_config = TelegramConfig(
                        bot_token=config.telegram_bot_token,
                        chat_id=config.telegram_chat_id,
                        parse_mode=config.telegram_parse_mode
                    )
                    
                    # Create Telegram-specific PostContent
                    telegram_post_content = PostContent(
                        content=entry.content,
                        platform="telegram",
                        category_id=category_id,
                        topic=topic,
                        hashtags=entry.metadata.tags,
                        status=PostStatus.PENDING
                    )
                    
                    async with TelegramPublisher(telegram_config) as telegram:
                        if await telegram.post_content(telegram_post_content):
                            success_count += 1
                            console.print("✅ Posted to Telegram")
                        else:
                            console.print("❌ Failed to post to Telegram")
                except Exception as e:
                    cli_handler.logger.error("Telegram posting failed", extra={
                        "error": str(e),
                        "category_id": category_id,
                        "topic": topic
                    })
                    console.print("❌ Failed to post to Telegram")
            
            if success_count > 0:
                console.print("✅ Posted successfully to at least one platform")
                cli_handler.logger.info("Post command completed successfully", extra={
                    "category_id": category_id,
                    "topic": topic,
                    "success_count": success_count,
                    "total_platforms": len(platforms)
                })
            else:
                raise PublishingError("Failed to post to any platform")
                
        except Exception as e:
            cli_handler.handle_error(e, f"post command for {category_id}/{topic}")
            raise typer.Exit(1)
    
    # Run async function
    asyncio.run(_post())


@app.command()
def list_topics(
    category_id: str = typer.Argument(..., help="Category identifier")
) -> None:
    """List all topics in a category."""
    try:
        cli_handler.logger.info("Listing topics", extra={
            "category_id": category_id
        })
        
        config = Config()
        manager = JSONCategoryManager(config.categories_directory)
        
        try:
            category = manager.load_category(category_id)
        except FileNotFoundError:
            raise ResourceNotFoundError(f"Category '{category_id}' not found")
        
        if not category.topics:
            console.print(f"No topics found in category '{category_id}'")
            return
        
        console.print(f"Topics in '{category.name}':")
        for topic_data in category.topics:
            entry_count = len(topic_data.entries)
            console.print(f"  • {topic_data.topic} ({entry_count} entries)")
        
        cli_handler.logger.info("Topics listed successfully", extra={
            "category_id": category_id,
            "topic_count": len(category.topics)
        })
            
    except Exception as e:
        cli_handler.handle_error(e, f"list-topics command for {category_id}")
        raise typer.Exit(1)


@app.command()
def version() -> None:
    """Show version information."""
    try:
        from bot import __version__
        console.print(f"OpenCast Bot version {__version__}")
        cli_handler.logger.info("Version command executed", extra={
            "version": __version__
        })
    except Exception as e:
        cli_handler.handle_error(e, "version command")
        raise typer.Exit(1)


@app.command()
def test_twitter() -> None:
    """Test Twitter API connection."""
    try:
        cli_handler.logger.info("Testing Twitter connection")
        
        config = Config()
        
        if not config.validate_twitter_config():
            raise ConfigurationError("Twitter configuration is invalid")
        
        from bot.publisher.twitter import TwitterPublisher, TwitterConfig
        twitter_config = TwitterConfig(
            api_key=config.twitter_api_key,
            api_secret=config.twitter_api_secret,
            access_token=config.twitter_access_token,
            access_token_secret=config.twitter_access_token_secret,
            bearer_token=config.twitter_bearer_token
        )
        
        publisher = TwitterPublisher(twitter_config)
        
        if publisher.test_connection():
            console.print("✅ Twitter API connection successful")
            cli_handler.logger.info("Twitter connection test successful")
        else:
            raise PublishingError("Twitter API connection failed")
            
    except Exception as e:
        cli_handler.handle_error(e, "test-twitter command")
        raise typer.Exit(1)


if __name__ == "__main__":
    app() 