"""
Command-line interface for OpenCast Bot.

This module provides the CLI interface using Typer for interacting
with the bot functionality.
"""

import asyncio
import logging
from typing import List, Optional

import typer

from bot.config import Config
from bot.db.json_orm import JSONCategoryManager
from bot.generator import ContentGenerator
from bot.publisher.twitter import TwitterPublisher
from bot.publisher.telegram import TelegramPublisher
from bot.models.topic import PostContent, PostStatus

app = typer.Typer(
    name="opencast-bot",
    help="OpenCast Bot - Content generation and social media posting automation",
    add_completion=False
)


@app.command()
def generate(
    category_id: str = typer.Argument(..., help="Category identifier"),
    topic: str = typer.Argument(..., help="Topic to generate content for")
) -> None:
    """Generate content for a category and topic (without posting)."""
    import asyncio
    
    # Show warning and ask for confirmation
    typer.echo("⚠️  WARNING: This command will only GENERATE content.")
    typer.echo("📝 Content will be saved to JSON but NOT posted to any platform.")
    typer.echo("🚀 Use 'post' command to both generate AND post content.")
    typer.echo()
    
    if not typer.confirm("Do you want to continue with content generation only?"):
        typer.echo("❌ Operation cancelled")
        raise typer.Exit(0)
    
    async def _generate():
        try:
            config = Config()
            manager = JSONCategoryManager(config.data_directory)
            generator = ContentGenerator(config)
            
            # Load category
            category = manager.load_category(category_id)
            
            # Generate content
            entry = await generator.generate_content(category, topic)
            
            if entry:
                # Add entry to category
                category.add_entry(topic, entry)
                manager.save_category(category)
                typer.echo("✅ Content generated successfully")
                
                if config.dry_run:
                    typer.echo(f"🔍 DRY RUN - Generated content: {entry.content}")
                else:
                    typer.echo(f"📝 Generated: {entry.content}")
            else:
                typer.echo("ℹ️  Content already exists for this topic")
                
        except FileNotFoundError:
            typer.echo(f"❌ Category '{category_id}' not found")
            raise typer.Exit(1)
        except Exception as e:
            typer.echo(f"❌ Error: {str(e)}")
            raise typer.Exit(1)
    
    # Run async function
    asyncio.run(_generate())


@app.command()
def list_categories() -> None:
    """List all available categories."""
    try:
        config = Config()
        manager = JSONCategoryManager(config.data_directory)
        categories = manager.list_categories()
        
        if not categories:
            typer.echo("No categories found")
            return
        
        typer.echo("Available categories:")
        for category_id in categories:
            try:
                category = manager.load_category(category_id)
                typer.echo(f"  • {category_id} - {category.name}")
            except Exception:
                typer.echo(f"  • {category_id}")
    except Exception as e:
        typer.echo(f"❌ Error: {str(e)}")
        raise typer.Exit(1)


@app.command()
def show_category(
    category_id: str = typer.Argument(..., help="Category identifier to display")
) -> None:
    """Show details of a specific category."""
    try:
        config = Config()
        manager = JSONCategoryManager(config.data_directory)
        category = manager.load_category(category_id)
        
        typer.echo(f"Category: {category.name}")
        typer.echo(f"ID: {category.category_id}")
        typer.echo(f"Description: {category.description}")
        typer.echo(f"Language: {category.language}")
        typer.echo(f"Topics: {len(category.topics)}")
        
        if category.topics:
            typer.echo("\nTopics:")
            for topic_data in category.topics:
                entry_count = len(topic_data.entries)
                typer.echo(f"  • {topic_data.topic} ({entry_count} entries)")
                
    except Exception as e:
        if "not found" in str(e).lower():
            typer.echo(f"❌ Category '{category_id}' not found")
            raise typer.Exit(1)
        else:
            typer.echo(f"❌ Error: {str(e)}")
            raise typer.Exit(1)


@app.command()
def validate_config() -> None:
    """Validate the current configuration."""
    try:
        config = Config()
        
        # Check OpenAI configuration
        if config.openai_api_key and config.openai_api_key != "sk-placeholder-for-development":
            typer.echo("✅ OpenAI API key configured")
        else:
            typer.echo("⚠️  Using placeholder OpenAI API key")
        
        # Check platform configurations
        platforms = config.get_enabled_platforms()
        
        if "twitter" in platforms:
            typer.echo("✅ Twitter configuration valid")
        else:
            typer.echo("⚠️  Twitter configuration incomplete or missing")
        
        if "telegram" in platforms:
            typer.echo("✅ Telegram configuration valid")
        else:
            typer.echo("⚠️  Telegram configuration incomplete or missing")
        
        typer.echo("✅ Configuration is valid")
        
        if platforms:
            typer.echo(f"\nEnabled platforms: {', '.join(platforms)}")
        else:
            typer.echo("\nNo platforms configured for posting")
            
    except Exception as e:
        typer.echo(f"❌ Configuration error: {str(e)}")
        raise typer.Exit(1)


@app.command()
def post(
    category_id: str = typer.Argument(..., help="Category identifier"),
    topic: str = typer.Argument(..., help="Topic to generate and post content for")
) -> None:
    """Generate new content and post it to social media platforms."""
    
    async def _post():
        try:
            config = Config()
            manager = JSONCategoryManager(config.data_directory)
            generator = ContentGenerator(config)
            
            # Load category
            category = manager.load_category(category_id)
            
            # Generate new content
            typer.echo(f"🔄 Generating content for '{topic}'...")
            entry = await generator.generate_content(category, topic)
            
            if not entry:
                typer.echo(f"❌ Failed to generate content for topic '{topic}'")
                raise typer.Exit(1)
            
            # Add entry to category and save
            category.add_entry(topic, entry)
            manager.save_category(category)
            typer.echo(f"📝 Generated: {entry.content}")
            
            if config.dry_run:
                typer.echo(f"🔍 DRY RUN - Would post: {entry.content}")
                return
            
            # Post to enabled platforms
            platforms = config.get_enabled_platforms()
            success_count = 0
            
            if "twitter" in platforms:
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
                        typer.echo("✅ Posted to Twitter")
                    else:
                        typer.echo("❌ Failed to post to Twitter")
            
            if "telegram" in platforms:
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
                        typer.echo("✅ Posted to Telegram")
                    else:
                        typer.echo("❌ Failed to post to Telegram")
            
            if success_count > 0:
                typer.echo("✅ Posted successfully to at least one platform")
            else:
                typer.echo("❌ Failed to post to any platform")
                raise typer.Exit(1)
                
        except Exception as e:
            if "not found" in str(e).lower():
                typer.echo(f"❌ Category '{category_id}' not found")
                raise typer.Exit(1)
            else:
                typer.echo(f"❌ Error: {str(e)}")
                raise typer.Exit(1)
    
    # Run async function
    asyncio.run(_post())


@app.command()
def list_topics(
    category_id: str = typer.Argument(..., help="Category identifier")
) -> None:
    """List all topics in a category."""
    try:
        config = Config()
        manager = JSONCategoryManager(config.data_directory)
        category = manager.load_category(category_id)
        
        if not category.topics:
            typer.echo(f"No topics found in category '{category_id}'")
            return
        
        typer.echo(f"Topics in '{category.name}':")
        for topic_data in category.topics:
            entry_count = len(topic_data.entries)
            typer.echo(f"  • {topic_data.topic} ({entry_count} entries)")
            
    except Exception as e:
        if "not found" in str(e).lower():
            typer.echo(f"❌ Category '{category_id}' not found")
            raise typer.Exit(1)
        else:
            typer.echo(f"❌ Error: {str(e)}")
            raise typer.Exit(1)


@app.command()
def version() -> None:
    """Show version information."""
    from bot import __version__
    typer.echo(f"OpenCast Bot version {__version__}")


@app.command()
def test_twitter() -> None:
    """Test Twitter API connection."""
    try:
        config = Config()
        
        if not config.validate_twitter_config():
            typer.echo("❌ Twitter configuration is invalid")
            raise typer.Exit(1)
        
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
            typer.echo("✅ Twitter API connection successful")
        else:
            typer.echo("❌ Twitter API connection failed")
            raise typer.Exit(1)
            
    except Exception as e:
        typer.echo(f"❌ Error: {str(e)}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app() 