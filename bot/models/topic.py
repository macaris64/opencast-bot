"""
Topic and post model definitions for OpenCast Bot.

This module defines models for topics and the post structure
as defined in section 10 of the PDR document.
"""

from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class PostStatus(str, Enum):
    """Enumeration of possible post statuses."""
    
    POSTED = "posted"
    FAILED = "failed"
    PENDING = "pending"
    DRAFT = "draft"


class PlatformType(str, Enum):
    """Enumeration of supported social media platforms."""
    
    X = "x"
    TELEGRAM = "telegram"


class TopicEntry(BaseModel):
    """Individual topic entry with basic metadata."""
    
    name: str = Field(..., description="Topic name")
    description: Optional[str] = Field(None, description="Optional topic description")
    created_at: datetime = Field(default_factory=datetime.now, description="Topic creation timestamp")
    is_active: bool = Field(default=True, description="Whether the topic is active for content generation")


class Topic(BaseModel):
    """Topic model representing a content topic."""
    
    name: str = Field(..., description="Topic name")
    category_id: str = Field(..., description="Associated category identifier")
    description: Optional[str] = Field(None, description="Topic description")
    keywords: List[str] = Field(default_factory=list, description="Keywords associated with the topic")
    created_at: datetime = Field(default_factory=datetime.now, description="Topic creation timestamp")
    is_active: bool = Field(default=True, description="Whether the topic is active")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate topic name is not empty."""
        if not v.strip():
            raise ValueError("Topic name cannot be empty")
        return v.strip()


class PostContent(BaseModel):
    """Post content structure for X and Telegram as defined in section 10 of the PDR."""
    
    content: str = Field(..., description="The actual content text with hashtags")
    platform: PlatformType = Field(..., description="Target platform for the post")
    category_id: str = Field(..., description="Category identifier")
    topic: str = Field(..., description="Topic name")
    hashtags: List[str] = Field(..., description="List of hashtags (exactly 2 required)")
    post_time: datetime = Field(default_factory=datetime.now, description="Time when the post was made")
    status: PostStatus = Field(default=PostStatus.PENDING, description="Post status")
    
    @field_validator('content')
    @classmethod
    def validate_content_length(cls, v: str) -> str:
        """Validate content is between 20-220 characters including hashtags."""
        if not (20 <= len(v) <= 220):
            raise ValueError("Content must be between 20-220 characters including hashtags")
        return v
    
    @field_validator('hashtags')
    @classmethod
    def validate_hashtags_count(cls, v: List[str]) -> List[str]:
        """Validate exactly 2 hashtags are provided."""
        if len(v) != 2:
            raise ValueError("Exactly 2 hashtags are required")
        
        # Ensure hashtags start with #
        for i, tag in enumerate(v):
            if not tag.startswith('#'):
                v[i] = f"#{tag}"
        
        return v
    
    @field_validator('topic')
    @classmethod
    def validate_topic_name(cls, v: str) -> str:
        """Validate topic name is not empty."""
        if not v.strip():
            raise ValueError("Topic name cannot be empty")
        return v.strip()
    
    def mark_as_posted(self) -> None:
        """Mark the post as successfully posted."""
        self.status = PostStatus.POSTED
        self.post_time = datetime.now()
    
    def mark_as_failed(self) -> None:
        """Mark the post as failed."""
        self.status = PostStatus.FAILED
        self.post_time = datetime.now() 