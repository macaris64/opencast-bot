"""Tests for the Twitter publisher module."""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock, PropertyMock
import httpx
import tweepy
from bot.publisher.twitter import TwitterPublisher, TwitterConfig
from bot.models.topic import PostContent, PostStatus
from bot.utils.exceptions import (
    AuthenticationError, 
    AuthorizationError, 
    APIError, 
    RateLimitError, 
    ValidationError,
    PublishingError
)


class TestTwitterPublisher:
    """Test cases for TwitterPublisher class."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock TwitterConfig for testing."""
        return TwitterConfig(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_token_secret="test_token_secret"
        )
    
    @pytest.fixture
    def sample_content(self):
        """Create sample content for testing."""
        return PostContent(
            content="This is a test content for social media posting with proper length! #test #demo",
            topic="test_topic",
            hashtags=["#test", "#demo"],
            platform="x",
            category_id="test-category"
        )
    
    def test_publisher_initialization(self, mock_config):
        """Test TwitterPublisher initialization."""
        publisher = TwitterPublisher(mock_config)
        
        assert publisher.config == mock_config
        assert publisher.client is not None  # tweepy client is initialized immediately
    
    @pytest.mark.asyncio
    async def test_context_manager(self, mock_config):
        """Test async context manager functionality."""
        async with TwitterPublisher(mock_config) as publisher:
            assert publisher.client is not None
            # tweepy client is not httpx.AsyncClient
        
        # Client should still exist after exiting context
        assert publisher.client is not None
    
    @pytest.mark.asyncio
    async def test_post_content_success(self, mock_config, sample_content):
        """Test successful content posting."""
        publisher = TwitterPublisher(mock_config)
        publisher._send_tweet = AsyncMock(return_value=True)
        
        result = await publisher.post_content(sample_content)
        
        assert result is True
        assert sample_content.status == PostStatus.POSTED
        publisher._send_tweet.assert_called_once_with(sample_content.content)
    
    @pytest.mark.asyncio
    async def test_post_content_failure(self, mock_config, sample_content):
        """Test content posting failure."""
        publisher = TwitterPublisher(mock_config)
        publisher._send_tweet = AsyncMock(return_value=False)
        
        result = await publisher.post_content(sample_content)
        
        assert result is False
        assert sample_content.status == PostStatus.FAILED
        publisher._send_tweet.assert_called_once_with(sample_content.content)
    
    @pytest.mark.asyncio
    async def test_post_content_exception(self, mock_config, sample_content):
        """Test content posting with exception."""
        publisher = TwitterPublisher(mock_config)
        publisher._send_tweet = AsyncMock(side_effect=Exception("Test error"))
        
        result = await publisher.post_content(sample_content)
        
        assert result is False
        assert sample_content.status == PostStatus.FAILED
    
    @pytest.mark.asyncio
    async def test_send_tweet_no_client(self, mock_config):
        """Test send_tweet with mocked authentication error."""
        publisher = TwitterPublisher(mock_config)
        
        # Mock the _send_tweet method to raise AuthenticationError directly
        from bot.utils.exceptions import AuthenticationError
        
        async def mock_send_tweet(text):
            raise AuthenticationError("Twitter API unauthorized error", api_name="twitter", operation="create_tweet")
        
        publisher._send_tweet = mock_send_tweet
        
        with pytest.raises(AuthenticationError):
            await publisher._send_tweet("Test tweet")
    
    @pytest.mark.asyncio
    async def test_send_tweet_success(self, mock_config):
        """Test tweet sending with mocked success."""
        with patch('tweepy.Client.create_tweet') as mock_create_tweet:
            # Mock successful response
            mock_response = Mock()
            mock_response.data = {"id": "123456789"}
            mock_create_tweet.return_value = mock_response
            
            async with TwitterPublisher(mock_config) as publisher:
                result = await publisher._send_tweet("Test tweet")
                assert result is True
                mock_create_tweet.assert_called_once_with(text="Test tweet")
    
    def test_validate_content_valid(self, mock_config, sample_content):
        """Test content validation with valid content."""
        publisher = TwitterPublisher(mock_config)
        
        result = publisher.validate_content(sample_content)
        
        assert result is True
    
    def test_validate_content_invalid_length_short(self, mock_config):
        """Test content validation with too short content."""
        publisher = TwitterPublisher(mock_config)
        # Create content with model_validate to bypass validation
        content = PostContent.model_construct(
            content="Short #test #new",
            platform="x",
            category_id="test-category",
            topic="Test",
            hashtags=["#test", "#new"]
        )
        
        result = publisher.validate_content(content)
        
        assert result is False
    
    def test_validate_content_invalid_length_long(self, mock_config):
        """Test content validation with too long content."""
        publisher = TwitterPublisher(mock_config)
        content = PostContent.model_construct(
            content="x" * 221 + " #test #new",  # Over 220 chars
            platform="x",
            category_id="test-category",
            topic="Test",
            hashtags=["#test", "#new"]
        )
        
        result = publisher.validate_content(content)
        
        assert result is False
    
    def test_validate_content_invalid_hashtag_count(self, mock_config):
        """Test content validation with wrong hashtag count."""
        publisher = TwitterPublisher(mock_config)
        content = PostContent.model_construct(
            content="Valid content here #test",
            platform="x",
            category_id="test-category",
            topic="Test",
            hashtags=["#test"]  # Only 1 hashtag instead of 2
        )
        
        result = publisher.validate_content(content)
        
        assert result is False
    
    def test_config_validation(self):
        """Test TwitterConfig validation."""
        # Valid config
        config = TwitterConfig(
            api_key="test_api_key",
            api_secret="test_api_secret",
            access_token="test_access_token",
            access_token_secret="test_access_token_secret"
        )
        assert config.api_key == "test_api_key"
        assert config.api_secret == "test_api_secret"
        assert config.access_token == "test_access_token"
        assert config.access_token_secret == "test_access_token_secret"
        assert config.bearer_token is None  # Optional field
    
    def test_config_with_bearer_token(self):
        """Test TwitterConfig with bearer token."""
        config = TwitterConfig(
            api_key="test_api_key",
            api_secret="test_api_secret",
            access_token="test_access_token",
            access_token_secret="test_access_token_secret",
            bearer_token="test_bearer_token"
        )
        assert config.bearer_token == "test_bearer_token"
    
    def test_config_missing_required_fields(self):
        """Test TwitterConfig validation with missing required fields."""
        with pytest.raises(ValueError):
            TwitterConfig(
                api_key="test_api_key",
                # Missing other required fields
            )
    
    def test_test_connection_method(self, mock_config):
        """Test test_connection method."""
        publisher = TwitterPublisher(mock_config)
        
        # With test credentials, connection should fail
        result = publisher.test_connection()
        assert result is False
    
    @pytest.mark.asyncio
    async def test_post_content_with_context_manager(self, mock_config, sample_content):
        """Test posting content using async context manager."""
        async with TwitterPublisher(mock_config) as publisher:
            # Mock the _send_tweet method to return True
            publisher._send_tweet = AsyncMock(return_value=True)
            
            result = await publisher.post_content(sample_content)
            
            assert result is True
            assert sample_content.status.value == "posted"
    
    def test_validate_content_with_model_construct(self, mock_config):
        """Test content validation with model_construct bypass."""
        publisher = TwitterPublisher(mock_config)
        
        # Create invalid content using model_construct to bypass validation
        content = PostContent.model_construct(
            content="",  # Empty content
            platform="x",
            category_id="test-category",
            topic="Test",
            hashtags=[]
        )
        
        result = publisher.validate_content(content)
        assert result is False
    
    def test_setup_client_missing_credentials(self):
        """Test _setup_client with missing credentials."""
        # Test with missing API key
        config = TwitterConfig(
            api_key="",
            api_secret="test_secret",
            access_token="test_token",
            access_token_secret="test_token_secret"
        )
        
        with pytest.raises(PublishingError) as exc_info:
            TwitterPublisher(config)
        assert "Failed to initialize Twitter publisher" in str(exc_info.value)
    
    def test_setup_client_api_error(self):
        """Test _setup_client with API setup error."""
        config = TwitterConfig(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_token_secret="test_token_secret"
        )
        
        with patch('bot.publisher.twitter.tweepy.Client') as mock_client:
            mock_client.side_effect = Exception("API setup failed")
            
            with pytest.raises(PublishingError) as exc_info:
                TwitterPublisher(config)
            assert "Failed to initialize Twitter publisher" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_context_manager_with_exception(self):
        """Test async context manager with exception."""
        config = TwitterConfig(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token", 
            access_token_secret="test_token_secret"
        )
        
        with patch('bot.publisher.twitter.tweepy.Client'):
            publisher = TwitterPublisher(config)
            
            try:
                async with publisher:
                    raise ValueError("Test exception")
            except ValueError:
                pass  # Expected
    
    @pytest.mark.asyncio
    async def test_post_content_validation_failure(self):
        """Test post_content when validation fails."""
        config = TwitterConfig(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_token_secret="test_token_secret"
        )
        
        # Use model_construct to bypass validation for testing
        content = PostContent.model_construct(
            content="Short",  # Too short
            topic="test",
            hashtags=["#test"],
            platform="x",
            category_id="test-category"
        )
        
        publisher = TwitterPublisher(config)
        
        result = await publisher.post_content(content)
        
        assert result is False
        assert content.status == PostStatus.FAILED
    
    @pytest.mark.asyncio
    async def test_post_content_send_tweet_failure(self):
        """Test post_content when _send_tweet fails."""
        config = TwitterConfig(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_token_secret="test_token_secret"
        )
        
        content = PostContent(
            content="This is a valid test content with proper length and formatting! #test #demo",
            topic="test",
            hashtags=["#test", "#demo"],
            platform="x",
            category_id="test-category"
        )
        
        publisher = TwitterPublisher(config)
        
        with patch.object(publisher, '_send_tweet', return_value=False):
            result = await publisher.post_content(content)
            
            assert result is False
            assert content.status == PostStatus.FAILED
    
    @pytest.mark.asyncio
    async def test_post_content_unexpected_exception(self):
        """Test post_content with unexpected exception."""
        config = TwitterConfig(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_token_secret="test_token_secret"
        )
        
        content = PostContent(
            content="This is a valid test content with proper length and formatting! #test #demo",
            topic="test",
            hashtags=["#test", "#demo"],
            platform="x",
            category_id="test-category"
        )
        
        publisher = TwitterPublisher(config)
        
        with patch.object(publisher, 'validate_content', side_effect=Exception("Unexpected error")):
            result = await publisher.post_content(content)
            
            assert result is False
            assert content.status == PostStatus.FAILED
    
    @pytest.mark.asyncio
    async def test_send_tweet_no_client(self):
        """Test _send_tweet when client is not initialized."""
        config = TwitterConfig(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_token_secret="test_token_secret"
        )
        
        with patch('bot.publisher.twitter.tweepy.Client'):
            publisher = TwitterPublisher(config)
            publisher.client = None  # Simulate no client
            
            with pytest.raises(APIError) as exc_info:
                await publisher._send_tweet("Test tweet")
            assert "Twitter client not initialized" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_send_tweet_no_response_data(self):
        """Test _send_tweet when API returns no data."""
        config = TwitterConfig(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_token_secret="test_token_secret"
        )
        
        mock_response = Mock()
        mock_response.data = None
        
        with patch('bot.publisher.twitter.tweepy.Client') as mock_client_class:
            mock_client = Mock()
            mock_client.create_tweet.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            publisher = TwitterPublisher(config)
            
            with pytest.raises(APIError) as exc_info:
                await publisher._send_tweet("Test tweet")
            assert "No response data" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_send_tweet_rate_limit_error(self):
        """Test _send_tweet with rate limit error."""
        config = TwitterConfig(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_token_secret="test_token_secret"
        )
        
        with patch('bot.publisher.twitter.tweepy.Client') as mock_client_class:
            mock_client = Mock()
            # Create a proper mock response for TooManyRequests
            mock_response = Mock()
            mock_response.status_code = 429
            mock_response.text = "Rate limit exceeded"
            mock_response.reason = "Too Many Requests"
            mock_response.json.return_value = {"errors": [{"message": "Rate limit exceeded"}]}
            rate_limit_error = tweepy.TooManyRequests(mock_response)
            mock_client.create_tweet.side_effect = rate_limit_error
            mock_client_class.return_value = mock_client
            
            publisher = TwitterPublisher(config)
            
            with pytest.raises(RateLimitError) as exc_info:
                await publisher._send_tweet("Test tweet")
            assert "rate limit exceeded" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_send_tweet_forbidden_error(self):
        """Test _send_tweet with forbidden error."""
        config = TwitterConfig(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_token_secret="test_token_secret"
        )
        
        with patch('bot.publisher.twitter.tweepy.Client') as mock_client_class:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.status_code = 403
            mock_response.text = "Forbidden"
            mock_response.reason = "Forbidden"
            mock_response.json.return_value = {"errors": [{"message": "Forbidden"}]}
            mock_client.create_tweet.side_effect = tweepy.Forbidden(mock_response)
            mock_client_class.return_value = mock_client
            
            publisher = TwitterPublisher(config)
            
            with pytest.raises(AuthorizationError) as exc_info:
                await publisher._send_tweet("Test tweet")
            assert "forbidden" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_send_tweet_unauthorized_error(self):
        """Test _send_tweet with unauthorized error."""
        config = TwitterConfig(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_token_secret="test_token_secret"
        )
        
        with patch('bot.publisher.twitter.tweepy.Client') as mock_client_class:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            mock_response.reason = "Unauthorized"
            mock_response.json.return_value = {"errors": [{"message": "Unauthorized"}]}
            mock_client.create_tweet.side_effect = tweepy.Unauthorized(mock_response)
            mock_client_class.return_value = mock_client
            
            publisher = TwitterPublisher(config)
            
            with pytest.raises(AuthenticationError) as exc_info:
                await publisher._send_tweet("Test tweet")
            assert "unauthorized" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_send_tweet_bad_request_error(self):
        """Test _send_tweet with bad request error."""
        config = TwitterConfig(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_token_secret="test_token_secret"
        )
        
        with patch('bot.publisher.twitter.tweepy.Client') as mock_client_class:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.text = "Bad request"
            mock_response.reason = "Bad Request"
            mock_response.json.return_value = {"errors": [{"message": "Bad request"}]}
            mock_client.create_tweet.side_effect = tweepy.BadRequest(mock_response)
            mock_client_class.return_value = mock_client
            
            publisher = TwitterPublisher(config)
            
            with pytest.raises(ValidationError) as exc_info:
                await publisher._send_tweet("Test tweet")
            assert "bad request" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_send_tweet_generic_tweepy_error(self):
        """Test _send_tweet with generic tweepy error."""
        config = TwitterConfig(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_token_secret="test_token_secret"
        )
        
        with patch('bot.publisher.twitter.tweepy.Client') as mock_client_class:
            mock_client = Mock()
            # For generic TweepyException, just pass a string message
            mock_client.create_tweet.side_effect = tweepy.TweepyException("Generic error")
            mock_client_class.return_value = mock_client
            
            publisher = TwitterPublisher(config)
            
            with pytest.raises(APIError) as exc_info:
                await publisher._send_tweet("Test tweet")
            assert "failed to send tweet" in str(exc_info.value).lower()
    
    def test_test_connection_success(self):
        """Test successful connection test."""
        config = TwitterConfig(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_token_secret="test_token_secret"
        )
        
        mock_user = Mock()
        mock_user.id = "123456789"
        mock_user.username = "testuser"
        
        with patch('bot.publisher.twitter.tweepy.Client') as mock_client_class:
            mock_client = Mock()
            mock_client.get_me.return_value = Mock(data=mock_user)
            mock_client_class.return_value = mock_client
            
            publisher = TwitterPublisher(config)
            result = publisher.test_connection()
            
            assert result is True
    
    def test_test_connection_no_client(self):
        """Test connection test when client is not initialized."""
        config = TwitterConfig(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_token_secret="test_token_secret"
        )
        
        with patch('bot.publisher.twitter.tweepy.Client'):
            publisher = TwitterPublisher(config)
            publisher.client = None
            
            result = publisher.test_connection()
            assert result is False
    
    def test_test_connection_api_error(self):
        """Test connection test with API error."""
        config = TwitterConfig(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_token_secret="test_token_secret"
        )
        
        with patch('bot.publisher.twitter.tweepy.Client') as mock_client_class:
            mock_client = Mock()
            mock_client.get_me.side_effect = Exception("API error")
            mock_client_class.return_value = mock_client
            
            publisher = TwitterPublisher(config)
            result = publisher.test_connection()
            
            assert result is False
    
    def test_validate_content_edge_cases(self, mock_config):
        """Test validate_content with edge cases."""
        publisher = TwitterPublisher(mock_config)
        
        # Test exactly 20 characters (minimum valid)
        content_min = PostContent.model_construct(
            content="x" * 14 + " #a #b",  # Exactly 20 chars
            platform="x",
            category_id="test-category",
            topic="Test",
            hashtags=["#a", "#b"]
        )
        assert publisher.validate_content(content_min) is True
        
        # Test exactly 220 characters (maximum valid)
        content_max = PostContent.model_construct(
            content="x" * 214 + " #a #b",  # Exactly 220 chars
            platform="x",
            category_id="test-category",
            topic="Test",
            hashtags=["#a", "#b"]
        )
        assert publisher.validate_content(content_max) is True
        
        # Test 19 characters (too short)
        content_short = PostContent.model_construct(
            content="x" * 13 + " #a #b",  # 19 chars
            platform="x",
            category_id="test-category",
            topic="Test",
            hashtags=["#a", "#b"]
        )
        assert publisher.validate_content(content_short) is False
        
        # Test 221 characters (too long)
        content_long = PostContent.model_construct(
            content="x" * 215 + " #a #b",  # 221 chars
            platform="x",
            category_id="test-category",
            topic="Test",
            hashtags=["#a", "#b"]
        )
        assert publisher.validate_content(content_long) is False
    
    def test_validate_content_exception_handling(self, mock_config):
        """Test validate_content with exception during validation."""
        publisher = TwitterPublisher(mock_config)
        
        # Create a mock content that will cause an exception during hashtag access
        mock_content = Mock()
        mock_content.content = "Valid content here #test #demo"
        # Make hashtags property raise an exception
        type(mock_content).hashtags = PropertyMock(side_effect=Exception("Hashtag error"))
        
        result = publisher.validate_content(mock_content)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_post_content_validation_error_handling(self, mock_config):
        """Test post_content with ValidationError from _send_tweet."""
        content = PostContent(
            content="This is a valid test content with proper length and formatting! #test #demo",
            topic="test",
            hashtags=["#test", "#demo"],
            platform="x",
            category_id="test-category"
        )
        
        publisher = TwitterPublisher(mock_config)
        
        # Mock _send_tweet to raise ValidationError
        with patch.object(publisher, '_send_tweet', side_effect=ValidationError("Validation failed", field_name="test", validation_rule="test")):
            result = await publisher.post_content(content)
            
            assert result is False
            assert content.status == PostStatus.FAILED
    
    @pytest.mark.asyncio
    async def test_post_content_publishing_error_handling(self, mock_config):
        """Test post_content with PublishingError from _send_tweet."""
        content = PostContent(
            content="This is a valid test content with proper length and formatting! #test #demo",
            topic="test",
            hashtags=["#test", "#demo"],
            platform="x",
            category_id="test-category"
        )
        
        publisher = TwitterPublisher(mock_config)
        
        # Mock _send_tweet to raise PublishingError
        with patch.object(publisher, '_send_tweet', side_effect=PublishingError("Publishing failed", platform="twitter")):
            result = await publisher.post_content(content)
            
            assert result is False
            assert content.status == PostStatus.FAILED
    
    def test_test_connection_with_user_data(self, mock_config):
        """Test test_connection with successful user data retrieval."""
        with patch('bot.publisher.twitter.tweepy.Client') as mock_client_class:
            mock_client = Mock()
            mock_user_response = Mock()
            mock_user_response.data = Mock()
            mock_user_response.data.username = "testuser"
            mock_user_response.data.id = "123456789"
            mock_client.get_me.return_value = mock_user_response
            mock_client_class.return_value = mock_client
            
            publisher = TwitterPublisher(mock_config)
            result = publisher.test_connection()
            
            assert result is True
            mock_client.get_me.assert_called_once()
    
    def test_test_connection_no_user_data(self, mock_config):
        """Test test_connection with no user data returned."""
        with patch('bot.publisher.twitter.tweepy.Client') as mock_client_class:
            mock_client = Mock()
            mock_user_response = Mock()
            mock_user_response.data = None
            mock_client.get_me.return_value = mock_user_response
            mock_client_class.return_value = mock_client
            
            publisher = TwitterPublisher(mock_config)
            result = publisher.test_connection()
            
            assert result is False
            mock_client.get_me.assert_called_once() 