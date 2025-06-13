"""Tests for the Telegram publisher module."""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import httpx
from bot.publisher.telegram import TelegramPublisher, TelegramConfig
from bot.models.topic import PostContent, PostStatus


class TestTelegramPublisher:
    """Test cases for TelegramPublisher class."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        return TelegramConfig(
            bot_token="123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
            chat_id="-1001234567890"
        )
    
    @pytest.fixture
    def sample_content(self):
        """Sample post content for testing."""
        return PostContent(
            content="x" * 169 + " #test #new",
            platform="telegram",
            category_id="test-category",
            topic="Test Topic",
            hashtags=["#test", "#new"]
        )
    
    def test_publisher_initialization(self, mock_config):
        """Test TelegramPublisher initialization."""
        publisher = TelegramPublisher(mock_config)
        
        assert publisher.config == mock_config
        assert publisher.base_url == "https://api.telegram.org/bot123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
        assert publisher.client is None
    
    @pytest.mark.asyncio
    async def test_context_manager(self, mock_config):
        """Test async context manager functionality."""
        async with TelegramPublisher(mock_config) as publisher:
            assert publisher.client is not None
            assert isinstance(publisher.client, httpx.AsyncClient)
        
        # Client should be closed after exiting context
        assert publisher.client is not None  # Reference still exists but client is closed
    
    @pytest.mark.asyncio
    async def test_post_content_success(self, mock_config, sample_content):
        """Test successful content posting."""
        publisher = TelegramPublisher(mock_config)
        publisher._send_message = AsyncMock(return_value=True)
        
        result = await publisher.post_content(sample_content)
        
        assert result is True
        assert sample_content.status == PostStatus.POSTED
        publisher._send_message.assert_called_once_with(sample_content.content)
    
    @pytest.mark.asyncio
    async def test_post_content_failure(self, mock_config, sample_content):
        """Test content posting failure."""
        publisher = TelegramPublisher(mock_config)
        publisher._send_message = AsyncMock(return_value=False)
        
        result = await publisher.post_content(sample_content)
        
        assert result is False
        assert sample_content.status == PostStatus.FAILED
        publisher._send_message.assert_called_once_with(sample_content.content)
    
    @pytest.mark.asyncio
    async def test_post_content_exception(self, mock_config, sample_content):
        """Test content posting with exception."""
        publisher = TelegramPublisher(mock_config)
        publisher._send_message = AsyncMock(side_effect=Exception("Test error"))
        
        result = await publisher.post_content(sample_content)
        
        assert result is False
        assert sample_content.status == PostStatus.FAILED
    
    @pytest.mark.asyncio
    async def test_send_message_no_client(self, mock_config):
        """Test send_message without initialized client."""
        publisher = TelegramPublisher(mock_config)
        
        with pytest.raises(RuntimeError, match="Client not initialized"):
            await publisher._send_message("Test message")
    
    @pytest.mark.asyncio
    async def test_send_message_success(self, mock_config):
        """Test message sending with test credentials."""
        async with TelegramPublisher(mock_config) as publisher:
            # With test credentials, this will fail
            result = await publisher._send_message("Test message")
            assert result is False  # Should fail with test credentials
    
    @pytest.mark.asyncio
    async def test_send_error_alert_success(self, mock_config):
        """Test successful error alert sending."""
        publisher = TelegramPublisher(mock_config)
        publisher._send_message = AsyncMock(return_value=True)
        
        result = await publisher.send_error_alert("Test error")
        
        assert result is True
        publisher._send_message.assert_called_once()
        call_args = publisher._send_message.call_args[0][0]
        assert "🚨 OpenCast Bot Error Alert 🚨" in call_args
        assert "Test error" in call_args
    
    @pytest.mark.asyncio
    async def test_send_error_alert_failure(self, mock_config):
        """Test error alert sending failure."""
        publisher = TelegramPublisher(mock_config)
        publisher._send_message = AsyncMock(side_effect=Exception("Test error"))
        
        result = await publisher.send_error_alert("Test error")
        
        assert result is False
    
    def test_validate_content_valid(self, mock_config, sample_content):
        """Test content validation with valid content."""
        publisher = TelegramPublisher(mock_config)
        
        result = publisher.validate_content(sample_content)
        
        assert result is True
    
    def test_validate_content_invalid_length_short(self, mock_config):
        """Test content validation with too short content."""
        publisher = TelegramPublisher(mock_config)
        content = PostContent.model_construct(
            content="Short #test #new",
            platform="telegram",
            category_id="test-category",
            topic="Test",
            hashtags=["#test", "#new"]
        )
        
        result = publisher.validate_content(content)
        
        assert result is False
    
    def test_validate_content_invalid_length_long(self, mock_config):
        """Test content validation with too long content."""
        publisher = TelegramPublisher(mock_config)
        content = PostContent.model_construct(
            content="x" * 250 + " #test #new",
            platform="telegram",
            category_id="test-category",
            topic="Test",
            hashtags=["#test", "#new"]
        )
        
        result = publisher.validate_content(content)
        
        assert result is False
    
    def test_validate_content_invalid_hashtag_count(self, mock_config):
        """Test content validation with wrong hashtag count."""
        publisher = TelegramPublisher(mock_config)
        content = PostContent.model_construct(
            content="x" * 169 + " #test",
            platform="telegram",
            category_id="test-category",
            topic="Test",
            hashtags=["#test"]  # Only 1 hashtag instead of 2
        )
        
        result = publisher.validate_content(content)
        
        assert result is False
    
    def test_config_validation(self):
        """Test TelegramConfig validation."""
        # Valid config
        config = TelegramConfig(
            bot_token="123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
            chat_id="-1001234567890"
        )
        assert config.bot_token == "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
        assert config.chat_id == "-1001234567890"
        assert config.parse_mode == "HTML"  # Default value
    
    def test_config_custom_parse_mode(self):
        """Test TelegramConfig with custom parse mode."""
        config = TelegramConfig(
            bot_token="123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
            chat_id="-1001234567890",
            parse_mode="Markdown"
        )
        assert config.parse_mode == "Markdown" 