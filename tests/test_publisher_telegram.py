"""Tests for the Telegram publisher module."""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import httpx
from bot.publisher.telegram import TelegramPublisher, TelegramConfig
from bot.models.topic import PostContent, PostStatus
from bot.utils.exceptions import (
    AuthenticationError, 
    AuthorizationError, 
    APIError, 
    RateLimitError, 
    ValidationError,
    NetworkError
)


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
        
        with pytest.raises(APIError, match="Telegram client not initialized"):
            await publisher._send_message("Test message")
    
    @pytest.mark.asyncio
    async def test_send_message_success(self, mock_config):
        """Test message sending with mocked response."""
        with patch('httpx.AsyncClient.post') as mock_post:
            # Mock successful response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "ok": True,
                "result": {"message_id": 123}
            }
            mock_post.return_value = mock_response
            
            async with TelegramPublisher(mock_config) as publisher:
                result = await publisher._send_message("Test message")
                assert result is True
                mock_post.assert_called_once()
    
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
            bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            chat_id="@testchannel",
            parse_mode="Markdown"
        )
        
        assert config.parse_mode == "Markdown"
    
    @pytest.mark.asyncio
    async def test_context_manager_client_init_error(self):
        """Test async context manager with client initialization error."""
        config = TelegramConfig(
            bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            chat_id="@testchannel"
        )
        
        publisher = TelegramPublisher(config)
        
        with patch('bot.publisher.telegram.httpx.AsyncClient') as mock_client:
            mock_client.side_effect = Exception("Client init failed")
            
            with pytest.raises(NetworkError) as exc_info:
                async with publisher:
                    pass
            assert "Failed to initialize Telegram HTTP client" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_context_manager_client_close_error(self):
        """Test async context manager with client close error."""
        config = TelegramConfig(
            bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            chat_id="@testchannel"
        )
        
        publisher = TelegramPublisher(config)
        
        mock_client = AsyncMock()
        mock_client.aclose.side_effect = Exception("Close failed")
        
        with patch('bot.publisher.telegram.httpx.AsyncClient', return_value=mock_client):
            async with publisher:
                pass  # Should not raise, just log warning
    
    @pytest.mark.asyncio
    async def test_context_manager_with_exception(self):
        """Test async context manager with exception during execution."""
        config = TelegramConfig(
            bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            chat_id="@testchannel"
        )
        
        publisher = TelegramPublisher(config)
        
        try:
            async with publisher:
                raise ValueError("Test exception")
        except ValueError:
            pass  # Expected
    
    @pytest.mark.asyncio
    async def test_post_content_validation_failure(self):
        """Test post_content when validation fails."""
        config = TelegramConfig(
            bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            chat_id="@testchannel"
        )
        
        # Use model_construct to bypass validation for testing
        content = PostContent.model_construct(
            content="Short",  # Too short
            topic="test",
            hashtags=["#test"],
            platform="telegram",
            category_id="test-category"
        )
        
        publisher = TelegramPublisher(config)
        
        result = await publisher.post_content(content)
        
        assert result is False
        assert content.status == PostStatus.FAILED
    
    @pytest.mark.asyncio
    async def test_post_content_send_message_failure(self):
        """Test post_content when _send_message fails."""
        config = TelegramConfig(
            bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            chat_id="@testchannel"
        )
        
        content = PostContent(
            content="This is a valid test content with proper length and formatting! #test #demo",
            topic="test",
            hashtags=["#test", "#demo"],
            platform="telegram",
            category_id="test-category"
        )
        
        publisher = TelegramPublisher(config)
        
        with patch.object(publisher, '_send_message', return_value=False):
            result = await publisher.post_content(content)
            
            assert result is False
            assert content.status == PostStatus.FAILED
    
    @pytest.mark.asyncio
    async def test_post_content_unexpected_exception(self):
        """Test post_content with unexpected exception."""
        config = TelegramConfig(
            bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            chat_id="@testchannel"
        )
        
        content = PostContent(
            content="This is a valid test content with proper length and formatting! #test #demo",
            topic="test",
            hashtags=["#test", "#demo"],
            platform="telegram",
            category_id="test-category"
        )
        
        publisher = TelegramPublisher(config)
        
        with patch.object(publisher, 'validate_content', side_effect=Exception("Unexpected error")):
            result = await publisher.post_content(content)
            
            assert result is False
            assert content.status == PostStatus.FAILED
    
    @pytest.mark.asyncio
    async def test_send_message_no_client(self):
        """Test _send_message when client is not initialized."""
        config = TelegramConfig(
            bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            chat_id="@testchannel"
        )
        
        publisher = TelegramPublisher(config)
        publisher.client = None  # Simulate no client
        
        with pytest.raises(APIError) as exc_info:
            await publisher._send_message("Test message")
        assert "Telegram client not initialized" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_send_message_api_not_ok(self):
        """Test _send_message when API returns not ok."""
        config = TelegramConfig(
            bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            chat_id="@testchannel"
        )
        
        publisher = TelegramPublisher(config)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ok": False,
            "error_code": 400,
            "description": "Bad Request: message text is empty"
        }
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        publisher.client = mock_client
        
        with pytest.raises(ValidationError) as exc_info:
            await publisher._send_message("Test message")
        assert "Telegram API validation error" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_send_message_unauthorized_error(self):
        """Test _send_message with unauthorized error."""
        config = TelegramConfig(
            bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            chat_id="@testchannel"
        )
        
        publisher = TelegramPublisher(config)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ok": False,
            "error_code": 401,
            "description": "Unauthorized: bot token is invalid"
        }
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        publisher.client = mock_client
        
        with pytest.raises(AuthenticationError) as exc_info:
            await publisher._send_message("Test message")
        assert "bot token is invalid" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_send_message_rate_limit_error(self):
        """Test _send_message with rate limit error."""
        config = TelegramConfig(
            bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            chat_id="@testchannel"
        )
        
        publisher = TelegramPublisher(config)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ok": False,
            "error_code": 429,
            "description": "Too Many Requests: retry after 30"
        }
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        publisher.client = mock_client
        
        with pytest.raises(RateLimitError) as exc_info:
            await publisher._send_message("Test message")
        assert "rate limit exceeded" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_send_message_generic_api_error(self):
        """Test _send_message with generic API error."""
        config = TelegramConfig(
            bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            chat_id="@testchannel"
        )
        
        publisher = TelegramPublisher(config)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ok": False,
            "error_code": 500,
            "description": "Internal Server Error"
        }
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        publisher.client = mock_client
        
        with pytest.raises(APIError) as exc_info:
            await publisher._send_message("Test message")
        assert "Telegram API error" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_send_message_http_error(self):
        """Test _send_message with HTTP error."""
        config = TelegramConfig(
            bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            chat_id="@testchannel"
        )
        
        publisher = TelegramPublisher(config)
        
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        publisher.client = mock_client
        
        with pytest.raises(NetworkError) as exc_info:
            await publisher._send_message("Test message")
        assert "HTTP error 500" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_send_message_network_exception(self):
        """Test _send_message with network exception."""
        config = TelegramConfig(
            bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            chat_id="@testchannel"
        )
        
        publisher = TelegramPublisher(config)
        
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("Network error")
        publisher.client = mock_client
        
        with pytest.raises(APIError) as exc_info:  # Changed to APIError since it gets wrapped
            await publisher._send_message("Test message")
        assert "network error" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_send_error_alert_success(self):
        """Test successful error alert sending."""
        config = TelegramConfig(
            bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            chat_id="@testchannel"
        )
        
        publisher = TelegramPublisher(config)
        
        with patch.object(publisher, '_send_message', return_value=True):
            result = await publisher.send_error_alert("Test error message")
            assert result is True
    
    @pytest.mark.asyncio
    async def test_send_error_alert_failure(self):
        """Test error alert sending failure."""
        config = TelegramConfig(
            bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            chat_id="@testchannel"
        )
        
        publisher = TelegramPublisher(config)
        
        with patch.object(publisher, '_send_message', side_effect=Exception("Send failed")):
            result = await publisher.send_error_alert("Test error message")
            assert result is False
    
    @pytest.mark.asyncio
    async def test_send_message_timeout_exception(self):
        """Test _send_message with timeout exception."""
        config = TelegramConfig(
            bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            chat_id="@testchannel"
        )
        
        publisher = TelegramPublisher(config)
        
        import httpx
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.TimeoutException("Request timeout")
        publisher.client = mock_client
        
        with pytest.raises(NetworkError) as exc_info:
            await publisher._send_message("Test message")
        assert "timeout" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_send_message_httpx_network_error(self):
        """Test _send_message with httpx network error."""
        config = TelegramConfig(
            bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            chat_id="@testchannel"
        )
        
        publisher = TelegramPublisher(config)
        
        import httpx
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.NetworkError("Network connection failed")
        publisher.client = mock_client
        
        with pytest.raises(NetworkError) as exc_info:
            await publisher._send_message("Test message")
        assert "network error" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_post_content_api_error_handling(self):
        """Test post_content with API error from _send_message."""
        config = TelegramConfig(
            bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            chat_id="@testchannel"
        )
        
        content = PostContent(
            content="This is a valid test content with proper length and formatting! #test #demo",
            topic="test",
            hashtags=["#test", "#demo"],
            platform="telegram",
            category_id="test-category"
        )
        
        publisher = TelegramPublisher(config)
        
        # Mock _send_message to raise APIError
        with patch.object(publisher, '_send_message', side_effect=APIError("API failed", api_name="telegram", operation="send")):
            result = await publisher.post_content(content)
            
            assert result is False
            assert content.status == PostStatus.FAILED
    
    @pytest.mark.asyncio
    async def test_context_manager_httpx_client_creation(self):
        """Test context manager creates httpx.AsyncClient properly."""
        config = TelegramConfig(
            bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            chat_id="@testchannel"
        )
        
        publisher = TelegramPublisher(config)
        
        # Test that client is None initially
        assert publisher.client is None
        
        async with publisher as pub:
            # Test that client is created and is httpx.AsyncClient
            assert pub.client is not None
            import httpx
            assert isinstance(pub.client, httpx.AsyncClient)
        
        # Client reference still exists but should be closed
        assert publisher.client is not None
    
    def test_validate_content_edge_cases(self):
        """Test validate_content with edge cases."""
        config = TelegramConfig(
            bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            chat_id="@testchannel"
        )
        
        publisher = TelegramPublisher(config)
        
        # Test exactly 20 characters (minimum valid)
        content_min = PostContent.model_construct(
            content="x" * 14 + " #a #b",  # Exactly 20 chars
            platform="telegram",
            category_id="test-category",
            topic="Test",
            hashtags=["#a", "#b"]
        )
        assert publisher.validate_content(content_min) is True
        
        # Test exactly 220 characters (maximum valid)
        content_max = PostContent.model_construct(
            content="x" * 214 + " #a #b",  # Exactly 220 chars
            platform="telegram",
            category_id="test-category",
            topic="Test",
            hashtags=["#a", "#b"]
        )
        assert publisher.validate_content(content_max) is True
        
        # Test 19 characters (too short)
        content_short = PostContent.model_construct(
            content="x" * 13 + " #a #b",  # 19 chars
            platform="telegram",
            category_id="test-category",
            topic="Test",
            hashtags=["#a", "#b"]
        )
        assert publisher.validate_content(content_short) is False
        
        # Test 221 characters (too long)
        content_long = PostContent.model_construct(
            content="x" * 215 + " #a #b",  # 221 chars
            platform="telegram",
            category_id="test-category",
            topic="Test",
            hashtags=["#a", "#b"]
        )
        assert publisher.validate_content(content_long) is False 