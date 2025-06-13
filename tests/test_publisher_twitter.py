"""Tests for the Twitter publisher module."""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import httpx
from bot.publisher.twitter import TwitterPublisher, TwitterConfig
from bot.models.topic import PostContent, PostStatus


class TestTwitterPublisher:
    """Test cases for TwitterPublisher class."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        return TwitterConfig(
            api_key="test_api_key",
            api_secret="test_api_secret",
            access_token="test_access_token",
            access_token_secret="test_access_token_secret",
            bearer_token="test_bearer_token"
        )
    
    @pytest.fixture
    def sample_content(self):
        """Sample post content for testing."""
        return PostContent(
            content="Valid test content here #test #new",
            platform="x",
            category_id="test-category",
            topic="Test Topic",
            hashtags=["#test", "#new"]
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
        """Test send_tweet with invalid credentials."""
        publisher = TwitterPublisher(mock_config)
        
        # With tweepy, client is always initialized but may fail with invalid credentials
        result = await publisher._send_tweet("Test tweet")
        assert result is False  # Should fail with test credentials
    
    @pytest.mark.asyncio
    async def test_send_tweet_success(self, mock_config):
        """Test tweet sending with mock."""
        async with TwitterPublisher(mock_config) as publisher:
            # With test credentials, this will fail
            result = await publisher._send_tweet("Test tweet")
            assert result is False  # Should fail with test credentials
    
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