"""
JSON-based ORM module for OpenCast Bot.

This module provides a simple Object-Relational Mapping (ORM) interface
for managing category data stored in JSON files.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

from bot.models.category import Category
from bot.utils import (
    get_logger, LoggerMixin, log_execution_time,
    OpenCastBotError, ValidationError as BotValidationError,
    CategoryNotFoundError, InvalidCategoryError,
    ResourceNotFoundError, InvalidDataError
)

T = TypeVar('T', bound=BaseModel)


class JSONCategoryManager(LoggerMixin):
    """JSON-based category manager for OpenCast Bot."""
    
    def __init__(self, data_directory: str = "categories") -> None:
        """
        Initialize JSON category manager with data directory.
        
        Args:
            data_directory: Directory where JSON files are stored
        """
        super().__init__()
        self.data_directory = Path(data_directory)
        self.data_directory.mkdir(exist_ok=True)
        
        self.logger.info(
            "JSONCategoryManager initialized",
            data_directory=str(self.data_directory),
            directory_exists=self.data_directory.exists()
        )
    
    def _get_category_file_path(self, category_id: str) -> Path:
        """
        Get the file path for a category.
        
        Args:
            category_id: Category identifier
            
        Returns:
            Path to the category JSON file
        """
        return self.data_directory / f"{category_id}.json"
    
    def _validate_category_structure(self, data: dict) -> None:
        """
        Validate category data structure.
        
        Args:
            data: Category data dictionary
            
        Raises:
            InvalidDataError: If data structure is invalid
        """
        required_fields = ["category_id", "name"]
        
        for field in required_fields:
            if field not in data:
                raise InvalidDataError(
                    f"Missing required field: {field}",
                    field_name=field,
                    data_type="category",
                    validation_rule="required_field"
                )
        
        if "topics" in data and not isinstance(data["topics"], list):
            raise InvalidDataError(
                "Topics field must be a list",
                field_name="topics",
                field_value=type(data["topics"]).__name__,
                data_type="category",
                validation_rule="field_type"
            )
    
    @log_execution_time
    def list_categories(self) -> List[str]:
        """
        List all available category IDs.
        
        Returns:
            List of category identifiers
        """
        try:
            json_files = list(self.data_directory.glob("*.json"))
            category_ids = [f.stem for f in json_files]
            
            self.logger.info(
                "Listed categories",
                category_count=len(category_ids),
                categories=category_ids
            )
            return category_ids
            
        except Exception as e:
            self.logger.error(
                "Failed to list categories",
                error=str(e),
                data_directory=str(self.data_directory)
            )
            raise OpenCastBotError(
                f"Failed to list categories: {str(e)}",
                context={"data_directory": str(self.data_directory)},
                cause=e
            )
    
    def category_exists(self, category_id: str) -> bool:
        """
        Check if a category file exists.
        
        Args:
            category_id: Category identifier to check
            
        Returns:
            True if category file exists, False otherwise
        """
        file_path = self._get_category_file_path(category_id)
        exists = file_path.exists()
        
        self.logger.debug(
            "Category existence check",
            category_id=category_id,
            file_path=str(file_path),
            exists=exists
        )
        
        return exists
    
    @log_execution_time
    def load_category(self, category_id: str) -> Category:
        """
        Load a category from JSON file.
        
        Args:
            category_id: Category identifier to load
            
        Returns:
            Category object
            
        Raises:
            CategoryNotFoundError: If category file doesn't exist
            InvalidDataError: If category data is invalid
        """
        file_path = self._get_category_file_path(category_id)
        
        if not file_path.exists():
            self.logger.warning(
                "Category file not found",
                category_id=category_id,
                file_path=str(file_path)
            )
            raise CategoryNotFoundError(category_id)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                category_data = json.load(f)
            
            # Validate structure
            self._validate_category_structure(category_data)
            
            # Create and validate Category object
            category = Category.model_validate(category_data)
            
            self.logger.info(
                "Category loaded successfully",
                category_id=category_id,
                file_path=str(file_path),
                topic_count=len(category.topics) if category.topics else 0
            )
            return category
            
        except json.JSONDecodeError as e:
            error = InvalidDataError(
                f"Invalid JSON in category file: {str(e)}",
                field_name="json_content",
                data_type="category_file",
                validation_rule="valid_json",
                context={"file_path": str(file_path), "category_id": category_id}
            )
            self.logger.error("JSON decode error", error=error)
            raise error
            
        except ValidationError as e:
            error = InvalidDataError(
                f"Invalid category data structure: {str(e)}",
                field_name="category_structure",
                data_type="category",
                validation_rule="pydantic_model",
                context={"file_path": str(file_path), "category_id": category_id}
            )
            self.logger.error("Category validation error", error=error)
            raise error
            
        except Exception as e:
            error = OpenCastBotError(
                f"Failed to load category: {str(e)}",
                context={"file_path": str(file_path), "category_id": category_id},
                cause=e
            )
            self.logger.error("Category load error", error=error)
            raise error
    
    @log_execution_time
    def save_category(self, category: Category) -> None:
        """
        Save a category to JSON file.
        
        Args:
            category: Category object to save
            
        Raises:
            InvalidDataError: If save operation fails
        """
        try:
            # Ensure directory exists
            self.data_directory.mkdir(parents=True, exist_ok=True)
            
            file_path = self._get_category_file_path(category.category_id)
            
            # Convert to JSON-serializable dict
            category_dict = category.model_dump(mode='json')
            
            # Write to file with proper formatting
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(category_dict, f, indent=2, ensure_ascii=False)
            
            self.logger.info(
                "Category saved successfully",
                category_id=category.category_id,
                file_path=str(file_path),
                topic_count=len(category.topics) if category.topics else 0
            )
            
        except Exception as e:
            error = OpenCastBotError(
                f"Failed to save category '{category.category_id}': {str(e)}",
                context={
                    "category_id": category.category_id,
                    "file_path": str(self._get_category_file_path(category.category_id))
                },
                cause=e
            )
            self.logger.error("Category save error", error=error)
            raise error
    
    @log_execution_time
    def delete_category(self, category_id: str) -> None:
        """
        Delete a category file.
        
        Args:
            category_id: Category identifier to delete
            
        Raises:
            CategoryNotFoundError: If category file doesn't exist
            OpenCastBotError: If delete operation fails
        """
        file_path = self._get_category_file_path(category_id)
        
        if not file_path.exists():
            self.logger.warning(
                "Cannot delete non-existent category",
                category_id=category_id,
                file_path=str(file_path)
            )
            raise CategoryNotFoundError(category_id)
        
        try:
            file_path.unlink()
            self.logger.info(
                "Category deleted successfully",
                category_id=category_id,
                file_path=str(file_path)
            )
            
        except Exception as e:
            error = OpenCastBotError(
                f"Failed to delete category '{category_id}': {str(e)}",
                context={"category_id": category_id, "file_path": str(file_path)},
                cause=e
            )
            self.logger.error("Category delete error", error=error)
            raise error
    
    @log_execution_time
    def get_category_stats(self, category_id: str) -> Dict[str, any]:
        """
        Get statistics for a category.
        
        Args:
            category_id: Category identifier
            
        Returns:
            Dictionary with category statistics
            
        Raises:
            CategoryNotFoundError: If category doesn't exist
        """
        category = self.load_category(category_id)
        
        total_entries = sum(len(topic.entries) for topic in category.topics)
        
        stats = {
            "category_id": category.category_id,
            "name": category.name,
            "topic_count": len(category.topics),
            "total_entries": total_entries,
            "description": category.description,
            "language": category.language
        }
        
        self.logger.info(
            "Category stats generated",
            category_id=category_id,
            stats=stats
        )
        
        return stats
    
    @log_execution_time
    def backup_category(self, category_id: str) -> Path:
        """
        Create a backup of a category file.
        
        Args:
            category_id: Category identifier to backup
            
        Returns:
            Path to the backup file
            
        Raises:
            CategoryNotFoundError: If category doesn't exist
            OpenCastBotError: If backup operation fails
        """
        file_path = self._get_category_file_path(category_id)
        
        if not file_path.exists():
            self.logger.warning(
                "Cannot backup non-existent category",
                category_id=category_id,
                file_path=str(file_path)
            )
            raise CategoryNotFoundError(category_id)
        
        # Create backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = file_path.parent / f"{category_id}_backup_{timestamp}.json"
        
        try:
            # Copy file content
            with open(file_path, 'r', encoding='utf-8') as src, \
                 open(backup_path, 'w', encoding='utf-8') as dst:
                dst.write(src.read())
            
            self.logger.info(
                "Category backup created",
                category_id=category_id,
                original_path=str(file_path),
                backup_path=str(backup_path)
            )
            return backup_path
            
        except Exception as e:
            error = OpenCastBotError(
                f"Failed to backup category '{category_id}': {str(e)}",
                context={
                    "category_id": category_id,
                    "file_path": str(file_path),
                    "backup_path": str(backup_path)
                },
                cause=e
            )
            self.logger.error("Category backup error", error=error)
            raise error


class JsonORM(LoggerMixin):
    """Simple JSON-based ORM for managing category data files."""
    
    def __init__(self, data_directory: str = "categories") -> None:
        """
        Initialize JSON ORM with data directory.
        
        Args:
            data_directory: Directory where JSON files are stored
        """
        super().__init__()
        self.data_directory = Path(data_directory)
        self.data_directory.mkdir(exist_ok=True)
        
        self.logger.info(
            "JsonORM initialized",
            data_directory=str(self.data_directory)
        )
    
    def _get_file_path(self, category_id: str) -> Path:
        """
        Get the file path for a category.
        
        Args:
            category_id: Category identifier
            
        Returns:
            Path to the category JSON file
        """
        return self.data_directory / f"{category_id}.json"
    
    @log_execution_time
    def save_category(self, category: Category) -> bool:
        """
        Save a category to JSON file.
        
        Args:
            category: Category object to save
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            file_path = self._get_file_path(category.category_id)
            
            # Convert to JSON-serializable dict
            category_dict = category.model_dump(mode='json')
            
            # Write to file with proper formatting
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(category_dict, f, indent=2, ensure_ascii=False)
            
            self.logger.info(
                "Category saved via JsonORM",
                category_id=category.category_id,
                file_path=str(file_path)
            )
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to save category via JsonORM",
                category_id=category.category_id,
                error=str(e)
            )
            return False
    
    @log_execution_time
    def load_category(self, category_id: str) -> Optional[Category]:
        """
        Load a category from JSON file.
        
        Args:
            category_id: Category identifier to load
            
        Returns:
            Category object if found and valid, None otherwise
        """
        try:
            file_path = self._get_file_path(category_id)
            
            if not file_path.exists():
                self.logger.warning(
                    "Category file not found for JsonORM load",
                    category_id=category_id,
                    file_path=str(file_path)
                )
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                category_data = json.load(f)
            
            # Validate and create Category object
            category = Category.model_validate(category_data)
            
            self.logger.info(
                "Category loaded via JsonORM",
                category_id=category_id,
                file_path=str(file_path)
            )
            return category
            
        except Exception as e:
            self.logger.error(
                "Failed to load category via JsonORM",
                category_id=category_id,
                error=str(e)
            )
            return None
    
    def category_exists(self, category_id: str) -> bool:
        """
        Check if a category file exists.
        
        Args:
            category_id: Category identifier to check
            
        Returns:
            True if category file exists, False otherwise
        """
        file_path = self._get_file_path(category_id)
        exists = file_path.exists()
        
        self.logger.debug(
            "Category existence check via JsonORM",
            category_id=category_id,
            file_path=str(file_path),
            exists=exists
        )
        
        return exists
    
    @log_execution_time
    def list_categories(self) -> List[str]:
        """
        List all available category IDs.
        
        Returns:
            List of category identifiers
        """
        try:
            json_files = list(self.data_directory.glob("*.json"))
            category_ids = [f.stem for f in json_files]
            
            self.logger.info(
                "Categories listed via JsonORM",
                category_count=len(category_ids),
                categories=category_ids
            )
            return category_ids
            
        except Exception as e:
            self.logger.error(
                "Failed to list categories via JsonORM",
                error=str(e),
                data_directory=str(self.data_directory)
            )
            return []
    
    @log_execution_time
    def delete_category(self, category_id: str) -> bool:
        """
        Delete a category file.
        
        Args:
            category_id: Category identifier to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            file_path = self._get_file_path(category_id)
            
            if not file_path.exists():
                self.logger.warning(
                    "Category file not found for deletion via JsonORM",
                    category_id=category_id,
                    file_path=str(file_path)
                )
                return False
            
            file_path.unlink()
            self.logger.info(
                "Category deleted via JsonORM",
                category_id=category_id,
                file_path=str(file_path)
            )
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to delete category via JsonORM",
                category_id=category_id,
                error=str(e)
            )
            return False
    
    @log_execution_time
    def backup_category(self, category_id: str, backup_suffix: str = ".backup") -> bool:
        """
        Create a backup of a category file.
        
        Args:
            category_id: Category identifier to backup
            backup_suffix: Suffix to add to backup filename
            
        Returns:
            True if backup created successfully, False otherwise
        """
        try:
            original_path = self._get_file_path(category_id)
            backup_path = original_path.with_suffix(f"{original_path.suffix}{backup_suffix}")
            
            if not original_path.exists():
                self.logger.warning(
                    "Cannot backup non-existent category via JsonORM",
                    category_id=category_id,
                    original_path=str(original_path)
                )
                return False
            
            # Copy file content
            with open(original_path, 'r', encoding='utf-8') as src, \
                 open(backup_path, 'w', encoding='utf-8') as dst:
                dst.write(src.read())
            
            self.logger.info(
                "Category backup created via JsonORM",
                category_id=category_id,
                original_path=str(original_path),
                backup_path=str(backup_path)
            )
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to backup category via JsonORM",
                category_id=category_id,
                error=str(e)
            )
            return False 