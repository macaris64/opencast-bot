"""
Category model definitions for OpenCast Bot.

This module defines models for categories and their entries as specified
in section 3.1 of the PDR document.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class CategoryMetadata(BaseModel):
    """Metadata for category entries."""
    
    length: int = Field(..., description="Content length in characters")
    source: str = Field(..., description="Source of the content (e.g., 'openai')")
    tags: List[str] = Field(default_factory=list, description="List of hashtags")


class CategoryEntry(BaseModel):
    """Individual content entry within a category topic."""
    
    content: str = Field(..., description="The actual content text with hashtags")
    metadata: CategoryMetadata = Field(..., description="Entry metadata")
    created_at: datetime = Field(default_factory=datetime.now, description="Entry creation timestamp")


class CategoryTopic(BaseModel):
    """Topic within a category containing multiple entries."""
    
    topic: str = Field(..., description="Topic name")
    entries: List[CategoryEntry] = Field(default_factory=list, description="List of content entries for this topic")
    
    @field_validator('topic')
    @classmethod
    def validate_topic_name(cls, v: str) -> str:
        """Validate topic name is not empty."""
        if not v.strip():
            raise ValueError("Topic name cannot be empty")
        return v.strip()


class Category(BaseModel):
    """Category model as defined in section 3.1 of the PDR."""
    
    category_id: str = Field(..., description="Unique category identifier")
    name: str = Field(..., description="Human-readable category name")
    description: str = Field(..., description="Category description")
    prompt_template: Optional[str] = Field(None, description="OpenAI prompt template with {topic} placeholder (optional, uses global default if not set)")
    language: str = Field(default="tr", description="Content language")
    created_at: datetime = Field(default_factory=datetime.now, description="Category creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Category last update timestamp")
    topics: List[CategoryTopic] = Field(default_factory=list, description="List of topics in this category")
    
    # Category-specific validation settings (optional overrides)
    min_length: Optional[int] = Field(None, description="Category-specific minimum content length")
    max_length: Optional[int] = Field(None, description="Category-specific maximum content length")
    required_hashtags: Optional[int] = Field(None, description="Category-specific required hashtag count")
    
    @field_validator('category_id')
    @classmethod
    def validate_category_id(cls, v: str) -> str:
        """Validate category ID is not empty and properly formatted."""
        if not v.strip():
            raise ValueError("Category ID cannot be empty")
        # Category IDs should be lowercase with hyphens
        formatted_id = v.strip().lower().replace(' ', '-')
        return formatted_id
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate category name is not empty."""
        if not v.strip():
            raise ValueError("Category name cannot be empty")
        return v.strip()
    
    @field_validator('prompt_template')
    @classmethod
    def validate_prompt_template(cls, v: Optional[str]) -> Optional[str]:
        """Validate prompt template contains {topic} placeholder if provided."""
        if v is None:
            return v  # Allow None, will use global default
        if not v.strip():
            raise ValueError("Prompt template cannot be empty")
        if "{topic}" not in v:
            raise ValueError("Prompt template must contain {topic} placeholder")
        return v.strip()
    
    def has_content_for_topic(self, topic_name: str) -> bool:
        """
        Check if content already exists for a given topic.
        
        Args:
            topic_name: Name of the topic to check
            
        Returns:
            True if topic has at least one entry, False otherwise
        """
        for topic in self.topics:
            if topic.topic.lower() == topic_name.lower():
                return len(topic.entries) > 0
        return False
    
    def get_topic(self, topic_name: str) -> Optional[CategoryTopic]:
        """
        Get a topic by name.
        
        Args:
            topic_name: Name of the topic to retrieve
            
        Returns:
            CategoryTopic if found, None otherwise
        """
        for topic in self.topics:
            if topic.topic.lower() == topic_name.lower():
                return topic
        return None
    
    def add_entry(self, topic_name: str, entry: CategoryEntry) -> None:
        """
        Add an entry to a topic, creating the topic if it doesn't exist.
        
        Args:
            topic_name: Name of the topic
            entry: CategoryEntry to add
        """
        topic = self.get_topic(topic_name)
        if topic is None:
            # Create new topic
            topic = CategoryTopic(topic=topic_name, entries=[])
            self.topics.append(topic)
        
        # Add entry to topic
        topic.entries.append(entry)
        
        # Update category timestamp
        self.updated_at = datetime.now()
    
    def get_all_entries(self) -> List[CategoryEntry]:
        """
        Get all entries from all topics in this category.
        
        Returns:
            List of all CategoryEntry objects
        """
        all_entries = []
        for topic in self.topics:
            all_entries.extend(topic.entries)
        return all_entries
    
    def get_entry_count(self) -> int:
        """
        Get total number of entries across all topics.
        
        Returns:
            Total entry count
        """
        return sum(len(topic.entries) for topic in self.topics)
    
    def get_topic_count(self) -> int:
        """
        Get number of topics in this category.
        
        Returns:
            Topic count
        """
        return len(self.topics)
    
    def get_effective_prompt_template(self, global_template: str) -> str:
        """
        Get the effective prompt template for this category.
        
        Args:
            global_template: Global default template
            
        Returns:
            Prompt template to use (category-specific or global)
        """
        return self.prompt_template if self.prompt_template else global_template
    
    def get_effective_min_length(self, global_min: int) -> int:
        """
        Get the effective minimum length for this category.
        
        Args:
            global_min: Global minimum length
            
        Returns:
            Minimum length to use (category-specific or global)
        """
        return self.min_length if self.min_length is not None else global_min
    
    def get_effective_max_length(self, global_max: int) -> int:
        """
        Get the effective maximum length for this category.
        
        Args:
            global_max: Global maximum length
            
        Returns:
            Maximum length to use (category-specific or global)
        """
        return self.max_length if self.max_length is not None else global_max
    
    def get_effective_required_hashtags(self, global_count: int) -> int:
        """
        Get the effective required hashtag count for this category.
        
        Args:
            global_count: Global required hashtag count
            
        Returns:
            Required hashtag count to use (category-specific or global)
        """
        return self.required_hashtags if self.required_hashtags is not None else global_count 