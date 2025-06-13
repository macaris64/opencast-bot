"""
JSON-based ORM module for OpenCast Bot.

This module provides a simple Object-Relational Mapping (ORM) interface
for managing category data stored in JSON files.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

from bot.models.category import Category

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class CategoryNotFoundError(Exception):
    """Exception raised when a category is not found."""
    
    def __init__(self, category_id: str):
        self.category_id = category_id
        super().__init__(f"Category '{category_id}' not found")


class InvalidCategoryError(Exception):
    """Exception raised when category data is invalid."""
    
    def __init__(self, message: str):
        super().__init__(message)


class JSONCategoryManager:
    """JSON-based category manager for OpenCast Bot."""
    
    def __init__(self, data_directory: str = "categories") -> None:
        """
        Initialize JSON category manager with data directory.
        
        Args:
            data_directory: Directory where JSON files are stored
        """
        self.data_directory = Path(data_directory)
        self.data_directory.mkdir(exist_ok=True)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
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
            InvalidCategoryError: If data structure is invalid
        """
        required_fields = ["category_id", "name"]
        
        for field in required_fields:
            if field not in data:
                raise InvalidCategoryError(f"Missing required field: {field}")
        
        if "topics" in data and not isinstance(data["topics"], list):
            raise InvalidCategoryError("Topics field must be a list")
    
    def list_categories(self) -> List[str]:
        """
        List all available category IDs.
        
        Returns:
            List of category identifiers
        """
        try:
            json_files = list(self.data_directory.glob("*.json"))
            category_ids = [f.stem for f in json_files]
            
            self.logger.info(f"Found {len(category_ids)} categories: {category_ids}")
            return category_ids
            
        except Exception as e:
            self.logger.error(f"Failed to list categories: {str(e)}")
            return []
    
    def category_exists(self, category_id: str) -> bool:
        """
        Check if a category file exists.
        
        Args:
            category_id: Category identifier to check
            
        Returns:
            True if category file exists, False otherwise
        """
        file_path = self._get_category_file_path(category_id)
        return file_path.exists()
    
    def load_category(self, category_id: str) -> Category:
        """
        Load a category from JSON file.
        
        Args:
            category_id: Category identifier to load
            
        Returns:
            Category object
            
        Raises:
            CategoryNotFoundError: If category file doesn't exist
            InvalidCategoryError: If category data is invalid
        """
        file_path = self._get_category_file_path(category_id)
        
        if not file_path.exists():
            raise CategoryNotFoundError(category_id)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                category_data = json.load(f)
            
            # Validate structure
            self._validate_category_structure(category_data)
            
            # Create and validate Category object
            category = Category.model_validate(category_data)
            
            self.logger.info(f"Loaded category '{category_id}' from {file_path}")
            return category
            
        except json.JSONDecodeError as e:
            raise InvalidCategoryError(f"Invalid JSON in category file: {str(e)}")
        except ValidationError as e:
            raise InvalidCategoryError(f"Invalid category data structure: {str(e)}")
        except Exception as e:
            raise InvalidCategoryError(f"Failed to load category: {str(e)}")
    
    def save_category(self, category: Category) -> None:
        """
        Save a category to JSON file.
        
        Args:
            category: Category object to save
            
        Raises:
            InvalidCategoryError: If save operation fails
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
            
            self.logger.info(f"Saved category '{category.category_id}' to {file_path}")
            
        except Exception as e:
            raise InvalidCategoryError(f"Failed to save category '{category.category_id}': {str(e)}")
    
    def delete_category(self, category_id: str) -> None:
        """
        Delete a category file.
        
        Args:
            category_id: Category identifier to delete
            
        Raises:
            CategoryNotFoundError: If category file doesn't exist
            InvalidCategoryError: If delete operation fails
        """
        file_path = self._get_category_file_path(category_id)
        
        if not file_path.exists():
            raise CategoryNotFoundError(category_id)
        
        try:
            file_path.unlink()
            self.logger.info(f"Deleted category '{category_id}' file: {file_path}")
            
        except Exception as e:
            raise InvalidCategoryError(f"Failed to delete category '{category_id}': {str(e)}")
    
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
        
        return {
            "category_id": category.category_id,
            "name": category.name,
            "topic_count": len(category.topics),
            "total_entries": total_entries,
            "description": category.description,
            "language": category.language
        }
    
    def backup_category(self, category_id: str) -> Path:
        """
        Create a backup of a category file.
        
        Args:
            category_id: Category identifier to backup
            
        Returns:
            Path to the backup file
            
        Raises:
            CategoryNotFoundError: If category doesn't exist
        """
        file_path = self._get_category_file_path(category_id)
        
        if not file_path.exists():
            raise CategoryNotFoundError(category_id)
        
        # Create backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = file_path.parent / f"{category_id}_backup_{timestamp}.json"
        
        try:
            # Copy file content
            with open(file_path, 'r', encoding='utf-8') as src, \
                 open(backup_path, 'w', encoding='utf-8') as dst:
                dst.write(src.read())
            
            self.logger.info(f"Created backup: {backup_path}")
            return backup_path
            
        except Exception as e:
            raise InvalidCategoryError(f"Failed to backup category '{category_id}': {str(e)}")


class JsonORM:
    """Simple JSON-based ORM for managing category data files."""
    
    def __init__(self, data_directory: str = "categories") -> None:
        """
        Initialize JSON ORM with data directory.
        
        Args:
            data_directory: Directory where JSON files are stored
        """
        self.data_directory = Path(data_directory)
        self.data_directory.mkdir(exist_ok=True)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def _get_file_path(self, category_id: str) -> Path:
        """
        Get the file path for a category.
        
        Args:
            category_id: Category identifier
            
        Returns:
            Path to the category JSON file
        """
        return self.data_directory / f"{category_id}.json"
    
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
            
            self.logger.info(f"Saved category '{category.category_id}' to {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save category '{category.category_id}': {str(e)}")
            return False
    
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
                self.logger.warning(f"Category file not found: {file_path}")
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                category_data = json.load(f)
            
            # Validate and create Category object
            category = Category.model_validate(category_data)
            
            self.logger.info(f"Loaded category '{category_id}' from {file_path}")
            return category
            
        except Exception as e:
            self.logger.error(f"Failed to load category '{category_id}': {str(e)}")
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
        return file_path.exists()
    
    def list_categories(self) -> List[str]:
        """
        List all available category IDs.
        
        Returns:
            List of category identifiers
        """
        try:
            json_files = list(self.data_directory.glob("*.json"))
            category_ids = [f.stem for f in json_files]
            
            self.logger.info(f"Found {len(category_ids)} categories: {category_ids}")
            return category_ids
            
        except Exception as e:
            self.logger.error(f"Failed to list categories: {str(e)}")
            return []
    
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
                self.logger.warning(f"Category file not found for deletion: {file_path}")
                return False
            
            file_path.unlink()
            self.logger.info(f"Deleted category '{category_id}' file: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete category '{category_id}': {str(e)}")
            return False
    
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
                self.logger.warning(f"Cannot backup non-existent category: {original_path}")
                return False
            
            # Copy file content
            with open(original_path, 'r', encoding='utf-8') as src, \
                 open(backup_path, 'w', encoding='utf-8') as dst:
                dst.write(src.read())
            
            self.logger.info(f"Created backup: {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to backup category '{category_id}': {str(e)}")
            return False 