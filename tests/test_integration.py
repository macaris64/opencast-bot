"""Integration tests for OpenCast Bot components working together."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
import tempfile
import json
import os

from bot.config import Config
from bot.generator import ContentGenerator
from bot.publisher.twitter import TwitterPublisher, TwitterConfig
from bot.publisher.telegram import TelegramPublisher, TelegramConfig
from bot.db.json_orm import JsonORM, JSONCategoryManager
from bot.models.topic import PostContent, PostStatus
from bot.models.category import Category, CategoryEntry, CategoryMetadata
from bot.utils.exceptions import *


class TestConfigIntegration:
    """Test Config integration with other components."""
    
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
            'TELEGRAM_CHAT_ID': 'test-chat-id'
        }
    
    def test_config_with_publisher_initialization(self, mock_env_config):
        """Test Config properly initializes with publisher settings."""
        with patch.dict(os.environ, mock_env_config):
            config = Config()
            
            # Test Twitter config fields
            assert config.twitter_api_key == 'test-twitter-key'
            assert config.twitter_api_secret == 'test-twitter-secret'
            
            # Test Telegram config fields
            assert config.telegram_bot_token == 'test-telegram-token'
            assert config.telegram_chat_id == 'test-chat-id'
            
            # Test OpenAI config
            assert config.openai_api_key == 'test-openai-key'
    
    def test_config_validation_integration(self, mock_env_config):
        """Test config validation with environment variables."""
        with patch.dict(os.environ, mock_env_config, clear=True):
            config = Config()
            
            # Verify config loaded from mocked environment
            assert config.openai_api_key == "test-openai-key"
            assert config.twitter_api_key == "test-twitter-key"
            assert config.telegram_bot_token == "test-telegram-token"
            assert config.dry_run is False  # DRY_RUN not set, defaults to False


class TestGeneratorIntegration:
    """Test ContentGenerator integration with other components."""
    
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
            'TELEGRAM_CHAT_ID': 'test-chat-id'
        }
    
    @pytest.fixture
    def sample_category(self):
        """Create sample category for testing."""
        return Category(
            category_id="integration-test",
            name="Integration Test",
            description="Category for integration testing",
            prompt_template="Create content about {topic}. Make it engaging and informative."
        )
    
    @pytest.mark.asyncio
    async def test_generator_with_category_integration(self, mock_env_config, sample_category):
        """Test generator integration with category objects."""
        
        with patch.dict(os.environ, mock_env_config):
            # Mock OpenAI response
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message = Mock()
            mock_response.choices[0].message.content = "Integration test content! #Integration #Test"
            
            with patch('openai.AsyncOpenAI') as mock_openai:
                mock_client = AsyncMock()
                mock_client.chat.completions.create.return_value = mock_response
                mock_openai.return_value = mock_client
                
                # Initialize generator
                config = Config()
                generator = ContentGenerator(config)
                
                # Generate content
                entry = await generator.generate_content(
                    category=sample_category,
                    topic="Integration Testing"
                )
                
                # Verify integration
                assert entry is not None
                assert "integration" in entry.content.lower()
                assert len(entry.metadata.tags) == 2
                assert entry.metadata.source == "openai"
    
    @pytest.mark.asyncio
    async def test_generator_error_handling_integration(self, mock_env_config, sample_category):
        """Test generator error handling integration."""
        
        with patch.dict(os.environ, mock_env_config):
            with patch('openai.AsyncOpenAI') as mock_openai:
                # Mock API failure
                mock_client = AsyncMock()
                mock_client.chat.completions.create.side_effect = Exception("API Error")
                mock_openai.return_value = mock_client
                
                # Initialize generator
                config = Config()
                generator = ContentGenerator(config)
                
                # Attempt generation
                entry = await generator.generate_content(
                    category=sample_category,
                    topic="Error Test"
                )
                
                # Should handle error gracefully
                assert entry is None


class TestPublisherIntegration:
    """Test Publisher integration scenarios."""
    
    @pytest.fixture
    def sample_content(self):
        """Sample content for testing."""
        return PostContent(
            content="Integration test content for social media posting! #test #integration",
            topic="Integration Testing",
            hashtags=["#test", "#integration"],
            platform="x",
            category_id="test-category"
        )
    
    @pytest.mark.asyncio
    async def test_twitter_telegram_publishing_integration(self, sample_content):
        """Test publishing to both Twitter and Telegram."""
        # Mock Twitter config and publisher
        twitter_config = TwitterConfig(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_token_secret="test_token_secret"
        )
        
        # Mock Telegram config and publisher
        telegram_config = TelegramConfig(
            bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            chat_id="@testchannel"
        )
        
        # Mock successful responses
        with patch('bot.publisher.twitter.tweepy.Client') as mock_twitter_client, \
             patch('httpx.AsyncClient') as mock_telegram_client:
            
            # Setup Twitter mock
            mock_twitter_response = Mock()
            mock_twitter_response.data = {"id": "123456789"}
            mock_twitter_client.return_value.create_tweet.return_value = mock_twitter_response
            
            # Setup Telegram mock - use AsyncMock for proper async behavior
            mock_telegram_instance = AsyncMock()
            mock_telegram_response = Mock()
            mock_telegram_response.status_code = 200
            mock_telegram_response.json.return_value = {
                "ok": True,
                "result": {"message_id": 123}
            }
            mock_telegram_instance.post.return_value = mock_telegram_response
            mock_telegram_instance.aclose.return_value = None
            mock_telegram_client.return_value = mock_telegram_instance
            
            # Test publishing
            twitter_publisher = TwitterPublisher(twitter_config)
            telegram_publisher = TelegramPublisher(telegram_config)
            
            # Test Twitter publishing
            twitter_result = await twitter_publisher.post_content(sample_content.model_copy())
            assert twitter_result is True
            
            # Test Telegram publishing
            async with telegram_publisher:
                telegram_content = sample_content.model_copy()
                telegram_content.platform = "telegram"
                telegram_result = await telegram_publisher.post_content(telegram_content)
                assert telegram_result is True
    
    @pytest.mark.asyncio
    async def test_publisher_failure_recovery_integration(self, sample_content):
        """Test publisher failure and recovery scenarios."""
        twitter_config = TwitterConfig(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_token_secret="test_token_secret"
        )
        
        with patch('bot.publisher.twitter.tweepy.Client') as mock_client_class:
            mock_client = Mock()
            
            # First attempt fails with rate limit
            mock_client.create_tweet.side_effect = [
                Exception("Rate limit exceeded"),
                Mock(data={"id": "123456789"})  # Second attempt succeeds
            ]
            mock_client_class.return_value = mock_client
            
            publisher = TwitterPublisher(twitter_config)
            
            # First attempt should fail
            result1 = await publisher.post_content(sample_content.model_copy())
            assert result1 is False
            
            # Second attempt should succeed (simulating retry)
            result2 = await publisher.post_content(sample_content.model_copy())
            assert result2 is True


class TestDatabaseIntegration:
    """Test database integration with other components."""
    
    @pytest.fixture
    def temp_db_dir(self):
        """Create temporary database directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.mark.asyncio
    async def test_category_storage_and_retrieval_integration(self, temp_db_dir):
        """Test storing and retrieving categories with JsonORM."""
        # Create category manager
        manager = JSONCategoryManager(str(temp_db_dir))
        
        # Create category
        category = Category(
            category_id="test-category",
            name="Test Category",
            description="Test category for database integration",
            prompt_template="Generate content about {topic}",
            topics=[]
        )
        
        # Store category
        manager.save_category(category)
        
        # Retrieve category
        retrieved_category = manager.load_category("test-category")
        
        assert retrieved_category is not None
        assert retrieved_category.category_id == category.category_id
        assert retrieved_category.name == category.name
        assert retrieved_category.description == category.description
    
    @pytest.mark.asyncio
    async def test_category_with_entries_integration(self, temp_db_dir):
        """Test category with entries storage and retrieval."""
        manager = JSONCategoryManager(str(temp_db_dir))
        
        # Create category with entry
        category = Category(
            category_id="test-category",
            name="Test Category",
            description="Test category",
            topics=[]
        )
        
        # Add entry to category
        metadata = CategoryMetadata(
            length=50,
            source="test",
            tags=["#test", "#integration"]
        )
        
        entry = CategoryEntry(
            content="Test content for integration! #test #integration",
            metadata=metadata
        )
        
        category.add_entry("Test Topic", entry)
        
        # Store and retrieve
        manager.save_category(category)
        retrieved_category = manager.load_category("test-category")
        
        assert len(retrieved_category.topics) == 1
        assert retrieved_category.topics[0].topic == "Test Topic"
        assert len(retrieved_category.topics[0].entries) == 1
        assert retrieved_category.topics[0].entries[0].content == entry.content
    
    @pytest.mark.asyncio
    async def test_database_error_handling_integration(self, temp_db_dir):
        """Test database error handling integration."""
        # Use invalid path to trigger error
        invalid_path = temp_db_dir / "nonexistent"
        
        # This should raise an error when trying to create the manager
        with pytest.raises((FileNotFoundError, OSError)):
            manager = JSONCategoryManager(str(invalid_path / "invalid.json"))


class TestFullWorkflowIntegration:
    """Test complete workflow integration scenarios."""
    
    @pytest.fixture
    def mock_full_config(self):
        """Mock configuration for full workflow testing."""
        return {
            'OPENAI_API_KEY': 'test-openai-key',
            'TWITTER_API_KEY': 'test-twitter-key',
            'TWITTER_API_SECRET': 'test-twitter-secret',
            'TWITTER_ACCESS_TOKEN': 'test-twitter-token',
            'TWITTER_ACCESS_TOKEN_SECRET': 'test-twitter-token-secret',
            'TELEGRAM_BOT_TOKEN': 'test-telegram-token',
            'TELEGRAM_CHAT_ID': 'test-chat-id',
            'DRY_RUN': 'true',
            'CONTENT_MIN_LENGTH': '20',
            'CONTENT_MAX_LENGTH': '200',
            'REQUIRED_HASHTAGS': '2'
        }
    
    @pytest.fixture
    def temp_workflow_dir(self):
        """Create temporary directory for workflow testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.mark.asyncio
    async def test_complete_content_generation_workflow(self, mock_full_config, temp_workflow_dir):
        """Test complete workflow: generate content -> publish to platforms."""
        
        with patch.dict(os.environ, mock_full_config, clear=True):
            # Create sample category
            category = Category(
                category_id="test-category",
                name="Test Category",
                description="Integration test category",
                prompt_template="Create content about {topic}. Keep it under 200 characters. Add exactly 2 hashtags.",
                topics=[]
            )
            
            # Mock OpenAI response
            mock_openai_response = Mock()
            mock_openai_response.choices = [Mock()]
            mock_openai_response.choices[0].message = Mock()
            mock_openai_response.choices[0].message.content = "AI automation is transforming workflows! #AI #Automation"
            
            # Mock publisher responses
            mock_twitter_response = Mock()
            mock_twitter_response.data = {"id": "123456789"}
            
            with patch('openai.AsyncOpenAI') as mock_openai, \
                 patch('bot.publisher.twitter.tweepy.Client') as mock_twitter_client:
                
                # Setup mocks
                mock_openai_client = AsyncMock()
                mock_openai_client.chat.completions.create.return_value = mock_openai_response
                mock_openai.return_value = mock_openai_client
                
                mock_twitter_client.return_value.create_tweet.return_value = mock_twitter_response
                
                # Initialize components with real Config
                config = Config()
                generator = ContentGenerator(config)
                
                twitter_config = TwitterConfig(
                    api_key=config.twitter_api_key,
                    api_secret=config.twitter_api_secret,
                    access_token=config.twitter_access_token,
                    access_token_secret=config.twitter_access_token_secret
                )
                twitter_publisher = TwitterPublisher(twitter_config)
                
                # Step 1: Generate content
                entry = await generator.generate_content(
                    category=category,
                    topic="AI Automation"
                )
                
                assert entry is not None
                assert "AI" in entry.content
                assert "Automation" in entry.content
                assert len(entry.metadata.tags) == 2
                
                # Step 2: Create PostContent from CategoryEntry
                post_content = PostContent(
                    content=entry.content,
                    topic="AI Automation",
                    hashtags=entry.metadata.tags,
                    platform="x",
                    category_id=category.category_id
                )
                
                # Step 3: Publish content
                result = await twitter_publisher.post_content(post_content)
                assert result is True
                assert post_content.status == PostStatus.POSTED


class TestConcurrencyIntegration:
    """Test concurrent operations integration."""
    
    @pytest.mark.asyncio
    async def test_concurrent_content_generation(self):
        """Test concurrent content generation."""
        mock_env = {
            'OPENAI_API_KEY': 'test-openai-key',
            'CONTENT_MIN_LENGTH': '20',
            'CONTENT_MAX_LENGTH': '200',
            'REQUIRED_HASHTAGS': '2',
            'DRY_RUN': 'false'
        }
        
        with patch.dict(os.environ, mock_env, clear=True):
            config = Config()
            
            category = Category(
                category_id="test-category",
                name="Test Category",
                description="Test category",
                prompt_template="Generate content about {topic}",
                topics=[]
            )
            
            # Mock OpenAI responses
            mock_responses = []
            for i in range(3):
                mock_response = Mock()
                mock_response.choices = [Mock()]
                mock_response.choices[0].message = Mock()
                mock_response.choices[0].message.content = f"Concurrent test content {i}! #test #concurrent"
                mock_responses.append(mock_response)
            
            with patch('openai.AsyncOpenAI') as mock_openai:
                mock_client = AsyncMock()
                mock_client.chat.completions.create.side_effect = mock_responses
                mock_openai.return_value = mock_client
                
                generator = ContentGenerator(config)
                
                # Generate multiple contents concurrently
                tasks = [
                    generator.generate_content(category=category, topic=f"Topic {i}")
                    for i in range(3)
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # All should succeed
                assert len(results) == 3
                for result in results:
                    assert isinstance(result, CategoryEntry)
                    assert "Concurrent test content" in result.content
    
    @pytest.mark.asyncio
    async def test_concurrent_publishing(self):
        """Test concurrent publishing to multiple platforms."""
        # Create multiple content pieces
        contents = [
            PostContent(
                content=f"Concurrent publishing test {i}! #test #concurrent",
                topic=f"Topic {i}",
                hashtags=["#test", "#concurrent"],
                platform="x",
                category_id="test-category"
            )
            for i in range(3)
        ]
        
        twitter_config = TwitterConfig(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_token_secret="test_token_secret"
        )
        
        # Mock successful responses
        with patch('bot.publisher.twitter.tweepy.Client') as mock_client_class:
            mock_client = Mock()
            mock_responses = [Mock(data={"id": f"12345678{i}"}) for i in range(3)]
            mock_client.create_tweet.side_effect = mock_responses
            mock_client_class.return_value = mock_client
            
            publisher = TwitterPublisher(twitter_config)
            
            # Publish concurrently
            tasks = [publisher.post_content(content) for content in contents]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All should succeed
            assert len(results) == 3
            assert all(result is True for result in results)
            assert all(content.status == PostStatus.POSTED for content in contents) 