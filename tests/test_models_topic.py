"""
Tests for topic models in OpenCast Bot.

This module tests the Topic, TopicEntry, and PostContent models
defined in bot/models/topic.py.
"""

from datetime import datetime
from typing import List

import pytest
from pydantic import ValidationError

from bot.models.topic import (
    Topic,
    TopicEntry,
    PostContent,
    PostStatus,
    PlatformType
)


class TestTopicEntry:
    """Test cases for TopicEntry model."""
    
    def test_topic_entry_creation_with_defaults(self):
        """Test creating a topic entry with default values."""
        entry = TopicEntry(name="Test Topic")
        
        assert entry.name == "Test Topic"
        assert entry.description is None
        assert entry.is_active is True
        assert isinstance(entry.created_at, datetime)
    
    def test_topic_entry_creation_with_all_fields(self):
        """Test creating a topic entry with all fields specified."""
        created_time = datetime.now()
        entry = TopicEntry(
            name="Test Topic",
            description="Test description",
            created_at=created_time,
            is_active=False
        )
        
        assert entry.name == "Test Topic"
        assert entry.description == "Test description"
        assert entry.created_at == created_time
        assert entry.is_active is False


class TestTopic:
    """Test cases for Topic model."""
    
    def test_topic_creation_with_defaults(self):
        """Test creating a topic with default values."""
        topic = Topic(
            name="Code Comments",
            category_id="dev-one-liners"
        )
        
        assert topic.name == "Code Comments"
        assert topic.category_id == "dev-one-liners"
        assert topic.description is None
        assert topic.keywords == []
        assert topic.is_active is True
        assert isinstance(topic.created_at, datetime)
    
    def test_topic_creation_with_all_fields(self):
        """Test creating a topic with all fields specified."""
        created_time = datetime.now()
        keywords = ["code", "comments", "development"]
        
        topic = Topic(
            name="Code Comments",
            category_id="dev-one-liners",
            description="Tips about code comments",
            keywords=keywords,
            created_at=created_time,
            is_active=False
        )
        
        assert topic.name == "Code Comments"
        assert topic.category_id == "dev-one-liners"
        assert topic.description == "Tips about code comments"
        assert topic.keywords == keywords
        assert topic.created_at == created_time
        assert topic.is_active is False
    
    def test_topic_name_validation_empty(self):
        """Test that empty topic names are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Topic(name="", category_id="dev-one-liners")
        
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "value_error"
        assert "empty" in str(errors[0]["msg"]).lower()
    
    def test_topic_name_validation_whitespace(self):
        """Test that whitespace-only names are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Topic(name="   ", category_id="dev-one-liners")
        
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "value_error"
    
    def test_topic_name_strips_whitespace(self):
        """Test that topic names are stripped of whitespace."""
        topic = Topic(name="  Code Comments  ", category_id="dev-one-liners")
        assert topic.name == "Code Comments"


class TestPostContent:
    """Test cases for PostContent model."""
    
    def test_post_content_creation_valid(self):
        """Test creating valid post content."""
        # Create content exactly 180 characters
        content = "If your code needs comments to be understood, it probably isn't clear enough. Write self-documenting code instead. #cleancode #development"
        # Adjust to exactly 180 characters
        content = "x" * 171 + " #cleancode #development"  # 171 + 1 + 10 + 1 + 11 = 194 chars
        hashtags = ["#cleancode", "#development"]
        
        post = PostContent(
            content=content,
            platform=PlatformType.X,
            category_id="dev-one-liners",
            topic="Code Comments",
            hashtags=hashtags
        )
        
        assert post.content == content
        assert post.platform == PlatformType.X
        assert post.category_id == "dev-one-liners"
        assert post.topic == "Code Comments"
        assert post.hashtags == hashtags
        assert post.status == PostStatus.PENDING
        assert isinstance(post.post_time, datetime)
    
    def test_post_content_length_validation_too_short(self):
        """Test that content shorter than 20 characters is rejected."""
        short_content = "Short #a #b"  # Less than 20 chars
        
        with pytest.raises(ValidationError) as exc_info:
            PostContent(
                content=short_content,
                platform=PlatformType.X,
                category_id="dev-one-liners",
                topic="Test Topic",
                hashtags=["#a", "#b"]
            )
        
        errors = exc_info.value.errors()
        assert any("20-220 characters" in str(error["msg"]) for error in errors)
    
    def test_post_content_length_validation_too_long(self):
        """Test that content longer than 220 characters is rejected."""
        long_content = "x" * 221  # More than 220 chars
        
        with pytest.raises(ValidationError) as exc_info:
            PostContent(
                content=long_content,
                platform=PlatformType.X,
                category_id="dev-one-liners",
                topic="Test Topic",
                hashtags=["#hash", "#tag"]
            )
        
        errors = exc_info.value.errors()
        assert any("20-220 characters" in str(error["msg"]) for error in errors)
    
    def test_post_content_length_validation_valid_range(self):
        """Test that content in 20-220 character range is accepted."""
        # Create content exactly 20 characters: "x" * 9 + " #hash #tag" = 9 + 1 + 5 + 1 + 4 = 20
        content_20 = "x" * 9 + " #hash #tag"  # 20 chars
        # Create content exactly 220 characters: "x" * 209 + " #hash #tag" = 209 + 1 + 5 + 1 + 4 = 220
        content_220 = "x" * 209 + " #hash #tag"  # 220 chars
        
        # Should not raise
        post_20 = PostContent(
            content=content_20,
            platform=PlatformType.X,
            category_id="dev-one-liners",
            topic="Test Topic",
            hashtags=["#hash", "#tag"]
        )
        
        post_220 = PostContent(
            content=content_220,
            platform=PlatformType.X,
            category_id="dev-one-liners",
            topic="Test Topic",
            hashtags=["#hash", "#tag"]
        )
        
        assert len(post_20.content) == 20
        assert len(post_220.content) == 220
    
    def test_hashtags_count_validation_too_few(self):
        """Test that fewer than 2 hashtags are rejected."""
        content = "Valid length content here #hash"  # Valid length, 1 hashtag
        
        with pytest.raises(ValidationError) as exc_info:
            PostContent(
                content=content,
                platform=PlatformType.X,
                category_id="dev-one-liners",
                topic="Test Topic",
                hashtags=["#hash"]
            )
        
        errors = exc_info.value.errors()
        assert any("Exactly 2 hashtags" in str(error["msg"]) for error in errors)
    
    def test_hashtags_count_validation_too_many(self):
        """Test that more than 2 hashtags are rejected."""
        content = "Valid length content here #hash #tag #extra"  # Valid length, 3 hashtags
        
        with pytest.raises(ValidationError) as exc_info:
            PostContent(
                content=content,
                platform=PlatformType.X,
                category_id="dev-one-liners",
                topic="Test Topic",
                hashtags=["#hash", "#tag", "#extra"]
            )
        
        errors = exc_info.value.errors()
        assert any("Exactly 2 hashtags" in str(error["msg"]) for error in errors)
    
    def test_hashtags_auto_prefix(self):
        """Test that hashtags without # are automatically prefixed."""
        content = "Valid length content here #hash #tag"
        
        post = PostContent(
            content=content,
            platform=PlatformType.X,
            category_id="dev-one-liners",
            topic="Test Topic",
            hashtags=["hash", "tag"]  # Without # prefix
        )
        
        assert post.hashtags == ["#hash", "#tag"]
    
    def test_topic_name_validation_empty(self):
        """Test that empty topic names are rejected."""
        content = "x" * 171 + " #hash #tag"
        
        with pytest.raises(ValidationError) as exc_info:
            PostContent(
                content=content,
                platform=PlatformType.X,
                category_id="dev-one-liners",
                topic="",
                hashtags=["#hash", "#tag"]
            )
        
        errors = exc_info.value.errors()
        assert any("empty" in str(error["msg"]).lower() for error in errors)
    
    def test_topic_name_strips_whitespace(self):
        """Test that topic names are stripped of whitespace."""
        content = "x" * 171 + " #hash #tag"
        
        post = PostContent(
            content=content,
            platform=PlatformType.X,
            category_id="dev-one-liners",
            topic="  Code Comments  ",
            hashtags=["#hash", "#tag"]
        )
        
        assert post.topic == "Code Comments"
    
    def test_mark_as_posted(self):
        """Test marking post as posted."""
        content = "x" * 171 + " #hash #tag"
        
        post = PostContent(
            content=content,
            platform=PlatformType.X,
            category_id="dev-one-liners",
            topic="Test Topic",
            hashtags=["#hash", "#tag"]
        )
        
        original_time = post.post_time
        post.mark_as_posted()
        
        assert post.status == PostStatus.POSTED
        assert post.post_time >= original_time
    
    def test_mark_as_failed(self):
        """Test marking post as failed."""
        content = "x" * 171 + " #hash #tag"
        
        post = PostContent(
            content=content,
            platform=PlatformType.X,
            category_id="dev-one-liners",
            topic="Test Topic",
            hashtags=["#hash", "#tag"]
        )
        
        original_time = post.post_time
        post.mark_as_failed()
        
        assert post.status == PostStatus.FAILED
        assert post.post_time >= original_time


class TestEnums:
    """Test cases for enum classes."""
    
    def test_post_status_values(self):
        """Test PostStatus enum values."""
        assert PostStatus.POSTED == "posted"
        assert PostStatus.FAILED == "failed"
        assert PostStatus.PENDING == "pending"
        assert PostStatus.DRAFT == "draft"
    
    def test_platform_type_values(self):
        """Test PlatformType enum values."""
        assert PlatformType.X == "x"
        assert PlatformType.TELEGRAM == "telegram" 