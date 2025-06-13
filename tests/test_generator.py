"""
Tests for content generator module in OpenCast Bot.

This module tests the ContentGenerator class and content generation logic
defined in bot/generator.py.
"""

from unittest.mock import Mock, patch, AsyncMock
import pytest

from bot.generator import ContentGenerator, ContentGenerationError
from bot.config import Config
from bot.models.category import Category, CategoryEntry, CategoryTopic, CategoryMetadata


class TestContentGenerator:
    """Test cases for ContentGenerator class."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock config for testing."""
        config = Mock(spec=Config)
        config.openai_api_key = "test-api-key"
        config.openai_model = "gpt-3.5-turbo"
        config.openai_max_tokens = 100
        config.openai_temperature = 0.7
        config.content_min_length = 180
        config.content_max_length = 200
        config.required_hashtag_count = 2
        return config
    
    @pytest.fixture
    def generator(self):
        """Create a ContentGenerator instance for testing."""
        # Create a real config with proper attributes
        config = Config()
        return ContentGenerator(config)
    
    @pytest.fixture
    def sample_category(self):
        """Create a sample category for testing."""
        return Category(
            category_id="test-category",
            name="Test Category",
            description="Test description",
            prompt_template=None,  # Will use global default
            language="en"
        )
    
    def test_generator_initialization(self, mock_config):
        """Test ContentGenerator initialization."""
        with patch('bot.generator.openai') as mock_openai:
            generator = ContentGenerator(mock_config)
            
            assert generator.config == mock_config
            assert hasattr(generator, 'logger')
            mock_openai.api_key = mock_config.openai_api_key
    
    @pytest.mark.asyncio
    async def test_generate_content_existing_content(self, generator, sample_category):
        """Test that generator returns None when content already exists."""
        # Add existing content for the topic
        existing_entry = CategoryEntry(
            content="Existing content #test #existing",
            metadata=CategoryMetadata(length=30, source="test", tags=["#test", "#existing"])
        )
        topic = CategoryTopic(topic="Test Topic", entries=[existing_entry])
        sample_category.topics = [topic]
        
        result = await generator.generate_content(sample_category, "Test Topic")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_generate_content_success(self, generator, sample_category):
        """Test successful content generation."""
        valid_content = "This is a test content with proper length and formatting! #test #content"  # Valid length
        
        with patch.object(generator, '_call_openai_api', return_value=valid_content) as mock_api:
            result = await generator.generate_content(sample_category, "New Topic")
            
            assert result is not None
            assert isinstance(result, CategoryEntry)
            assert "#test" in result.content
            assert "#content" in result.content
            mock_api.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_content_api_failure(self, generator, sample_category):
        """Test content generation when API call fails."""
        from bot.generator import APIError
        
        with patch.object(generator, '_call_openai_api', side_effect=APIError("API failed")):
            result = await generator.generate_content(sample_category, "New Topic")
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_generate_content_validation_failure(self, generator, sample_category):
        """Test content generation when validation fails."""
        invalid_content = "Too short"  # Less than 20 chars
        
        with patch.object(generator, '_call_openai_api', return_value=invalid_content):
            result = await generator.generate_content(sample_category, "New Topic")
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_generate_content_exception_handling(self, generator, sample_category):
        """Test content generation with exception handling."""
        with patch.object(generator, '_call_openai_api', side_effect=Exception("Test error")):
            result = await generator.generate_content(sample_category, "New Topic")
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_call_openai_api_placeholder(self, generator):
        """Test OpenAI API call placeholder implementation."""
        # Temporarily set placeholder key
        original_key = generator.config.openai_api_key
        generator.config.openai_api_key = "sk-placeholder-for-development"
        
        prompt_template = "Generate content about {topic}. Include hashtags."
        topic = "Test Topic"

        result = await generator._call_openai_api(prompt_template, topic)
        
        # Restore original key
        generator.config.openai_api_key = original_key
        
        assert result is not None
        assert "Test Topic" in result
        assert "#placeholder" in result
        assert "#demo" in result
    
    def test_validate_content_valid_length(self, generator, sample_category):
        """Test content validation with valid length."""
        valid_content = "This is a valid content with proper length and formatting! #test #valid"

        with patch.object(generator, '_extract_hashtags', return_value=["#test", "#valid"]):
            result = generator._validate_content(valid_content, sample_category)
            assert result is True

    def test_validate_content_too_short(self, generator, sample_category):
        """Test content validation with too short content."""
        short_content = "Short"  # Less than 20 chars

        result = generator._validate_content(short_content, sample_category)
        assert result is False

    def test_validate_content_too_long(self, generator, sample_category):
        """Test content validation with too long content."""
        long_content = "x" * 250  # More than 220 chars

        result = generator._validate_content(long_content, sample_category)
        assert result is False

    def test_validate_content_wrong_hashtag_count(self, generator, sample_category):
        """Test content validation with wrong hashtag count."""
        valid_content = "This is a valid content with proper length and formatting!"

        # Test with 1 hashtag (should be 2)
        with patch.object(generator, '_extract_hashtags', return_value=["#only"]):
            result = generator._validate_content(valid_content, sample_category)
            assert result is False

        # Test with 3 hashtags (should be 2)
        with patch.object(generator, '_extract_hashtags', return_value=["#one", "#two", "#three"]):
            result = generator._validate_content(valid_content, sample_category)
            assert result is False
    
    def test_extract_hashtags_single_word(self, generator):
        """Test hashtag extraction with single word hashtags."""
        content = "Some content with #hashtag and #another hashtag"
        
        result = generator._extract_hashtags(content)
        
        assert result == ["#hashtag", "#another"]
    
    def test_extract_hashtags_no_hashtags(self, generator):
        """Test hashtag extraction with no hashtags."""
        content = "Content without any hashtags"
        
        result = generator._extract_hashtags(content)
        
        assert result == []
    
    def test_extract_hashtags_complex_pattern(self, generator):
        """Test hashtag extraction with complex patterns."""
        content = "Content with #CamelCase #under_score and #numbers123 hashtags"
        
        result = generator._extract_hashtags(content)
        
        assert "#CamelCase" in result
        assert "#under_score" in result
        assert "#numbers123" in result
        assert len(result) == 3
    
    def test_extract_hashtags_edge_cases(self, generator):
        """Test hashtag extraction edge cases."""
        # Hashtag at start and end
        content = "#start content in middle #end"
        result = generator._extract_hashtags(content)
        assert result == ["#start", "#end"]
        
        # Multiple consecutive hashtags
        content = "content #first#second #third"
        result = generator._extract_hashtags(content)
        assert "#first" in result
        assert "#second" in result
        assert "#third" in result
    
    @pytest.mark.asyncio
    async def test_openai_api_format_prompt(self, generator):
        """Test that prompt is correctly formatted with topic."""
        # Temporarily set placeholder key to avoid real API call
        original_key = generator.config.openai_api_key
        generator.config.openai_api_key = "sk-placeholder-for-development"
        
        prompt_template = "Write about {topic} in a professional tone."
        topic = "Unit Testing"

        result = await generator._call_openai_api(prompt_template, topic)
        
        # Restore original key
        generator.config.openai_api_key = original_key
        
        assert result is not None
        assert "Unit Testing" in result
        assert "#placeholder" in result
        assert "#demo" in result
    
    @pytest.mark.asyncio
    async def test_call_openai_api_real_key(self, generator):
        """Test OpenAI API call with real key format."""
        # Test with real-looking key format
        original_key = generator.config.openai_api_key
        generator.config.openai_api_key = "sk-test123456789"
        
        prompt_template = "Generate content about {topic}."
        topic = "Test Topic"
        
        with patch('openai.AsyncOpenAI') as mock_openai:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message = Mock()
            mock_response.choices[0].message.content = "Generated content #test #api"
            
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client
            
            result = await generator._call_openai_api(prompt_template, topic)
            
            # Restore original key
            generator.config.openai_api_key = original_key
            
            assert result == "Generated content #test #api"
            mock_client.chat.completions.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_call_openai_api_exception(self, generator):
        """Test OpenAI API call with exception."""
        from bot.generator import APIError
        
        original_key = generator.config.openai_api_key
        generator.config.openai_api_key = "sk-test123456789"
        
        prompt_template = "Generate content about {topic}."
        topic = "Test Topic"
        
        with patch('openai.AsyncOpenAI') as mock_openai:
            mock_client = Mock()
            mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API Error"))
            mock_openai.return_value = mock_client
            
            with pytest.raises(APIError):
                await generator._call_openai_api(prompt_template, topic)
        
        # Restore original key
        generator.config.openai_api_key = original_key
    
    def test_adjust_content_length_no_adjustment_needed(self, generator, sample_category):
        """Test content length adjustment when no adjustment is needed."""
        content = "Perfect length content with hashtags #test #perfect"
        
        result = generator._adjust_content_length(content, sample_category)
        
        assert result == content
    
    def test_adjust_content_length_too_long(self, generator, sample_category):
        """Test content length adjustment when content is too long."""
        # Create a very long content
        long_content = "This is a very long content that exceeds the maximum length limit and needs to be truncated properly while preserving hashtags and maintaining readability for users who will read this content on social media platforms #test #long"
        
        result = generator._adjust_content_length(long_content, sample_category)
        
        # Should be shorter than original but still contain hashtags
        assert len(result) < len(long_content)
        assert "#test" in result
        assert "#long" in result 