"""Tests for the main module."""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from bot.main import OpenCastBot, main
from bot.models.category import Category, CategoryEntry, CategoryMetadata
from bot.config import Config


class TestOpenCastBot:
    """Test cases for OpenCastBot class."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        config = Mock()  # Remove spec=Config to allow any attribute
        config.categories_directory = "/tmp/test"
        config.dry_run = False
        config.get_enabled_platforms.return_value = ["twitter", "telegram"]
        config.validate_twitter_config.return_value = True
        config.validate_telegram_config.return_value = True
        config.setup_logging = Mock(return_value=None)
        
        # Add real string values for Twitter config
        config.twitter_api_key = "test_api_key"
        config.twitter_api_secret = "test_api_secret"
        config.twitter_access_token = "test_access_token"
        config.twitter_access_token_secret = "test_access_token_secret"
        config.twitter_bearer_token = "test_bearer_token"
        
        # Add real string values for Telegram config
        config.telegram_bot_token = "test_bot_token"
        config.telegram_chat_id = "test_chat_id"
        
        return config
    
    @pytest.fixture
    def sample_category_data(self):
        """Sample category data for testing."""
        return {
            "category_id": "test-category",
            "name": "Test Category",
            "description": "Test description",
            "prompt_template": "Generate content about {topic}.",
            "language": "en",
            "topics": [
                {
                    "topic": "Test Topic",
                    "entries": [
                        {
                            "content": "x" * 169 + " #test #new",
                            "metadata": {
                                "length": 180,
                                "source": "openai",
                                "tags": ["#test", "#new"]
                            },
                            "created_at": "2024-01-01T00:00:00"
                        }
                    ]
                }
            ]
        }
    
    @patch('bot.main.JsonORM')
    @patch('bot.main.ContentGenerator')
    def test_bot_initialization(self, mock_generator, mock_orm, mock_config):
        """Test OpenCastBot initialization."""
        bot = OpenCastBot(mock_config)
        
        assert bot.config == mock_config
        mock_orm.assert_called_once_with(mock_config.categories_directory)
        mock_generator.assert_called_once_with(mock_config)
    
    @patch('bot.main.JsonORM')
    @patch('bot.main.ContentGenerator')
    @pytest.mark.asyncio
    async def test_run_success(self, mock_generator, mock_orm, mock_config, sample_category_data):
        """Test successful bot run."""
        # Setup mocks
        category = Category(**sample_category_data)
        mock_orm_instance = Mock()
        mock_orm_instance.load_category.return_value = category
        mock_orm_instance.save_category.return_value = None
        mock_orm.return_value = mock_orm_instance
        
        entry = CategoryEntry(
            content="x" * 169 + " #test #new",
            metadata=CategoryMetadata(length=180, source="openai", tags=["#test", "#new"])
        )
        mock_generator_instance = Mock()
        mock_generator_instance.generate_content = AsyncMock(return_value=entry)
        mock_generator.return_value = mock_generator_instance
        
        bot = OpenCastBot(mock_config)
        bot._post_to_platforms = AsyncMock(return_value=True)
        
        # Run test
        result = await bot.run("test-category", "New Topic")
        
        # Verify
        assert result is True
        mock_orm_instance.load_category.assert_called_once_with("test-category")
        mock_generator_instance.generate_content.assert_called_once()
        mock_orm_instance.save_category.assert_called_once()
        bot._post_to_platforms.assert_called_once()
    
    @patch('bot.main.JsonORM')
    @patch('bot.main.ContentGenerator')
    @pytest.mark.asyncio
    async def test_run_category_not_found(self, mock_generator, mock_orm, mock_config):
        """Test bot run when category is not found."""
        # Setup mocks
        mock_orm_instance = Mock()
        mock_orm_instance.load_category.return_value = None
        mock_orm.return_value = mock_orm_instance
        
        bot = OpenCastBot(mock_config)
        
        # Run test
        result = await bot.run("nonexistent", "Topic")
        
        # Verify
        assert result is False
        mock_orm_instance.load_category.assert_called_once_with("nonexistent")
    
    @patch('bot.main.JsonORM')
    @patch('bot.main.ContentGenerator')
    @pytest.mark.asyncio
    async def test_run_no_content_generated(self, mock_generator, mock_orm, mock_config, sample_category_data):
        """Test bot run when no content is generated."""
        # Setup mocks
        category = Category(**sample_category_data)
        mock_orm_instance = Mock()
        mock_orm_instance.load_category.return_value = category
        mock_orm.return_value = mock_orm_instance
        
        mock_generator_instance = Mock()
        mock_generator_instance.generate_content = AsyncMock(return_value=None)
        mock_generator.return_value = mock_generator_instance
        
        bot = OpenCastBot(mock_config)
        
        # Run test
        result = await bot.run("test-category", "Topic")
        
        # Verify
        assert result is False
        mock_generator_instance.generate_content.assert_called_once()
    
    @patch('bot.main.JsonORM')
    @patch('bot.main.ContentGenerator')
    @pytest.mark.asyncio
    async def test_run_no_platforms_configured(self, mock_generator, mock_orm, mock_config, sample_category_data):
        """Test bot run when no platforms are configured."""
        # Setup mocks
        mock_config.get_enabled_platforms.return_value = []
        
        category = Category(**sample_category_data)
        mock_orm_instance = Mock()
        mock_orm_instance.load_category.return_value = category
        mock_orm_instance.save_category.return_value = None
        mock_orm.return_value = mock_orm_instance
        
        entry = CategoryEntry(
            content="x" * 169 + " #test #new",
            metadata=CategoryMetadata(length=180, source="openai", tags=["#test", "#new"])
        )
        mock_generator_instance = Mock()
        mock_generator_instance.generate_content = AsyncMock(return_value=entry)
        mock_generator.return_value = mock_generator_instance
        
        bot = OpenCastBot(mock_config)
        
        # Run test
        result = await bot.run("test-category", "Topic")
        
        # Verify - should still return True as content was generated
        assert result is True
        mock_orm_instance.save_category.assert_called_once()
    
    @patch('bot.main.JsonORM')
    @patch('bot.main.ContentGenerator')
    @pytest.mark.asyncio
    async def test_run_exception_handling(self, mock_generator, mock_orm, mock_config):
        """Test bot run exception handling."""
        # Setup mocks to raise exception
        mock_orm_instance = Mock()
        mock_orm_instance.load_category.side_effect = Exception("Test error")
        mock_orm.return_value = mock_orm_instance
        
        bot = OpenCastBot(mock_config)
        
        # Run test
        result = await bot.run("test-category", "Topic")
        
        # Verify
        assert result is False
    
    @patch('bot.main.JsonORM')
    @patch('bot.main.ContentGenerator')
    @pytest.mark.asyncio
    async def test_post_to_platforms_success(self, mock_generator, mock_orm, mock_config):
        """Test successful posting to platforms."""
        bot = OpenCastBot(mock_config)
        bot._post_to_twitter = AsyncMock(return_value=True)
        bot._post_to_telegram = AsyncMock(return_value=True)
        
        # Run test
        result = await bot._post_to_platforms("Test content", "category", "topic", ["twitter", "telegram"])
        
        # Verify
        assert result is True
        bot._post_to_twitter.assert_called_once_with("Test content", "category", "topic")
        bot._post_to_telegram.assert_called_once_with("Test content", "category", "topic")
    
    @patch('bot.main.JsonORM')
    @patch('bot.main.ContentGenerator')
    @pytest.mark.asyncio
    async def test_post_to_platforms_partial_failure(self, mock_generator, mock_orm, mock_config):
        """Test posting to platforms with partial failure."""
        bot = OpenCastBot(mock_config)
        bot._post_to_twitter = AsyncMock(return_value=True)
        bot._post_to_telegram = AsyncMock(return_value=False)
        
        # Run test
        result = await bot._post_to_platforms("Test content", "category", "topic", ["twitter", "telegram"])
        
        # Verify
        assert result is False
    
    @patch('bot.main.JsonORM')
    @patch('bot.main.ContentGenerator')
    @pytest.mark.asyncio
    async def test_post_to_platforms_invalid_platform(self, mock_generator, mock_orm, mock_config):
        """Test posting to invalid platform."""
        bot = OpenCastBot(mock_config)
        
        # Run test
        result = await bot._post_to_platforms("Test content", "category", "topic", ["invalid"])
        
        # Verify - should return False when no valid platforms are configured
        assert result is False
    
    @patch('bot.main.JsonORM')
    @patch('bot.main.ContentGenerator')
    @pytest.mark.asyncio
    async def test_post_to_twitter_dry_run(self, mock_generator, mock_orm, mock_config):
        """Test Twitter posting in dry run mode."""
        mock_config.dry_run = True
        bot = OpenCastBot(mock_config)
        
        # Run test
        result = await bot._post_to_twitter("Test content", "category", "topic")
        
        # Verify
        assert result is True
    
    @patch('bot.main.JsonORM')
    @patch('bot.main.ContentGenerator')
    @pytest.mark.asyncio
    async def test_post_to_telegram_dry_run(self, mock_generator, mock_orm, mock_config):
        """Test Telegram posting in dry run mode."""
        mock_config.dry_run = True
        bot = OpenCastBot(mock_config)
        
        # Run test
        result = await bot._post_to_telegram("Test content", "category", "topic")
        
        # Verify
        assert result is True
    
    @patch('bot.main.TwitterPublisher')
    @patch('bot.main.JsonORM')
    @patch('bot.main.ContentGenerator')
    @pytest.mark.asyncio
    async def test_post_to_twitter_normal_mode(self, mock_generator, mock_orm, mock_twitter, mock_config):
        """Test Twitter posting in normal mode."""
        # Mock Twitter publisher
        mock_publisher = Mock()
        mock_publisher.post_content = AsyncMock(return_value=True)
        mock_twitter.return_value.__aenter__.return_value = mock_publisher
        
        bot = OpenCastBot(mock_config)
        
        # Use valid content (20-220 chars with hashtags)
        valid_content = "This is a test content with proper length and formatting! #test #content"
        
        # Run test
        result = await bot._post_to_twitter(valid_content, "test-category", "Test Topic")
        
        # Verify
        assert result is True
        mock_twitter.assert_called_once()
    
    @patch('bot.main.TelegramPublisher')
    @patch('bot.main.JsonORM')
    @patch('bot.main.ContentGenerator')
    @pytest.mark.asyncio
    async def test_post_to_telegram_normal_mode(self, mock_generator, mock_orm, mock_telegram, mock_config):
        """Test Telegram posting in normal mode."""
        # Mock Telegram publisher
        mock_publisher = Mock()
        mock_publisher.post_content = AsyncMock(return_value=True)
        mock_telegram.return_value.__aenter__.return_value = mock_publisher
        
        bot = OpenCastBot(mock_config)
        
        # Use valid content (20-220 chars with hashtags)
        valid_content = "This is a test content with proper length and formatting! #test #content"
        
        # Run test
        result = await bot._post_to_telegram(valid_content, "test-category", "Test Topic")
        
        # Verify
        assert result is True
        mock_telegram.assert_called_once()


class TestMainFunction:
    """Test cases for main function."""
    
    @patch('bot.main.OpenCastBot')
    @patch('bot.main.get_config')
    @pytest.mark.asyncio
    async def test_main_function(self, mock_get_config, mock_bot_class):
        """Test main function execution."""
        # Setup mocks
        mock_bot_instance = Mock()
        mock_bot_instance.run = AsyncMock(return_value=True)
        mock_bot_class.return_value = mock_bot_instance
        
        # Run test
        await main()
        
        # Verify
        mock_bot_class.assert_called_once_with(mock_get_config.return_value)
        mock_bot_instance.run.assert_called_once() 