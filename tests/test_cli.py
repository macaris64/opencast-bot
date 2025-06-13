"""
Tests for CLI module.

This module tests the command-line interface functionality including
category management, content generation, and posting commands.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

import pytest
from typer.testing import CliRunner

from bot.cli import app
from bot.models.category import Category, CategoryEntry, CategoryMetadata


class TestCLI:
    """Test cases for CLI commands."""
    
    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()
    
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
                            "content": "This is a test content with proper length and formatting! #test #new",
                            "metadata": {
                                "length": 70,
                                "source": "openai",
                                "tags": ["#test", "#new"],
                                "timestamp": "2024-01-01T00:00:00Z"
                            }
                        }
                    ]
                }
            ]
        }
    
    def test_version_command(self, runner):
        """Test version command."""
        with patch('bot.cli.console') as mock_console:
            result = runner.invoke(app, ["version"])
            
            assert result.exit_code == 0
            mock_console.print.assert_called()
            # Check that version was printed
            call_args = mock_console.print.call_args[0][0]
            assert "OpenCast Bot version" in call_args
    
    @patch('bot.cli.Config')
    def test_validate_config_command_success(self, mock_config, runner):
        """Test validate-config command with valid configuration."""
        mock_config_instance = Mock()
        mock_config_instance.openai_api_key = "sk-real-key"
        mock_config_instance.get_enabled_platforms.return_value = ["twitter", "telegram"]
        mock_config.return_value = mock_config_instance
        
        with patch('bot.cli.console') as mock_console:
            result = runner.invoke(app, ["validate-config"])
            
            assert result.exit_code == 0
            # Check that success messages were printed
            print_calls = [call[0][0] for call in mock_console.print.call_args_list]
            assert any("OpenAI API key configured" in call for call in print_calls)
            assert any("Configuration is valid" in call for call in print_calls)
    
    @patch('bot.cli.Config')
    def test_validate_config_command_with_platforms(self, mock_config, runner):
        """Test validate-config command with platform information."""
        mock_config_instance = Mock()
        mock_config_instance.openai_api_key = "sk-real-key"
        mock_config_instance.get_enabled_platforms.return_value = ["twitter"]
        mock_config.return_value = mock_config_instance
        
        with patch('bot.cli.console') as mock_console:
            result = runner.invoke(app, ["validate-config"])
            
            assert result.exit_code == 0
            print_calls = [call[0][0] for call in mock_console.print.call_args_list]
            assert any("twitter" in call for call in print_calls)
    
    @patch('bot.cli.Config')
    @patch('bot.cli.JSONCategoryManager')
    def test_list_categories_command_empty(self, mock_manager, mock_config, runner):
        """Test list-categories command with no categories."""
        mock_config_instance = Mock()
        mock_config_instance.categories_directory = "categories"
        mock_config.return_value = mock_config_instance
        
        mock_manager_instance = Mock()
        mock_manager_instance.list_categories.return_value = []
        mock_manager.return_value = mock_manager_instance
        
        with patch('bot.cli.console') as mock_console:
            result = runner.invoke(app, ["list-categories"])
            
            assert result.exit_code == 0
            print_calls = [call[0][0] for call in mock_console.print.call_args_list]
            assert any("No categories found" in call for call in print_calls)
    
    @patch('bot.cli.Config')
    @patch('bot.cli.JSONCategoryManager')
    def test_list_categories_command_with_categories(self, mock_manager, mock_config, runner, sample_category_data):
        """Test list-categories command with existing categories."""
        mock_config_instance = Mock()
        mock_config_instance.categories_directory = "categories"
        mock_config.return_value = mock_config_instance
        
        mock_category = Category(**sample_category_data)
        mock_manager_instance = Mock()
        mock_manager_instance.list_categories.return_value = ["test-category"]
        mock_manager_instance.load_category.return_value = mock_category
        mock_manager.return_value = mock_manager_instance
        
        with patch('bot.cli.console') as mock_console:
            result = runner.invoke(app, ["list-categories"])
            
            assert result.exit_code == 0
            print_calls = [call[0][0] for call in mock_console.print.call_args_list]
            assert any("test-category" in call for call in print_calls)
            assert any("Test Category" in call for call in print_calls)
    
    @patch('bot.cli.Config')
    @patch('bot.cli.JSONCategoryManager')
    def test_show_category_command_existing(self, mock_manager, mock_config, runner, sample_category_data):
        """Test show-category command with existing category."""
        mock_config_instance = Mock()
        mock_config_instance.categories_directory = "categories"
        mock_config.return_value = mock_config_instance
        
        mock_category = Category(**sample_category_data)
        mock_manager_instance = Mock()
        mock_manager_instance.load_category.return_value = mock_category
        mock_manager.return_value = mock_manager_instance
        
        with patch('bot.cli.console') as mock_console:
            result = runner.invoke(app, ["show-category", "test-category"])
            
            assert result.exit_code == 0
            print_calls = [call[0][0] for call in mock_console.print.call_args_list]
            assert any("Test Category" in call for call in print_calls)
            assert any("Test Topic" in call for call in print_calls)
            assert any("1 entries" in call for call in print_calls)
    
    @patch('bot.cli.Config')
    @patch('bot.cli.JSONCategoryManager')
    def test_show_category_command_nonexistent(self, mock_manager, mock_config, runner):
        """Test show-category command with non-existent category."""
        mock_config_instance = Mock()
        mock_config_instance.categories_directory = "categories"
        mock_config.return_value = mock_config_instance
        
        mock_manager_instance = Mock()
        mock_manager_instance.load_category.side_effect = FileNotFoundError()
        mock_manager.return_value = mock_manager_instance
        
        with patch('bot.cli.console') as mock_console:
            result = runner.invoke(app, ["show-category", "nonexistent"])
            
            assert result.exit_code == 1
            print_calls = [call[0][0] for call in mock_console.print.call_args_list]
            assert any("Category 'nonexistent' not found" in call for call in print_calls)
    
    @patch('bot.cli.Config')
    @patch('bot.cli.ContentGenerator')
    @patch('bot.cli.JSONCategoryManager')
    def test_generate_command_success(self, mock_manager, mock_generator, mock_config, runner, sample_category_data):
        """Test successful generate command."""
        # Setup config mock
        mock_config_instance = Mock()
        mock_config_instance.categories_directory = "categories"
        mock_config.return_value = mock_config_instance
        
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

        with patch('bot.cli.console') as mock_console:
            # Provide 'y' input for confirmation prompt
            result = runner.invoke(app, ["generate", "test-category", "New Topic"], input="y\n")

            assert result.exit_code == 0
            print_calls = [call[0][0] for call in mock_console.print.call_args_list]
            assert any("Content generated successfully" in call for call in print_calls)

    @patch('bot.cli.Config')
    @patch('bot.cli.ContentGenerator')
    @patch('bot.cli.JSONCategoryManager')
    def test_generate_command_existing_content(self, mock_manager, mock_generator, mock_config, runner, sample_category_data):
        """Test generate command when content already exists."""
        # Setup config mock
        mock_config_instance = Mock()
        mock_config_instance.categories_directory = "categories"
        mock_config.return_value = mock_config_instance
        
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

        with patch('bot.cli.console') as mock_console:
            # Provide 'y' input for confirmation prompt
            result = runner.invoke(app, ["generate", "test-category", "Test Topic"], input="y\n")

            assert result.exit_code == 0
            print_calls = [call[0][0] for call in mock_console.print.call_args_list]
            assert any("Content already exists for this topic" in call for call in print_calls)
    
    @patch('bot.cli.Config')
    @patch('bot.cli.ContentGenerator')
    @patch('bot.cli.JSONCategoryManager')
    def test_generate_command_category_not_found(self, mock_manager, mock_generator, mock_config, runner):
        """Test generate command with non-existent category."""
        # Setup config mock
        mock_config_instance = Mock()
        mock_config_instance.categories_directory = "categories"
        mock_config.return_value = mock_config_instance
        
        # Setup mocks
        mock_manager_instance = Mock()
        mock_manager_instance.load_category.side_effect = FileNotFoundError()
        mock_manager.return_value = mock_manager_instance
        
        with patch('bot.cli.console') as mock_console:
            # Provide 'y' input for confirmation prompt
            result = runner.invoke(app, ["generate", "nonexistent", "Topic"], input="y\n")
            
            assert result.exit_code == 1
            print_calls = [call[0][0] for call in mock_console.print.call_args_list]
            assert any("Category 'nonexistent' not found" in call for call in print_calls)
    
    @patch('bot.cli.Config')
    @patch('bot.publisher.twitter.TwitterPublisher')
    @patch('bot.publisher.telegram.TelegramPublisher')
    @patch('bot.cli.ContentGenerator')
    @patch('bot.cli.JSONCategoryManager')
    def test_post_command_success(self, mock_manager, mock_generator, mock_telegram, mock_twitter, mock_config, runner, sample_category_data):
        """Test post command with successful posting."""
        # Setup config mock
        mock_config_instance = Mock()
        mock_config_instance.categories_directory = "categories"
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
        
        # Setup category manager mocks
        mock_category = Category(**sample_category_data)
        mock_manager_instance = Mock()
        mock_manager_instance.load_category.return_value = mock_category
        mock_manager_instance.save_category.return_value = None
        mock_manager.return_value = mock_manager_instance
        
        # Setup content generator mocks
        mock_entry = CategoryEntry(
            content="This is a test content with proper length and formatting! #test #new",
            metadata=CategoryMetadata(length=70, source="openai", tags=["#test", "#new"])
        )
        mock_generator_instance = Mock()
        async def mock_generate_content(*args, **kwargs):
            return mock_entry
        mock_generator_instance.generate_content = mock_generate_content
        mock_generator.return_value = mock_generator_instance
        
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
        
        with patch('bot.cli.console') as mock_console:
            result = runner.invoke(app, ["post", "test-category", "Test Topic"])
            
            assert result.exit_code == 0
            print_calls = [call[0][0] for call in mock_console.print.call_args_list]
            assert any("Posted successfully" in call for call in print_calls)
    
    @patch('bot.cli.Config')
    @patch('bot.cli.ContentGenerator')
    @patch('bot.cli.JSONCategoryManager')
    def test_post_command_no_content(self, mock_manager, mock_generator, mock_config, runner):
        """Test post command when no content exists for topic."""
        # Setup config mock
        mock_config_instance = Mock()
        mock_config_instance.categories_directory = "categories"
        mock_config.return_value = mock_config_instance
        
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
        
        # Setup content generator to return None (no content generated)
        mock_generator_instance = Mock()
        async def mock_generate_content(*args, **kwargs):
            return None
        mock_generator_instance.generate_content = mock_generate_content
        mock_generator.return_value = mock_generator_instance
        
        with patch('bot.cli.console') as mock_console:
            result = runner.invoke(app, ["post", "test-category", "New Topic"])
            
            assert result.exit_code == 1
            print_calls = [call[0][0] for call in mock_console.print.call_args_list]
            assert any("Failed to generate content" in call for call in print_calls)
    
    @patch('bot.cli.Config')
    @patch('bot.cli.ContentGenerator')
    @patch('bot.cli.JSONCategoryManager')
    def test_post_command_dry_run(self, mock_manager, mock_generator, mock_config, runner, sample_category_data):
        """Test post command in dry run mode."""
        # Setup config mock
        mock_config_instance = Mock()
        mock_config_instance.categories_directory = "categories"
        mock_config_instance.dry_run = True
        mock_config.return_value = mock_config_instance
        
        # Setup category manager mocks
        mock_category = Category(**sample_category_data)
        mock_manager_instance = Mock()
        mock_manager_instance.load_category.return_value = mock_category
        mock_manager_instance.save_category.return_value = None
        mock_manager.return_value = mock_manager_instance
        
        # Setup content generator mocks
        mock_entry = CategoryEntry(
            content="This is a test content with proper length and formatting! #test #new",
            metadata=CategoryMetadata(length=70, source="openai", tags=["#test", "#new"])
        )
        mock_generator_instance = Mock()
        async def mock_generate_content(*args, **kwargs):
            return mock_entry
        mock_generator_instance.generate_content = mock_generate_content
        mock_generator.return_value = mock_generator_instance
        
        with patch('bot.cli.console') as mock_console:
            result = runner.invoke(app, ["post", "test-category", "Test Topic"])
            
            assert result.exit_code == 0
            print_calls = [call[0][0] for call in mock_console.print.call_args_list]
            assert any("DRY RUN" in call for call in print_calls)
    
    @patch('bot.cli.Config')
    @patch('bot.cli.JSONCategoryManager')
    def test_list_topics_command(self, mock_manager, mock_config, runner, sample_category_data):
        """Test list-topics command."""
        mock_config_instance = Mock()
        mock_config_instance.categories_directory = "categories"
        mock_config.return_value = mock_config_instance
        
        mock_category = Category(**sample_category_data)
        mock_manager_instance = Mock()
        mock_manager_instance.load_category.return_value = mock_category
        mock_manager.return_value = mock_manager_instance
        
        with patch('bot.cli.console') as mock_console:
            result = runner.invoke(app, ["list-topics", "test-category"])
            
            assert result.exit_code == 0
            print_calls = [call[0][0] for call in mock_console.print.call_args_list]
            assert any("Test Topic" in call for call in print_calls)
    
    @patch('bot.cli.Config')
    @patch('bot.cli.JSONCategoryManager')
    def test_list_topics_command_category_not_found(self, mock_manager, mock_config, runner):
        """Test list-topics command with non-existent category."""
        mock_config_instance = Mock()
        mock_config_instance.categories_directory = "categories"
        mock_config.return_value = mock_config_instance
        
        mock_manager_instance = Mock()
        mock_manager_instance.load_category.side_effect = FileNotFoundError()
        mock_manager.return_value = mock_manager_instance
        
        with patch('bot.cli.console') as mock_console:
            result = runner.invoke(app, ["list-topics", "nonexistent"])
            
            assert result.exit_code == 1
            print_calls = [call[0][0] for call in mock_console.print.call_args_list]
            assert any("Category 'nonexistent' not found" in call for call in print_calls)
    
    def test_help_command(self, runner):
        """Test help command."""
        result = runner.invoke(app, ["--help"])
        
        assert result.exit_code == 0
        assert "OpenCast Bot" in result.stdout
    
    def test_invalid_command(self, runner):
        """Test invalid command."""
        result = runner.invoke(app, ["invalid-command"])
        
        assert result.exit_code != 0
    
    @patch('bot.cli.Config')
    def test_config_loading_error(self, mock_config, runner):
        """Test CLI behavior when config loading fails."""
        mock_config.side_effect = Exception("Config error")
        
        # Test with a command that actually uses Config
        with patch('bot.cli.console') as mock_console:
            result = runner.invoke(app, ["validate-config"])
            
            assert result.exit_code == 1
            print_calls = [call[0][0] for call in mock_console.print.call_args_list]
            assert any("Unexpected error" in call for call in print_calls)
    
    def test_generate_command_missing_arguments(self, runner):
        """Test generate command with missing arguments."""
        result = runner.invoke(app, ["generate"])
        
        assert result.exit_code != 0
        # Typer outputs error messages to stderr for missing arguments
        assert result.exit_code == 2  # Typer's exit code for missing arguments
    
    def test_post_command_missing_arguments(self, runner):
        """Test post command with missing arguments."""
        result = runner.invoke(app, ["post"])
        
        assert result.exit_code != 0
        # Typer outputs error messages to stderr for missing arguments
        assert result.exit_code == 2  # Typer's exit code for missing arguments
    
    @patch('bot.cli.Config')
    def test_test_twitter_command_success(self, mock_config, runner):
        """Test test-twitter command with valid configuration."""
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
            
            with patch('bot.cli.console') as mock_console:
                result = runner.invoke(app, ["test-twitter"])
                
                assert result.exit_code == 0
                print_calls = [call[0][0] for call in mock_console.print.call_args_list]
                assert any("Twitter API connection successful" in call for call in print_calls)
    
    @patch('bot.cli.Config')
    def test_test_twitter_command_invalid_config(self, mock_config, runner):
        """Test test-twitter command with invalid configuration."""
        mock_config_instance = Mock()
        mock_config_instance.validate_twitter_config.return_value = False
        mock_config.return_value = mock_config_instance
        
        with patch('bot.cli.console') as mock_console:
            result = runner.invoke(app, ["test-twitter"])
            
            assert result.exit_code == 1
            print_calls = [call[0][0] for call in mock_console.print.call_args_list]
            assert any("Twitter configuration is invalid" in call for call in print_calls)
    
    @patch('bot.cli.Config')
    @patch('bot.cli.JSONCategoryManager')
    def test_generate_command_generation_error(self, mock_manager, mock_config, runner, sample_category_data):
        """Test generate command when generation fails."""
        # Setup config mock
        mock_config_instance = Mock()
        mock_config_instance.categories_directory = "categories"
        mock_config.return_value = mock_config_instance
        
        mock_category = Category(**sample_category_data)
        mock_manager_instance = Mock()
        mock_manager_instance.load_category.return_value = mock_category
        mock_manager.return_value = mock_manager_instance
        
        with patch('bot.cli.ContentGenerator') as mock_generator:
            mock_generator_instance = Mock()
            async def mock_generate_content(*args, **kwargs):
                raise Exception("Generation failed")
            mock_generator_instance.generate_content = mock_generate_content
            mock_generator.return_value = mock_generator_instance
            
            with patch('bot.cli.console') as mock_console:
                result = runner.invoke(app, ["generate", "test-category", "New Topic"], input="y\n")
                
                assert result.exit_code == 1
                print_calls = [call[0][0] for call in mock_console.print.call_args_list]
                assert any("Unexpected error" in call for call in print_calls)
    
    @patch('bot.cli.Config')
    @patch('bot.publisher.twitter.TwitterPublisher')
    @patch('bot.publisher.telegram.TelegramPublisher')
    @patch('bot.cli.ContentGenerator')
    @patch('bot.cli.JSONCategoryManager')
    def test_post_command_partial_success(self, mock_manager, mock_generator, mock_telegram, mock_twitter, mock_config, runner, sample_category_data):
        """Test post command with partial success (one platform fails)."""
        # Setup config mock
        mock_config_instance = Mock()
        mock_config_instance.categories_directory = "categories"
        mock_config_instance.dry_run = False
        mock_config_instance.get_enabled_platforms.return_value = ["twitter", "telegram"]
        
        # Mock config properties
        mock_config_instance.twitter_api_key = "test_key"
        mock_config_instance.twitter_api_secret = "test_secret"
        mock_config_instance.twitter_access_token = "test_token"
        mock_config_instance.twitter_access_token_secret = "test_token_secret"
        mock_config_instance.twitter_bearer_token = "test_bearer"
        mock_config_instance.telegram_bot_token = "test_bot_token"
        mock_config_instance.telegram_chat_id = "test_chat_id"
        mock_config_instance.telegram_parse_mode = "HTML"
        
        mock_config.return_value = mock_config_instance
        
        # Setup category manager mocks
        mock_category = Category(**sample_category_data)
        mock_manager_instance = Mock()
        mock_manager_instance.load_category.return_value = mock_category
        mock_manager_instance.save_category.return_value = None
        mock_manager.return_value = mock_manager_instance
        
        # Setup content generator mocks
        mock_entry = CategoryEntry(
            content="This is a test content with proper length and formatting! #test #new",
            metadata=CategoryMetadata(length=70, source="openai", tags=["#test", "#new"])
        )
        mock_generator_instance = Mock()
        async def mock_generate_content(*args, **kwargs):
            return mock_entry
        mock_generator_instance.generate_content = mock_generate_content
        mock_generator.return_value = mock_generator_instance
        
        # Mock Twitter success, Telegram failure
        mock_twitter_instance = Mock()
        mock_twitter_instance.post_content = AsyncMock(return_value=True)
        mock_twitter_instance.__aenter__ = AsyncMock(return_value=mock_twitter_instance)
        mock_twitter_instance.__aexit__ = AsyncMock(return_value=None)
        mock_twitter.return_value = mock_twitter_instance
        
        mock_telegram_instance = Mock()
        mock_telegram_instance.post_content = AsyncMock(return_value=False)
        mock_telegram_instance.__aenter__ = AsyncMock(return_value=mock_telegram_instance)
        mock_telegram_instance.__aexit__ = AsyncMock(return_value=None)
        mock_telegram.return_value = mock_telegram_instance
        
        with patch('bot.cli.console') as mock_console:
            result = runner.invoke(app, ["post", "test-category", "Test Topic"])
            
            assert result.exit_code == 0
            print_calls = [call[0][0] for call in mock_console.print.call_args_list]
            assert any("Posted successfully" in call for call in print_calls)
            assert any("Posted to Twitter" in call for call in print_calls)
            assert any("Failed to post to Telegram" in call for call in print_calls) 