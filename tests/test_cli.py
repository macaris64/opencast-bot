"""
Tests for CLI module in OpenCast Bot.

This module tests the CLI interface and commands
defined in bot/cli.py.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typer.testing import CliRunner
import pytest

from bot.cli import app
from bot.config import Config
from bot.models.category import Category, CategoryTopic, CategoryEntry, CategoryMetadata


class TestCLI:
    """Test cases for CLI commands."""
    
    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()
    
    @pytest.fixture
    def sample_category_data(self):
        """Create sample category data for testing."""
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
                            "content": "x" * 169 + " #test #content",  # 180 chars
                            "metadata": {
                                "length": 180,
                                "source": "test",
                                "tags": ["#test", "#content"]
                            }
                        }
                    ]
                }
            ]
        }
    
    def test_version_command(self, runner):
        """Test version command."""
        result = runner.invoke(app, ["version"])
        
        assert result.exit_code == 0
        assert "OpenCast Bot" in result.stdout
        assert "0.1.0" in result.stdout
    
    def test_validate_config_command_success(self, runner):
        """Test validate-config command with valid configuration."""
        with patch.dict('os.environ', {
            'OPENAI_API_KEY': 'test-key',
            'DRY_RUN': 'true'
        }):
            result = runner.invoke(app, ["validate-config"])
            
            assert result.exit_code == 0
            assert "Configuration is valid" in result.stdout
    
    def test_validate_config_command_with_platforms(self, runner):
        """Test validate-config command with platform configurations."""
        with patch.dict('os.environ', {
            'OPENAI_API_KEY': 'test-key',
            'TWITTER_ENABLED': 'true',
            'TWITTER_API_KEY': 'twitter-key',
            'TWITTER_API_SECRET': 'twitter-secret',
            'TWITTER_ACCESS_TOKEN': 'twitter-token',
            'TWITTER_ACCESS_TOKEN_SECRET': 'twitter-token-secret',
            'TELEGRAM_ENABLED': 'true',
            'TELEGRAM_BOT_TOKEN': 'telegram-token',
            'TELEGRAM_CHAT_ID': 'telegram-chat-id'
        }):
            result = runner.invoke(app, ["validate-config"])
            
            assert result.exit_code == 0
            assert "Configuration is valid" in result.stdout
            assert "twitter" in result.stdout.lower()
            assert "telegram" in result.stdout.lower()
    
    def test_list_categories_command_empty(self, runner):
        """Test list-categories command with no categories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict('os.environ', {'DATA_DIRECTORY': temp_dir}):
                result = runner.invoke(app, ["list-categories"])
                
                assert result.exit_code == 0
                assert "No categories found" in result.stdout
    
    def test_list_categories_command_with_categories(self, runner, sample_category_data):
        """Test list-categories command with existing categories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a sample category file
            category_file = Path(temp_dir) / "test-category.json"
            with open(category_file, 'w') as f:
                json.dump(sample_category_data, f)
            
            with patch.dict('os.environ', {'DATA_DIRECTORY': temp_dir}):
                result = runner.invoke(app, ["list-categories"])
                
                assert result.exit_code == 0
                assert "test-category" in result.stdout
                assert "Test Category" in result.stdout
    
    def test_show_category_command_existing(self, runner, sample_category_data):
        """Test show-category command with existing category."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a sample category file
            category_file = Path(temp_dir) / "test-category.json"
            with open(category_file, 'w') as f:
                json.dump(sample_category_data, f)
            
            with patch.dict('os.environ', {'DATA_DIRECTORY': temp_dir}):
                result = runner.invoke(app, ["show-category", "test-category"])
                
                assert result.exit_code == 0
                assert "Test Category" in result.stdout
                assert "Test Topic" in result.stdout
                assert "1 entries" in result.stdout
    
    def test_show_category_command_nonexistent(self, runner):
        """Test show-category command with non-existent category."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict('os.environ', {'DATA_DIRECTORY': temp_dir}):
                result = runner.invoke(app, ["show-category", "nonexistent"])
                
                assert result.exit_code == 1
                assert "Category 'nonexistent' not found" in result.stdout
    
    @patch('bot.cli.ContentGenerator')
    @patch('bot.cli.JSONCategoryManager')
    def test_generate_command_success(self, mock_manager, mock_generator, runner, sample_category_data):
        """Test successful generate command."""
        # Setup mocks
        mock_category = Category(**sample_category_data)
        mock_manager_instance = Mock()
        mock_manager_instance.load_category.return_value = mock_category
        mock_manager_instance.save_category.return_value = None
        mock_manager.return_value = mock_manager_instance

        mock_entry = CategoryEntry(
            content="This is a test content with proper length and formatting! #test #new",
            metadata=CategoryMetadata(length=70, source="openai", tags=["#test", "#new"])
        )
        mock_generator_instance = Mock()
        # Make generate_content return a coroutine
        async def mock_generate_content(*args, **kwargs):
            return mock_entry
        mock_generator_instance.generate_content = mock_generate_content
        mock_generator.return_value = mock_generator_instance

        result = runner.invoke(app, ["generate", "test-category", "New Topic"])

        assert result.exit_code == 0
        assert "Content generated successfully" in result.stdout

    @patch('bot.cli.ContentGenerator')
    @patch('bot.cli.JSONCategoryManager')
    def test_generate_command_existing_content(self, mock_manager, mock_generator, runner, sample_category_data):
        """Test generate command when content already exists."""
        # Setup mocks
        mock_category = Category(**sample_category_data)
        mock_manager_instance = Mock()
        mock_manager_instance.load_category.return_value = mock_category
        mock_manager.return_value = mock_manager_instance

        mock_generator_instance = Mock()
        # Make generate_content return a coroutine that returns None
        async def mock_generate_content(*args, **kwargs):
            return None
        mock_generator_instance.generate_content = mock_generate_content
        mock_generator.return_value = mock_generator_instance

        result = runner.invoke(app, ["generate", "test-category", "Test Topic"])

        assert result.exit_code == 0
        assert "Content already exists for this topic" in result.stdout
    
    @patch('bot.cli.ContentGenerator')
    @patch('bot.cli.JSONCategoryManager')
    def test_generate_command_category_not_found(self, mock_manager, mock_generator, runner):
        """Test generate command with non-existent category."""
        # Setup mocks
        mock_manager_instance = Mock()
        mock_manager_instance.load_category.side_effect = FileNotFoundError()
        mock_manager.return_value = mock_manager_instance
        
        result = runner.invoke(app, ["generate", "nonexistent", "Topic"])
        
        assert result.exit_code == 1
        assert "Category 'nonexistent' not found" in result.stdout
    
    @patch('bot.cli.Config')
    @patch('bot.publisher.twitter.TwitterPublisher')
    @patch('bot.publisher.telegram.TelegramPublisher')
    @patch('bot.cli.JSONCategoryManager')
    def test_post_command_success(self, mock_manager, mock_telegram, mock_twitter, mock_config, runner, sample_category_data):
        """Test post command with successful posting."""
        # Setup config mock
        mock_config_instance = Mock()
        mock_config_instance.dry_run = False
        mock_config_instance.get_enabled_platforms.return_value = ["twitter", "telegram"]
        
        # Mock Twitter config properties
        mock_config_instance.twitter_api_key = "test_key"
        mock_config_instance.twitter_api_secret = "test_secret"
        mock_config_instance.twitter_access_token = "test_token"
        mock_config_instance.twitter_access_token_secret = "test_token_secret"
        mock_config_instance.twitter_bearer_token = "test_bearer"
        
        # Mock Telegram config properties
        mock_config_instance.telegram_bot_token = "test_bot_token"
        mock_config_instance.telegram_chat_id = "test_chat_id"
        mock_config_instance.telegram_parse_mode = "HTML"
        
        mock_config.return_value = mock_config_instance
        
        # Setup mocks
        mock_category = Category(**sample_category_data)
        mock_manager_instance = Mock()
        mock_manager_instance.load_category.return_value = mock_category
        mock_manager.return_value = mock_manager_instance
        
        # Mock publisher instances with async context manager support
        mock_twitter_instance = Mock()
        mock_twitter_instance.post_content = AsyncMock(return_value=True)
        mock_twitter_instance.__aenter__ = AsyncMock(return_value=mock_twitter_instance)
        mock_twitter_instance.__aexit__ = AsyncMock(return_value=None)
        mock_twitter.return_value = mock_twitter_instance
        
        mock_telegram_instance = Mock()
        mock_telegram_instance.post_content = AsyncMock(return_value=True)
        mock_telegram_instance.__aenter__ = AsyncMock(return_value=mock_telegram_instance)
        mock_telegram_instance.__aexit__ = AsyncMock(return_value=None)
        mock_telegram.return_value = mock_telegram_instance
        
        result = runner.invoke(app, ["post", "test-category", "Test Topic"])
        
        assert result.exit_code == 0
        assert "Posted successfully" in result.stdout
    
    @patch('bot.cli.JSONCategoryManager')
    def test_post_command_no_content(self, mock_manager, runner):
        """Test post command when no content exists for topic."""
        # Setup mocks
        empty_category_data = {
            "category_id": "test-category",
            "name": "Test Category",
            "description": "Test description",
            "prompt_template": "Generate content about {topic}.",
            "language": "en",
            "topics": []
        }
        mock_category = Category(**empty_category_data)
        mock_manager_instance = Mock()
        mock_manager_instance.load_category.return_value = mock_category
        mock_manager.return_value = mock_manager_instance
        
        result = runner.invoke(app, ["post", "test-category", "Nonexistent Topic"])
        
        assert result.exit_code == 1
        assert "No content found" in result.stdout
    
    def test_post_command_dry_run(self, runner, sample_category_data):
        """Test post command in dry-run mode."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a sample category file
            category_file = Path(temp_dir) / "test-category.json"
            with open(category_file, 'w') as f:
                json.dump(sample_category_data, f)
            
            with patch.dict('os.environ', {
                'DATA_DIRECTORY': temp_dir,
                'DRY_RUN': 'true'
            }):
                result = runner.invoke(app, ["post", "test-category", "Test Topic"])
                
                assert result.exit_code == 0
                assert "DRY RUN" in result.stdout
    
    def test_list_topics_command(self, runner, sample_category_data):
        """Test list-topics command."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a sample category file
            category_file = Path(temp_dir) / "test-category.json"
            with open(category_file, 'w') as f:
                json.dump(sample_category_data, f)
            
            with patch.dict('os.environ', {'DATA_DIRECTORY': temp_dir}):
                result = runner.invoke(app, ["list-topics", "test-category"])
                
                assert result.exit_code == 0
                assert "Test Topic" in result.stdout
                assert "1 entries" in result.stdout
    
    def test_list_topics_command_category_not_found(self, runner):
        """Test list-topics command with non-existent category."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict('os.environ', {'DATA_DIRECTORY': temp_dir}):
                result = runner.invoke(app, ["list-topics", "nonexistent"])
                
                assert result.exit_code == 1
                assert "Category 'nonexistent' not found" in result.stdout
    
    def test_help_command(self, runner):
        """Test help command."""
        result = runner.invoke(app, ["--help"])
        
        assert result.exit_code == 0
        assert "OpenCast Bot" in result.stdout
        assert "generate" in result.stdout
        assert "post" in result.stdout
        assert "list-categories" in result.stdout
    
    def test_invalid_command(self, runner):
        """Test invalid command."""
        result = runner.invoke(app, ["invalid-command"])
        
        assert result.exit_code != 0
    
    @patch('bot.cli.Config')
    def test_config_loading_error(self, mock_config, runner):
        """Test CLI behavior when config loading fails."""
        mock_config.side_effect = Exception("Config error")
        
        result = runner.invoke(app, ["version"])
        
        # Should still work for version command as it doesn't need config
        assert result.exit_code == 0
    
    def test_generate_command_missing_arguments(self, runner):
        """Test generate command with missing arguments."""
        result = runner.invoke(app, ["generate"])
        
        assert result.exit_code != 0
        # Typer outputs error messages to stderr, not stdout
        assert "Missing argument" in result.stderr or "Usage:" in result.stderr or result.exit_code == 2
    
    def test_post_command_missing_arguments(self, runner):
        """Test post command with missing arguments."""
        result = runner.invoke(app, ["post"])
        
        assert result.exit_code != 0
        # Typer outputs error messages to stderr, not stdout
        assert "Missing argument" in result.stderr or "Usage:" in result.stderr or result.exit_code == 2
    
    @patch('bot.cli.Config')
    def test_test_twitter_command_success(self, mock_config, runner):
        """Test test-twitter command with valid config."""
        mock_config_instance = Mock()
        mock_config_instance.validate_twitter_config.return_value = True
        mock_config_instance.twitter_api_key = "test_key"
        mock_config_instance.twitter_api_secret = "test_secret"
        mock_config_instance.twitter_access_token = "test_token"
        mock_config_instance.twitter_access_token_secret = "test_token_secret"
        mock_config_instance.twitter_bearer_token = "test_bearer"
        mock_config.return_value = mock_config_instance
        
        with patch('bot.publisher.twitter.TwitterPublisher') as mock_publisher:
            mock_publisher_instance = Mock()
            mock_publisher_instance.test_connection.return_value = True
            mock_publisher.return_value = mock_publisher_instance
            
            result = runner.invoke(app, ["test-twitter"])
            
            assert result.exit_code == 0
            assert "Twitter API connection successful" in result.stdout
    
    @patch('bot.cli.Config')
    def test_test_twitter_command_invalid_config(self, mock_config, runner):
        """Test test-twitter command with invalid config."""
        mock_config_instance = Mock()
        mock_config_instance.validate_twitter_config.return_value = False
        mock_config.return_value = mock_config_instance
        
        result = runner.invoke(app, ["test-twitter"])
        
        assert result.exit_code == 1
        assert "Twitter configuration is invalid" in result.stdout
    
    @patch('bot.cli.Config')
    @patch('bot.cli.JSONCategoryManager')
    def test_generate_command_generation_error(self, mock_manager, mock_config, runner, sample_category_data):
        """Test generate command when generation fails."""
        # Setup config mock
        mock_config_instance = Mock()
        mock_config.return_value = mock_config_instance
        
        # Setup mocks
        mock_category = Category(**sample_category_data)
        mock_manager_instance = Mock()
        mock_manager_instance.load_category.return_value = mock_category
        mock_manager.return_value = mock_manager_instance
        
        with patch('bot.cli.ContentGenerator') as mock_generator:
            mock_generator_instance = Mock()
            # Make generate_content raise an exception
            async def mock_generate_content(*args, **kwargs):
                raise Exception("Generation failed")
            mock_generator_instance.generate_content = mock_generate_content
            mock_generator.return_value = mock_generator_instance
            
            result = runner.invoke(app, ["generate", "test-category", "New Topic"])
            
            assert result.exit_code == 1
            assert "Error:" in result.stdout
    
    @patch('bot.cli.Config')
    @patch('bot.publisher.twitter.TwitterPublisher')
    @patch('bot.publisher.telegram.TelegramPublisher')
    @patch('bot.cli.JSONCategoryManager')
    def test_post_command_partial_success(self, mock_manager, mock_telegram, mock_twitter, mock_config, runner, sample_category_data):
        """Test post command with partial success (one platform fails)."""
        # Setup config mock
        mock_config_instance = Mock()
        mock_config_instance.dry_run = False
        mock_config_instance.get_enabled_platforms.return_value = ["twitter", "telegram"]
        
        # Mock Twitter config properties
        mock_config_instance.twitter_api_key = "test_key"
        mock_config_instance.twitter_api_secret = "test_secret"
        mock_config_instance.twitter_access_token = "test_token"
        mock_config_instance.twitter_access_token_secret = "test_token_secret"
        mock_config_instance.twitter_bearer_token = "test_bearer"
        
        # Mock Telegram config properties
        mock_config_instance.telegram_bot_token = "test_bot_token"
        mock_config_instance.telegram_chat_id = "test_chat_id"
        mock_config_instance.telegram_parse_mode = "HTML"
        
        mock_config.return_value = mock_config_instance
        
        # Setup mocks
        mock_category = Category(**sample_category_data)
        mock_manager_instance = Mock()
        mock_manager_instance.load_category.return_value = mock_category
        mock_manager.return_value = mock_manager_instance
        
        # Mock publisher instances - Twitter succeeds, Telegram fails
        mock_twitter_instance = Mock()
        mock_twitter_instance.post_content = AsyncMock(return_value=True)
        mock_twitter_instance.__aenter__ = AsyncMock(return_value=mock_twitter_instance)
        mock_twitter_instance.__aexit__ = AsyncMock(return_value=None)
        mock_twitter.return_value = mock_twitter_instance
        
        mock_telegram_instance = Mock()
        mock_telegram_instance.post_content = AsyncMock(return_value=False)  # Fails
        mock_telegram_instance.__aenter__ = AsyncMock(return_value=mock_telegram_instance)
        mock_telegram_instance.__aexit__ = AsyncMock(return_value=None)
        mock_telegram.return_value = mock_telegram_instance
        
        result = runner.invoke(app, ["post", "test-category", "Test Topic"])
        
        assert result.exit_code == 0  # Should succeed if at least one platform works
        assert "Posted successfully to at least one platform" in result.stdout 