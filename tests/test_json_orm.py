"""
Tests for JSON ORM module in OpenCast Bot.

This module tests the JSON file operations and category management
defined in bot/db/json_orm.py.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import pytest

from bot.db.json_orm import JSONCategoryManager, CategoryNotFoundError, InvalidCategoryError, JsonORM
from bot.models.category import Category, CategoryTopic, CategoryEntry, CategoryMetadata
from bot.utils.exceptions import InvalidDataError, OpenCastBotError


class TestJSONCategoryManager:
    """Test cases for JSONCategoryManager class."""
    
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
    
    @pytest.fixture
    def sample_category(self, sample_category_data):
        """Create sample Category object."""
        return Category(**sample_category_data)
    
    def test_manager_initialization_default_directory(self):
        """Test manager initialization with default directory."""
        manager = JSONCategoryManager()
        
        assert manager.data_directory == Path("categories")
    
    def test_manager_initialization_custom_directory(self):
        """Test manager initialization with custom directory."""
        custom_dir = "/tmp/custom"
        manager = JSONCategoryManager(data_directory=custom_dir)
        
        assert manager.data_directory == Path(custom_dir)
    
    def test_get_category_file_path(self):
        """Test getting category file path."""
        manager = JSONCategoryManager(data_directory="/tmp/test")
        
        file_path = manager._get_category_file_path("test-category")
        
        assert file_path == Path("/tmp/test/test-category.json")
    
    def test_list_categories_empty_directory(self):
        """Test listing categories in empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = JSONCategoryManager(data_directory=temp_dir)
            
            categories = manager.list_categories()
            
            assert categories == []
    
    def test_list_categories_with_files(self, sample_category_data):
        """Test listing categories with existing files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create sample category files
            category1_file = Path(temp_dir) / "category1.json"
            category2_file = Path(temp_dir) / "category2.json"
            
            with open(category1_file, 'w') as f:
                json.dump(sample_category_data, f)
            
            sample_category_data2 = sample_category_data.copy()
            sample_category_data2["category_id"] = "category2"
            sample_category_data2["name"] = "Category 2"
            
            with open(category2_file, 'w') as f:
                json.dump(sample_category_data2, f)
            
            # Create a non-JSON file (should be ignored)
            (Path(temp_dir) / "not_json.txt").write_text("not json")
            
            manager = JSONCategoryManager(data_directory=temp_dir)
            categories = manager.list_categories()
            
            assert len(categories) == 2
            assert "category1" in categories
            assert "category2" in categories
    
    def test_category_exists_true(self, sample_category_data):
        """Test category_exists returns True for existing category."""
        with tempfile.TemporaryDirectory() as temp_dir:
            category_file = Path(temp_dir) / "test-category.json"
            with open(category_file, 'w') as f:
                json.dump(sample_category_data, f)
            
            manager = JSONCategoryManager(data_directory=temp_dir)
            
            assert manager.category_exists("test-category") is True
    
    def test_category_exists_false(self):
        """Test category_exists returns False for non-existent category."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = JSONCategoryManager(data_directory=temp_dir)
            
            assert manager.category_exists("nonexistent") is False
    
    def test_load_category_success(self, sample_category_data):
        """Test loading existing category successfully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            category_file = Path(temp_dir) / "test-category.json"
            with open(category_file, 'w') as f:
                json.dump(sample_category_data, f)
            
            manager = JSONCategoryManager(data_directory=temp_dir)
            category = manager.load_category("test-category")
            
            assert isinstance(category, Category)
            assert category.category_id == "test-category"
            assert category.name == "Test Category"
            assert len(category.topics) == 1
            assert category.topics[0].topic == "Test Topic"
    
    def test_load_category_not_found(self):
        """Test loading non-existent category raises error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = JSONCategoryManager(data_directory=temp_dir)
            
            with pytest.raises(CategoryNotFoundError):
                manager.load_category("nonexistent")
    
    def test_load_category_invalid_json(self):
        """Test loading category with invalid JSON raises error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            category_file = Path(temp_dir) / "invalid.json"
            category_file.write_text("invalid json content")
            
            manager = JSONCategoryManager(data_directory=temp_dir)
            
            with pytest.raises(InvalidDataError):
                manager.load_category("invalid")
    
    def test_load_category_invalid_structure(self):
        """Test loading category with invalid structure raises error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            category_file = Path(temp_dir) / "invalid-structure.json"
            invalid_data = {"invalid": "structure"}
            
            with open(category_file, 'w') as f:
                json.dump(invalid_data, f)
            
            manager = JSONCategoryManager(data_directory=temp_dir)
            
            with pytest.raises(OpenCastBotError):  # Wrapped in OpenCastBotError
                manager.load_category("invalid-structure")
    
    def test_save_category_new_file(self, sample_category):
        """Test saving category to new file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = JSONCategoryManager(data_directory=temp_dir)
            
            manager.save_category(sample_category)
            
            # Verify file was created
            category_file = Path(temp_dir) / "test-category.json"
            assert category_file.exists()
            
            # Verify content
            with open(category_file, 'r') as f:
                saved_data = json.load(f)
            
            assert saved_data["category_id"] == "test-category"
            assert saved_data["name"] == "Test Category"
    
    def test_save_category_overwrite_existing(self, sample_category):
        """Test saving category overwrites existing file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            category_file = Path(temp_dir) / "test-category.json"
            
            # Create existing file with different content
            existing_data = {"category_id": "test-category", "name": "Old Name"}
            with open(category_file, 'w') as f:
                json.dump(existing_data, f)
            
            manager = JSONCategoryManager(data_directory=temp_dir)
            manager.save_category(sample_category)
            
            # Verify content was updated
            with open(category_file, 'r') as f:
                saved_data = json.load(f)
            
            assert saved_data["name"] == "Test Category"  # New name
    
    def test_save_category_creates_directory(self, sample_category):
        """Test saving category creates directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            non_existent_dir = Path(temp_dir) / "new_dir"
            manager = JSONCategoryManager(data_directory=non_existent_dir)
            
            manager.save_category(sample_category)
            
            # Verify directory was created
            assert non_existent_dir.exists()
            assert non_existent_dir.is_dir()
            
            # Verify file was created
            category_file = non_existent_dir / "test-category.json"
            assert category_file.exists()
    
    @patch('builtins.open', side_effect=PermissionError("Permission denied"))
    def test_save_category_permission_error(self, mock_open_func, sample_category):
        """Test saving category handles permission errors."""
        manager = JSONCategoryManager(data_directory="/tmp/test")
        
        with pytest.raises(OpenCastBotError):
            manager.save_category(sample_category)
    
    def test_delete_category_success(self, sample_category_data):
        """Test deleting existing category successfully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            category_file = Path(temp_dir) / "test-category.json"
            with open(category_file, 'w') as f:
                json.dump(sample_category_data, f)
            
            manager = JSONCategoryManager(data_directory=temp_dir)
            
            # Verify file exists before deletion
            assert category_file.exists()
            
            manager.delete_category("test-category")
            
            # Verify file was deleted
            assert not category_file.exists()
    
    def test_delete_category_not_found(self):
        """Test deleting non-existent category raises error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = JSONCategoryManager(data_directory=temp_dir)
            
            with pytest.raises(CategoryNotFoundError):
                manager.delete_category("nonexistent")
    
    @patch('pathlib.Path.unlink', side_effect=PermissionError("Permission denied"))
    def test_delete_category_permission_error(self, mock_unlink, sample_category_data):
        """Test deleting category handles permission errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            category_file = Path(temp_dir) / "test-category.json"
            with open(category_file, 'w') as f:
                json.dump(sample_category_data, f)
            
            manager = JSONCategoryManager(data_directory=temp_dir)
            
            with pytest.raises(OpenCastBotError):
                manager.delete_category("test-category")
    
    def test_get_category_stats(self, sample_category_data):
        """Test getting category statistics."""
        with tempfile.TemporaryDirectory() as temp_dir:
            category_file = Path(temp_dir) / "test-category.json"
            with open(category_file, 'w') as f:
                json.dump(sample_category_data, f)
            
            manager = JSONCategoryManager(data_directory=temp_dir)
            stats = manager.get_category_stats("test-category")
            
            assert stats["category_id"] == "test-category"
            assert stats["name"] == "Test Category"
            assert stats["topic_count"] == 1
            assert stats["total_entries"] == 1
    
    def test_get_category_stats_not_found(self):
        """Test getting stats for non-existent category raises error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = JSONCategoryManager(data_directory=temp_dir)
            
            with pytest.raises(CategoryNotFoundError):
                manager.get_category_stats("nonexistent")
    
    def test_backup_category(self, sample_category_data):
        """Test creating backup of category."""
        with tempfile.TemporaryDirectory() as temp_dir:
            category_file = Path(temp_dir) / "test-category.json"
            with open(category_file, 'w') as f:
                json.dump(sample_category_data, f)
            
            manager = JSONCategoryManager(data_directory=temp_dir)
            backup_path = manager.backup_category("test-category")
            
            # Verify backup file was created
            assert backup_path.exists()
            assert backup_path.name.startswith("test-category_backup_")
            assert backup_path.suffix == ".json"
            
            # Verify backup content matches original
            with open(backup_path, 'r') as f:
                backup_data = json.load(f)
            
            assert backup_data == sample_category_data
    
    def test_backup_category_not_found(self):
        """Test backing up non-existent category raises error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = JSONCategoryManager(data_directory=temp_dir)
            
            with pytest.raises(CategoryNotFoundError):
                manager.backup_category("nonexistent")
    
    def test_validate_category_structure_valid(self, sample_category_data):
        """Test validating valid category structure."""
        manager = JSONCategoryManager()
        
        # Should not raise any exception
        manager._validate_category_structure(sample_category_data)
    
    def test_validate_category_structure_missing_required_field(self):
        """Test validating category structure with missing required field."""
        manager = JSONCategoryManager()
        invalid_data = {"name": "Test"}  # Missing category_id
        
        with pytest.raises(InvalidDataError):
            manager._validate_category_structure(invalid_data)
    
    def test_validate_category_structure_invalid_type(self):
        """Test validating category structure with invalid field type."""
        manager = JSONCategoryManager()
        invalid_data = {
            "category_id": "test",
            "name": "Test",
            "topics": "not a list"  # Should be list
        }
        
        with pytest.raises(InvalidDataError):
            manager._validate_category_structure(invalid_data)


class TestCategoryExceptions:
    """Test cases for custom exceptions."""
    
    def test_category_not_found_error(self):
        """Test CategoryNotFoundError exception."""
        error = CategoryNotFoundError("test-category")
        
        assert "Category 'test-category' not found" in str(error)
        assert error.category_id == "test-category"
    
    def test_invalid_category_error(self):
        """Test InvalidCategoryError exception."""
        error = InvalidCategoryError("Invalid structure")
        
        assert "Invalid structure" in str(error)


class TestJSONORM:
    """Test cases for legacy JsonORM class."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def json_orm(self, temp_dir):
        """Create JsonORM instance for testing."""
        return JsonORM(temp_dir)
    
    @pytest.fixture
    def sample_category_data(self):
        """Sample category data for testing."""
        return {
            "category_id": "test-category",
            "name": "Test Category",
            "description": "Test description",
            "prompt_template": "Generate content about {topic}.",
            "language": "en",
            "topics": []
        }
    
    def test_json_orm_initialization(self, temp_dir):
        """Test JsonORM initialization."""
        orm = JsonORM(temp_dir)
        assert orm.data_directory == Path(temp_dir)
        assert orm.data_directory.exists()
    
    def test_get_file_path(self, json_orm):
        """Test _get_file_path method."""
        file_path = json_orm._get_file_path("test-category")
        expected_path = json_orm.data_directory / "test-category.json"
        assert file_path == expected_path
    
    def test_save_category_success(self, json_orm, sample_category_data):
        """Test successful category save."""
        category = Category(**sample_category_data)
        result = json_orm.save_category(category)
        
        assert result is True
        file_path = json_orm._get_file_path(category.category_id)
        assert file_path.exists()
    
    def test_save_category_failure(self, json_orm, sample_category_data):
        """Test category save failure."""
        category = Category(**sample_category_data)
        
        # Make directory read-only to cause save failure
        json_orm.data_directory.chmod(0o444)
        
        try:
            result = json_orm.save_category(category)
            assert result is False
        finally:
            # Restore permissions
            json_orm.data_directory.chmod(0o755)
    
    def test_load_category_success(self, json_orm, sample_category_data):
        """Test successful category load."""
        category = Category(**sample_category_data)
        json_orm.save_category(category)
        
        loaded_category = json_orm.load_category("test-category")
        assert loaded_category is not None
        assert loaded_category.category_id == "test-category"
        assert loaded_category.name == "Test Category"
    
    def test_load_category_not_found(self, json_orm):
        """Test loading non-existent category."""
        result = json_orm.load_category("nonexistent")
        assert result is None
    
    def test_load_category_invalid_json(self, json_orm):
        """Test loading category with invalid JSON."""
        file_path = json_orm._get_file_path("invalid-json")
        file_path.write_text("invalid json content")
        
        result = json_orm.load_category("invalid-json")
        assert result is None
    
    def test_category_exists_true(self, json_orm, sample_category_data):
        """Test category_exists returns True for existing category."""
        category = Category(**sample_category_data)
        json_orm.save_category(category)
        
        assert json_orm.category_exists("test-category") is True
    
    def test_category_exists_false(self, json_orm):
        """Test category_exists returns False for non-existent category."""
        assert json_orm.category_exists("nonexistent") is False
    
    def test_list_categories_empty(self, json_orm):
        """Test listing categories in empty directory."""
        categories = json_orm.list_categories()
        assert categories == []
    
    def test_list_categories_with_files(self, json_orm, sample_category_data):
        """Test listing categories with existing files."""
        # Create multiple categories
        for i in range(3):
            category_data = sample_category_data.copy()
            category_data["category_id"] = f"test-category-{i}"
            category = Category(**category_data)
            json_orm.save_category(category)
        
        categories = json_orm.list_categories()
        assert len(categories) == 3
        assert "test-category-0" in categories
        assert "test-category-1" in categories
        assert "test-category-2" in categories
    
    def test_delete_category_success(self, json_orm, sample_category_data):
        """Test successful category deletion."""
        category = Category(**sample_category_data)
        json_orm.save_category(category)
        
        result = json_orm.delete_category("test-category")
        assert result is True
        assert not json_orm.category_exists("test-category")
    
    def test_delete_category_not_found(self, json_orm):
        """Test deleting non-existent category."""
        result = json_orm.delete_category("nonexistent")
        assert result is False
    
    def test_backup_category_success(self, json_orm, sample_category_data):
        """Test successful category backup."""
        category = Category(**sample_category_data)
        json_orm.save_category(category)
        
        result = json_orm.backup_category("test-category")
        assert result is True
        
        # Check backup file exists (JsonORM uses .json.backup format)
        backup_files = list(json_orm.data_directory.glob("test-category.json.backup"))
        assert len(backup_files) == 1
    
    def test_backup_category_not_found(self, json_orm):
        """Test backing up non-existent category."""
        result = json_orm.backup_category("nonexistent")
        assert result is False
    
    def test_backup_category_custom_suffix(self, json_orm, sample_category_data):
        """Test category backup with custom suffix."""
        category = Category(**sample_category_data)
        json_orm.save_category(category)
        
        result = json_orm.backup_category("test-category", ".custom")
        assert result is True
        
        # Check backup file exists with custom suffix (JsonORM uses .json.custom format)
        backup_files = list(json_orm.data_directory.glob("test-category.json.custom"))
        assert len(backup_files) == 1 