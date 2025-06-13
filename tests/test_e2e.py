"""End-to-End tests for OpenCast Bot complete workflows."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
import tempfile
import json
import os
from datetime import datetime, timedelta

from bot.config import Config
from bot.generator import ContentGenerator
from bot.publisher.twitter import TwitterPublisher, TwitterConfig
from bot.publisher.telegram import TelegramPublisher, TelegramConfig
from bot.db.json_orm import JSONCategoryManager
from bot.models.topic import PostContent, PostStatus
from bot.models.category import Category, CategoryEntry, CategoryMetadata
from bot.utils.exceptions import *


class TestE2EWorkflows:
    """End-to-End workflow tests."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def mock_env_config(self):
        """Mock environment configuration."""
        return {
            'OPENAI_API_KEY': 'test-openai-key',
            'TWITTER_API_KEY': 'test-twitter-key',
            'TWITTER_API_SECRET': 'test-twitter-secret',
            'TWITTER_ACCESS_TOKEN': 'test-twitter-token',
            'TWITTER_ACCESS_TOKEN_SECRET': 'test-twitter-token-secret',
            'TELEGRAM_BOT_TOKEN': 'test-telegram-token',
            'TELEGRAM_CHAT_ID': 'test-chat-id',
            'DRY_RUN': 'true'
        }
    
    @pytest.fixture
    def sample_categories(self):
        """Create sample categories for testing."""
        return [
            Category(
                category_id="ai-tips",
                name="AI Tips",
                description="Tips about artificial intelligence",
                prompt_template="Create an AI tip about {topic}. Make it informative and engaging."
            ),
            Category(
                category_id="dev-tips",
                name="Development Tips",
                description="Software development tips",
                prompt_template="Create a development tip about {topic}. Make it practical and useful."
            )
        ]
    
    @pytest.mark.asyncio
    async def test_complete_content_generation_workflow(self, temp_workspace, mock_env_config, sample_categories):
        """Test complete workflow from content generation to publishing."""
        
        with patch.dict(os.environ, mock_env_config):
            # Mock OpenAI responses for each category
            mock_responses = []
            contents = [
                "AI tip: Machine learning models need quality data! #AI #MachineLearning",
                "Dev tip: Python is great for rapid prototyping! #Python #Development"
            ]
            
            for content in contents:
                mock_response = Mock()
                mock_response.choices = [Mock()]
                mock_response.choices[0].message = Mock()
                mock_response.choices[0].message.content = content
                mock_responses.append(mock_response)
            
            # Mock publisher responses
            mock_twitter_response = Mock()
            mock_twitter_response.data = {"id": "123456789"}
            
            with patch('openai.AsyncOpenAI') as mock_openai, \
                 patch('bot.publisher.twitter.tweepy.Client') as mock_twitter_client:
                
                # Setup mocks
                mock_openai_client = AsyncMock()
                mock_openai_client.chat.completions.create.side_effect = mock_responses
                mock_openai.return_value = mock_openai_client
                
                mock_twitter_client.return_value.create_tweet.return_value = mock_twitter_response
                
                # Initialize components
                config = Config()
                generator = ContentGenerator(config)
                twitter_publisher = TwitterPublisher(TwitterConfig(
                    api_key=config.twitter_api_key,
                    api_secret=config.twitter_api_secret,
                    access_token=config.twitter_access_token,
                    access_token_secret=config.twitter_access_token_secret
                ))
                
                # Generate content for each category
                generated_entries = []
                topics = ["Machine Learning", "Python"]
                
                for i, category in enumerate(sample_categories):
                    topic = topics[i]
                    
                    entry = await generator.generate_content(
                        category=category,
                        topic=topic
                    )
                    
                    assert entry is not None
                    assert topic.lower() in entry.content.lower()
                    assert len(entry.metadata.tags) == 2
                    generated_entries.append((entry, category, topic))
                
                # Publish content
                for entry, category, topic in generated_entries:
                    # Create PostContent from CategoryEntry
                    post_content = PostContent(
                        content=entry.content,
                        topic=topic,
                        hashtags=entry.metadata.tags,
                        platform="x",
                        category_id=category.category_id
                    )
                    
                    result = await twitter_publisher.post_content(post_content)
                    assert result is True
                    assert post_content.status == PostStatus.POSTED
                
                # Verify all content was generated and published
                assert len(generated_entries) == 2
    
    @pytest.mark.asyncio
    async def test_multi_platform_publishing_workflow(self, temp_workspace, mock_env_config, sample_categories):
        """Test publishing same content to multiple platforms."""
        
        with patch.dict(os.environ, mock_env_config):
            # Mock responses
            mock_openai_response = Mock()
            mock_openai_response.choices = [Mock()]
            mock_openai_response.choices[0].message = Mock()
            mock_openai_response.choices[0].message.content = "Multi-platform content! #Multi #Platform"
            
            mock_twitter_response = Mock()
            mock_twitter_response.data = {"id": "123456789"}
            
            mock_telegram_response = Mock()
            mock_telegram_response.status_code = 200
            mock_telegram_response.json.return_value = {
                "ok": True,
                "result": {"message_id": 123}
            }
            
            with patch('openai.AsyncOpenAI') as mock_openai, \
                 patch('bot.publisher.twitter.tweepy.Client') as mock_twitter_client, \
                 patch('httpx.AsyncClient') as mock_telegram_client:
                
                # Setup mocks
                mock_openai_client = AsyncMock()
                mock_openai_client.chat.completions.create.return_value = mock_openai_response
                mock_openai.return_value = mock_openai_client
                
                mock_twitter_client.return_value.create_tweet.return_value = mock_twitter_response
                
                mock_telegram_instance = AsyncMock()
                mock_telegram_instance.post.return_value = mock_telegram_response
                mock_telegram_instance.aclose.return_value = None
                mock_telegram_client.return_value = mock_telegram_instance
                
                # Initialize components
                config = Config()
                generator = ContentGenerator(config)
                
                twitter_publisher = TwitterPublisher(TwitterConfig(
                    api_key=config.twitter_api_key,
                    api_secret=config.twitter_api_secret,
                    access_token=config.twitter_access_token,
                    access_token_secret=config.twitter_access_token_secret
                ))
                
                telegram_publisher = TelegramPublisher(TelegramConfig(
                    bot_token=config.telegram_bot_token,
                    chat_id=config.telegram_chat_id
                ))
                
                # Generate base content
                category = sample_categories[0]
                entry = await generator.generate_content(
                    category=category,
                    topic="Multi Platform"
                )
                
                # Create platform-specific copies
                twitter_content = PostContent(
                    content=entry.content,
                    topic="Multi Platform",
                    hashtags=entry.metadata.tags,
                    platform="x",
                    category_id=category.category_id
                )
                
                telegram_content = PostContent(
                    content=entry.content,
                    topic="Multi Platform",
                    hashtags=entry.metadata.tags,
                    platform="telegram",
                    category_id=category.category_id
                )
                
                # Publish to both platforms
                twitter_result = await twitter_publisher.post_content(twitter_content)
                
                async with telegram_publisher:
                    telegram_result = await telegram_publisher.post_content(telegram_content)
                
                # Verify both published successfully
                assert twitter_result is True
                assert telegram_result is True
                assert twitter_content.status == PostStatus.POSTED
                assert telegram_content.status == PostStatus.POSTED
    
    @pytest.mark.asyncio
    async def test_category_management_workflow(self, temp_workspace, sample_categories):
        """Test category management workflow."""
        
        # Create category manager
        categories_dir = temp_workspace / "categories"
        manager = JSONCategoryManager(str(categories_dir))
        
        # Store categories
        for category in sample_categories:
            manager.save_category(category)
        
        # Verify categories were stored
        category_ids = manager.list_categories()
        assert len(category_ids) == 2
        assert "ai-tips" in category_ids
        assert "dev-tips" in category_ids
        
        # Load and verify categories
        for category in sample_categories:
            loaded_category = manager.load_category(category.category_id)
            assert loaded_category.category_id == category.category_id
            assert loaded_category.name == category.name
            assert loaded_category.description == category.description
    
    @pytest.mark.asyncio
    async def test_content_generation_with_storage_workflow(self, temp_workspace, mock_env_config, sample_categories):
        """Test content generation with category storage."""
        
        with patch.dict(os.environ, mock_env_config):
            # Setup category manager
            categories_dir = temp_workspace / "categories"
            manager = JSONCategoryManager(str(categories_dir))
            
            # Store categories
            for category in sample_categories:
                manager.save_category(category)
            
            # Mock OpenAI response
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message = Mock()
            mock_response.choices[0].message.content = "Storage workflow test content! #Storage #Test"
            
            with patch('openai.AsyncOpenAI') as mock_openai:
                mock_client = AsyncMock()
                mock_client.chat.completions.create.return_value = mock_response
                mock_openai.return_value = mock_client
                
                # Initialize generator
                config = Config()
                generator = ContentGenerator(config)
                
                # Load category and generate content
                category = manager.load_category("ai-tips")
                entry = await generator.generate_content(
                    category=category,
                    topic="Storage Test"
                )
                
                # Verify content was generated
                assert entry is not None
                assert "storage" in entry.content.lower()
                assert len(entry.metadata.tags) == 2
                
                # Add entry to category and save
                category.add_entry("Storage Test", entry)
                manager.save_category(category)
                
                # Verify entry was saved
                reloaded_category = manager.load_category("ai-tips")
                assert reloaded_category.has_content_for_topic("Storage Test")


class TestE2EErrorScenarios:
    """End-to-end error scenario tests."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def mock_env_config(self):
        """Mock environment configuration."""
        return {
            'OPENAI_API_KEY': 'test-openai-key',
            'TWITTER_API_KEY': 'test-twitter-key',
            'TWITTER_API_SECRET': 'test-twitter-secret',
            'TWITTER_ACCESS_TOKEN': 'test-twitter-token',
            'TWITTER_ACCESS_TOKEN_SECRET': 'test-twitter-token-secret',
            'TELEGRAM_BOT_TOKEN': 'test-telegram-token',
            'TELEGRAM_CHAT_ID': 'test-chat-id',
            'DRY_RUN': 'true'
        }
    
    @pytest.fixture
    def sample_category(self):
        """Create sample category for testing."""
        return Category(
            category_id="test-category",
            name="Test Category",
            description="Test category for error scenarios",
            prompt_template="Create content about {topic}."
        )
    
    @pytest.mark.asyncio
    async def test_openai_api_failure_workflow(self, mock_env_config, sample_category):
        """Test workflow when OpenAI API fails."""
        
        with patch.dict(os.environ, mock_env_config):
            with patch('openai.AsyncOpenAI') as mock_openai:
                # Mock API failure
                mock_client = AsyncMock()
                mock_client.chat.completions.create.side_effect = Exception("API Error")
                mock_openai.return_value = mock_client
                
                # Initialize generator
                config = Config()
                generator = ContentGenerator(config)
                
                # Attempt content generation
                entry = await generator.generate_content(
                    category=sample_category,
                    topic="Test Topic"
                )
                
                # Should return None on failure
                assert entry is None
    
    @pytest.mark.asyncio
    async def test_all_publishers_failure_workflow(self, mock_env_config, sample_category):
        """Test workflow when all publishers fail."""
        
        with patch.dict(os.environ, mock_env_config):
            # Mock successful content generation
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message = Mock()
            mock_response.choices[0].message.content = "Test content for failure scenario! #Test #Failure"
            
            with patch('openai.AsyncOpenAI') as mock_openai, \
                 patch('bot.publisher.twitter.tweepy.Client') as mock_twitter, \
                 patch('httpx.AsyncClient') as mock_telegram:
                
                # Setup successful content generation
                mock_openai_client = AsyncMock()
                mock_openai_client.chat.completions.create.return_value = mock_response
                mock_openai.return_value = mock_openai_client
                
                # Setup failing publishers
                mock_twitter.return_value.create_tweet.side_effect = Exception("Twitter API Error")
                
                mock_telegram_instance = AsyncMock()
                mock_telegram_instance.post.side_effect = Exception("Telegram API Error")
                mock_telegram_instance.aclose.return_value = None
                mock_telegram.return_value = mock_telegram_instance
                
                # Initialize components
                config = Config()
                generator = ContentGenerator(config)
                
                twitter_publisher = TwitterPublisher(TwitterConfig(
                    api_key=config.twitter_api_key,
                    api_secret=config.twitter_api_secret,
                    access_token=config.twitter_access_token,
                    access_token_secret=config.twitter_access_token_secret
                ))
                
                telegram_publisher = TelegramPublisher(TelegramConfig(
                    bot_token=config.telegram_bot_token,
                    chat_id=config.telegram_chat_id
                ))
                
                # Generate content
                entry = await generator.generate_content(
                    category=sample_category,
                    topic="Failure Test"
                )
                
                assert entry is not None
                
                # Create post content
                post_content = PostContent(
                    content=entry.content,
                    topic="Failure Test",
                    hashtags=entry.metadata.tags,
                    platform="x",
                    category_id=sample_category.category_id
                )
                
                # Attempt publishing - should fail
                twitter_result = await twitter_publisher.post_content(post_content)
                assert twitter_result is False
                
                async with telegram_publisher:
                    telegram_result = await telegram_publisher.post_content(post_content)
                    assert telegram_result is False
    
    @pytest.mark.asyncio
    async def test_category_storage_failure_workflow(self, temp_workspace, sample_category):
        """Test workflow when category storage fails."""

        # Use invalid path to trigger error
        invalid_path = temp_workspace / "nonexistent" / "invalid"

        # This should raise an error when trying to create the manager
        with pytest.raises((FileNotFoundError, OSError)):
            manager = JSONCategoryManager(str(invalid_path))
            manager.save_category(sample_category) 