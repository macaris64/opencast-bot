"""
Tests for category models in OpenCast Bot.

This module tests the Category, CategoryTopic, CategoryEntry, and CategoryMetadata models
defined in bot/models/category.py.
"""

from datetime import datetime
import pytest
from pydantic import ValidationError

from bot.models.category import (
    Category,
    CategoryTopic,
    CategoryEntry,
    CategoryMetadata
)


class TestCategoryMetadata:
    """Test cases for CategoryMetadata model."""
    
    def test_metadata_creation(self):
        """Test creating category metadata."""
        metadata = CategoryMetadata(
            length=180,
            source="openai",
            tags=["#test", "#metadata"]
        )
        
        assert metadata.length == 180
        assert metadata.source == "openai"
        assert metadata.tags == ["#test", "#metadata"]
    
    def test_metadata_with_empty_tags(self):
        """Test creating metadata with empty tags list."""
        metadata = CategoryMetadata(
            length=180,
            source="openai"
        )
        
        assert metadata.tags == []


class TestCategoryEntry:
    """Test cases for CategoryEntry model."""
    
    def test_entry_creation(self):
        """Test creating a category entry."""
        metadata = CategoryMetadata(
            length=180,
            source="openai",
            tags=["#test", "#entry"]
        )
        
        entry = CategoryEntry(
            content="Test content with hashtags #test #entry",
            metadata=metadata
        )
        
        assert entry.content == "Test content with hashtags #test #entry"
        assert entry.metadata == metadata
        assert isinstance(entry.created_at, datetime)
    
    def test_entry_creation_with_custom_timestamp(self):
        """Test creating entry with custom timestamp."""
        custom_time = datetime(2024, 1, 1, 12, 0, 0)
        metadata = CategoryMetadata(length=180, source="test", tags=[])
        
        entry = CategoryEntry(
            content="Test content",
            metadata=metadata,
            created_at=custom_time
        )
        
        assert entry.created_at == custom_time


class TestCategoryTopic:
    """Test cases for CategoryTopic model."""
    
    def test_topic_creation_empty(self):
        """Test creating an empty topic."""
        topic = CategoryTopic(topic="Test Topic")
        
        assert topic.topic == "Test Topic"
        assert topic.entries == []
    
    def test_topic_creation_with_entries(self):
        """Test creating topic with entries."""
        metadata = CategoryMetadata(length=180, source="test", tags=[])
        entry = CategoryEntry(content="Test content", metadata=metadata)
        
        topic = CategoryTopic(
            topic="Test Topic",
            entries=[entry]
        )
        
        assert topic.topic == "Test Topic"
        assert len(topic.entries) == 1
        assert topic.entries[0] == entry
    
    def test_topic_name_validation_empty(self):
        """Test that empty topic names are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            CategoryTopic(topic="")
        
        errors = exc_info.value.errors()
        assert any("empty" in str(error["msg"]).lower() for error in errors)
    
    def test_topic_name_validation_whitespace(self):
        """Test that whitespace-only topic names are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            CategoryTopic(topic="   ")
        
        errors = exc_info.value.errors()
        assert any("empty" in str(error["msg"]).lower() for error in errors)
    
    def test_topic_name_strips_whitespace(self):
        """Test that topic names are stripped of whitespace."""
        topic = CategoryTopic(topic="  Test Topic  ")
        assert topic.topic == "Test Topic"


class TestCategory:
    """Test cases for Category model."""
    
    def test_category_creation_minimal(self):
        """Test creating category with minimal required fields."""
        category = Category(
            category_id="test-category",
            name="Test Category",
            description="Test description",
            prompt_template="Generate content about {topic}."
        )
        
        assert category.category_id == "test-category"
        assert category.name == "Test Category"
        assert category.description == "Test description"
        assert category.prompt_template == "Generate content about {topic}."
        assert category.language == "tr"  # Default value
        assert category.topics == []
        assert isinstance(category.created_at, datetime)
        assert isinstance(category.updated_at, datetime)
    
    def test_category_creation_full(self):
        """Test creating category with all fields."""
        created_time = datetime(2024, 1, 1, 12, 0, 0)
        updated_time = datetime(2024, 1, 2, 12, 0, 0)
        
        topic = CategoryTopic(topic="Test Topic")
        
        category = Category(
            category_id="test-category",
            name="Test Category",
            description="Test description",
            prompt_template="Generate content about {topic}.",
            language="en",
            created_at=created_time,
            updated_at=updated_time,
            topics=[topic]
        )
        
        assert category.language == "en"
        assert category.created_at == created_time
        assert category.updated_at == updated_time
        assert len(category.topics) == 1
        assert category.topics[0] == topic
    
    def test_category_id_validation_empty(self):
        """Test that empty category IDs are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Category(
                category_id="",
                name="Test",
                description="Test",
                prompt_template="Test {topic}"
            )
        
        errors = exc_info.value.errors()
        assert any("empty" in str(error["msg"]).lower() for error in errors)
    
    def test_category_id_formatting(self):
        """Test that category IDs are properly formatted."""
        category = Category(
            category_id="Test Category ID",
            name="Test",
            description="Test",
            prompt_template="Test {topic}"
        )
        
        assert category.category_id == "test-category-id"
    
    def test_name_validation_empty(self):
        """Test that empty names are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Category(
                category_id="test",
                name="",
                description="Test",
                prompt_template="Test {topic}"
            )
        
        errors = exc_info.value.errors()
        assert any("empty" in str(error["msg"]).lower() for error in errors)
    
    def test_name_strips_whitespace(self):
        """Test that names are stripped of whitespace."""
        category = Category(
            category_id="test",
            name="  Test Category  ",
            description="Test",
            prompt_template="Test {topic}"
        )
        
        assert category.name == "Test Category"
    
    def test_prompt_template_validation_empty(self):
        """Test that empty prompt templates are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Category(
                category_id="test",
                name="Test",
                description="Test",
                prompt_template=""
            )
        
        errors = exc_info.value.errors()
        assert any("empty" in str(error["msg"]).lower() for error in errors)
    
    def test_prompt_template_validation_missing_placeholder(self):
        """Test that prompt templates without {topic} are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Category(
                category_id="test",
                name="Test",
                description="Test",
                prompt_template="Generate content without placeholder"
            )
        
        errors = exc_info.value.errors()
        assert any("placeholder" in str(error["msg"]).lower() for error in errors)
    
    def test_has_content_for_topic_empty(self):
        """Test has_content_for_topic with no topics."""
        category = Category(
            category_id="test",
            name="Test",
            description="Test",
            prompt_template="Test {topic}"
        )
        
        assert category.has_content_for_topic("Any Topic") is False
    
    def test_has_content_for_topic_with_empty_topic(self):
        """Test has_content_for_topic with empty topic."""
        topic = CategoryTopic(topic="Test Topic")
        category = Category(
            category_id="test",
            name="Test",
            description="Test",
            prompt_template="Test {topic}",
            topics=[topic]
        )
        
        assert category.has_content_for_topic("Test Topic") is False
    
    def test_has_content_for_topic_with_content(self):
        """Test has_content_for_topic with content."""
        metadata = CategoryMetadata(length=180, source="test", tags=[])
        entry = CategoryEntry(content="Test content", metadata=metadata)
        topic = CategoryTopic(topic="Test Topic", entries=[entry])
        
        category = Category(
            category_id="test",
            name="Test",
            description="Test",
            prompt_template="Test {topic}",
            topics=[topic]
        )
        
        assert category.has_content_for_topic("Test Topic") is True
        assert category.has_content_for_topic("test topic") is True  # Case insensitive
        assert category.has_content_for_topic("Other Topic") is False
    
    def test_get_topic_existing(self):
        """Test getting an existing topic."""
        topic = CategoryTopic(topic="Test Topic")
        category = Category(
            category_id="test",
            name="Test",
            description="Test",
            prompt_template="Test {topic}",
            topics=[topic]
        )
        
        found_topic = category.get_topic("Test Topic")
        assert found_topic == topic
        
        # Test case insensitive
        found_topic = category.get_topic("test topic")
        assert found_topic == topic
    
    def test_get_topic_nonexistent(self):
        """Test getting a non-existent topic."""
        category = Category(
            category_id="test",
            name="Test",
            description="Test",
            prompt_template="Test {topic}"
        )
        
        found_topic = category.get_topic("Nonexistent Topic")
        assert found_topic is None
    
    def test_add_entry_new_topic(self):
        """Test adding entry to a new topic."""
        category = Category(
            category_id="test",
            name="Test",
            description="Test",
            prompt_template="Test {topic}"
        )
        
        metadata = CategoryMetadata(length=180, source="test", tags=[])
        entry = CategoryEntry(content="Test content", metadata=metadata)
        
        original_updated_at = category.updated_at
        category.add_entry("New Topic", entry)
        
        assert len(category.topics) == 1
        assert category.topics[0].topic == "New Topic"
        assert len(category.topics[0].entries) == 1
        assert category.topics[0].entries[0] == entry
        assert category.updated_at > original_updated_at
    
    def test_add_entry_existing_topic(self):
        """Test adding entry to existing topic."""
        topic = CategoryTopic(topic="Existing Topic")
        category = Category(
            category_id="test",
            name="Test",
            description="Test",
            prompt_template="Test {topic}",
            topics=[topic]
        )
        
        metadata = CategoryMetadata(length=180, source="test", tags=[])
        entry = CategoryEntry(content="Test content", metadata=metadata)
        
        category.add_entry("Existing Topic", entry)
        
        assert len(category.topics) == 1  # No new topic created
        assert len(category.topics[0].entries) == 1
        assert category.topics[0].entries[0] == entry
    
    def test_get_all_entries_empty(self):
        """Test getting all entries from empty category."""
        category = Category(
            category_id="test",
            name="Test",
            description="Test",
            prompt_template="Test {topic}"
        )
        
        entries = category.get_all_entries()
        assert entries == []
    
    def test_get_all_entries_multiple_topics(self):
        """Test getting all entries from multiple topics."""
        metadata1 = CategoryMetadata(length=180, source="test", tags=[])
        entry1 = CategoryEntry(content="Content 1", metadata=metadata1)
        topic1 = CategoryTopic(topic="Topic 1", entries=[entry1])
        
        metadata2 = CategoryMetadata(length=181, source="test", tags=[])
        entry2 = CategoryEntry(content="Content 2", metadata=metadata2)
        metadata3 = CategoryMetadata(length=182, source="test", tags=[])
        entry3 = CategoryEntry(content="Content 3", metadata=metadata3)
        topic2 = CategoryTopic(topic="Topic 2", entries=[entry2, entry3])
        
        category = Category(
            category_id="test",
            name="Test",
            description="Test",
            prompt_template="Test {topic}",
            topics=[topic1, topic2]
        )
        
        entries = category.get_all_entries()
        assert len(entries) == 3
        assert entry1 in entries
        assert entry2 in entries
        assert entry3 in entries
    
    def test_get_entry_count(self):
        """Test getting total entry count."""
        metadata = CategoryMetadata(length=180, source="test", tags=[])
        entry1 = CategoryEntry(content="Content 1", metadata=metadata)
        entry2 = CategoryEntry(content="Content 2", metadata=metadata)
        entry3 = CategoryEntry(content="Content 3", metadata=metadata)
        
        topic1 = CategoryTopic(topic="Topic 1", entries=[entry1])
        topic2 = CategoryTopic(topic="Topic 2", entries=[entry2, entry3])
        
        category = Category(
            category_id="test",
            name="Test",
            description="Test",
            prompt_template="Test {topic}",
            topics=[topic1, topic2]
        )
        
        assert category.get_entry_count() == 3
    
    def test_get_topic_count(self):
        """Test getting topic count."""
        topic1 = CategoryTopic(topic="Topic 1")
        topic2 = CategoryTopic(topic="Topic 2")
        
        category = Category(
            category_id="test",
            name="Test",
            description="Test",
            prompt_template="Test {topic}",
            topics=[topic1, topic2]
        )
        
        assert category.get_topic_count() == 2 