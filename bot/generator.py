"""
Content generator module for OpenCast Bot.

This module handles content generation using OpenAI API based on 
category templates and topics.
"""

import re
from typing import List, Optional
import asyncio

import openai
from pydantic import BaseModel

from bot.config import Config
from bot.models.category import Category, CategoryEntry, CategoryMetadata
from bot.models.content_seeds import get_seed_manager
from bot.utils import (
    get_logger, LoggerMixin, log_execution_time,
    ContentGenerationError, APIError, ValidationError, 
    RateLimitError, AuthenticationError, NetworkError
)


class ContentGenerator(LoggerMixin):
    """Generator class for creating content using OpenAI API."""
    
    def __init__(self, config: Config) -> None:
        """
        Initialize content generator with configuration.
        
        Args:
            config: Configuration object containing API keys and settings
        """
        super().__init__()
        self.config = config
        
        self.logger.info(
            "ContentGenerator initialized",
            model=config.openai_model,
            max_tokens=config.openai_max_tokens,
            temperature=config.openai_temperature,
            dry_run=config.dry_run
        )
        
        # Configure OpenAI client
        openai.api_key = config.openai_api_key
    
    async def generate_content(
        self, 
        category: Category, 
        topic: str
    ) -> Optional[CategoryEntry]:
        """
        Generate content for a specific category and topic.
        
        Args:
            category: Category object with prompt template
            topic: Topic to generate content for
            
        Returns:
            CategoryEntry if generation successful, None otherwise
        """
        max_retries = self.config.max_retries
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Get effective prompt template
                prompt_template = category.get_effective_prompt_template(self.config.default_prompt_template)
                
                # Generate content using OpenAI
                content_text = await self._call_openai_api(prompt_template, topic)
                
                if not content_text:
                    raise APIError(f"Failed to generate content for topic '{topic}' - empty response")
                
                # Post-process content to fit length requirements
                content_text = self._adjust_content_length(content_text, category)
                
                # Validate content
                if not self._validate_content(content_text, category):
                    raise ValidationError(f"Generated content does not meet requirements: {content_text}")
                
                # Extract hashtags from content
                hashtags = self._extract_hashtags(content_text)
                
                # Create metadata
                metadata = CategoryMetadata(
                    length=len(content_text),
                    source="openai",
                    tags=hashtags
                )
                
                # Create entry
                entry = CategoryEntry(
                    content=content_text,
                    metadata=metadata
                )
                
                self.logger.info(f"Successfully generated content for topic '{topic}': {content_text[:50]}...")
                return entry
                
            except APIError as e:
                retry_count += 1
                self.logger.warning(f"API error (attempt {retry_count}/{max_retries}): {str(e)}")
                if retry_count < max_retries:
                    await asyncio.sleep(self.config.retry_delay * retry_count)  # Exponential backoff
                    continue
                else:
                    self.logger.error(f"Max retries exceeded for topic '{topic}': {str(e)}")
                    return None
                    
            except ValidationError as e:
                self.logger.error(f"Validation error for topic '{topic}': {str(e)}")
                return None
                
            except Exception as e:
                retry_count += 1
                self.logger.error(f"Unexpected error (attempt {retry_count}/{max_retries}) for topic '{topic}': {str(e)}")
                if retry_count < max_retries:
                    await asyncio.sleep(self.config.retry_delay * retry_count)
                    continue
                else:
                    self.logger.error(f"Max retries exceeded for topic '{topic}' due to unexpected errors")
                    return None
        
        return None
    
    async def _call_openai_api(self, prompt_template: str, topic: str) -> Optional[str]:
        """
        Call OpenAI API to generate content.
        
        Args:
            prompt_template: Template with {topic} placeholder
            topic: Topic to substitute in template
            
        Returns:
            Generated content text or None if failed
            
        Raises:
            APIError: If API call fails
        """
        try:
            # Get a random content seed for variety
            seed_manager = get_seed_manager()
            seed = seed_manager.get_random_seed()
            
            # Apply seed to enhance the prompt
            enhanced_prompt = seed.apply_to_prompt(prompt_template)
            
            # Format prompt with topic
            prompt = enhanced_prompt.format(topic=topic)
            
            self.logger.debug(f"Generating content with enhanced prompt (tone: {seed.tone.value}, style: {seed.style.value}): {prompt[:100]}...")
            
            # Check if using placeholder API key
            if self.config.openai_api_key == "sk-placeholder-for-development":
                self.logger.warning("Using placeholder OpenAI API key - returning mock content")
                return f"This is a placeholder content generated for the topic '{topic}'. It demonstrates the content generation system with proper length and formatting requirements perfectly! #placeholder #demo"
            
            # Make actual OpenAI API call
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=self.config.openai_api_key)
            
            response = await client.chat.completions.create(
                model=self.config.openai_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.config.openai_max_tokens,
                temperature=self.config.openai_temperature
            )
            
            if response.choices and response.choices[0].message:
                content = response.choices[0].message.content.strip()
                self.logger.info(f"OpenAI API returned content: {content[:50]}...")
                return content
            else:
                raise APIError("OpenAI API returned empty response")
            
        except Exception as e:
            if "rate limit" in str(e).lower():
                raise APIError(f"OpenAI API rate limit exceeded: {str(e)}")
            elif "quota" in str(e).lower():
                raise APIError(f"OpenAI API quota exceeded: {str(e)}")
            elif "authentication" in str(e).lower():
                raise APIError(f"OpenAI API authentication failed: {str(e)}")
            else:
                raise APIError(f"OpenAI API call failed: {str(e)}")
    
    def _validate_content(self, content: str, category: Category) -> bool:
        """
        Validate generated content meets requirements.
        
        Args:
            content: Generated content to validate
            category: Category object
            
        Returns:
            True if content is valid, False otherwise
        """
        try:
            # Get effective validation settings
            min_length = category.get_effective_min_length(self.config.content_min_length)
            max_length = category.get_effective_max_length(self.config.content_max_length)
            required_hashtags = category.get_effective_required_hashtags(self.config.required_hashtag_count)
            
            # Check length
            content_length = len(content)
            if not (min_length <= content_length <= max_length):
                self.logger.warning(
                    "Content length validation failed",
                    content_length=content_length,
                    min_length=min_length,
                    max_length=max_length,
                    content_preview=content[:50] + "..."
                )
                return False
            
            # Check hashtag count
            hashtags = self._extract_hashtags(content)
            hashtag_count = len(hashtags)
            if hashtag_count != required_hashtags:
                self.logger.warning(
                    "Hashtag count validation failed",
                    expected_hashtags=required_hashtags,
                    found_hashtags=hashtag_count,
                    hashtags=hashtags,
                    content_preview=content[:50] + "..."
                )
                return False
            
            self.logger.debug(
                "Content validation successful",
                content_length=content_length,
                hashtag_count=hashtag_count,
                hashtags=hashtags
            )
            
            return True
            
        except Exception as e:
            validation_error = ValidationError(
                "Error during content validation",
                field_name="content",
                field_value=content[:100],
                cause=e
            )
            self.logger.error("Content validation error", error=validation_error)
            return False
    
    def _extract_hashtags(self, content: str) -> List[str]:
        """
        Extract hashtags from content text.
        
        Args:
            content: Content text to extract hashtags from
            
        Returns:
            List of hashtags found in content
        """
        try:
            # Find all hashtags using regex
            hashtag_pattern = r'#\w+'
            hashtags = re.findall(hashtag_pattern, content)
            
            self.logger.debug(
                "Hashtags extracted",
                hashtag_count=len(hashtags),
                hashtags=hashtags
            )
            
            return hashtags
            
        except Exception as e:
            self.logger.error(
                "Error extracting hashtags",
                error=e,
                content_preview=content[:100] + "..."
            )
            return []

    def _adjust_content_length(self, content: str, category: Category) -> str:
        """
        Adjust content length to fit within the specified range.
        
        Args:
            content: Generated content to adjust
            category: Category object
            
        Returns:
            Adjusted content text
        """
        try:
            original_length = len(content)
            
            # Get effective length settings
            max_length = category.get_effective_max_length(self.config.content_max_length)
            
            # Extract hashtags first
            hashtags = self._extract_hashtags(content)
            
            # Remove hashtags from content to work with main text
            main_text = content
            for hashtag in hashtags:
                main_text = main_text.replace(hashtag, "").strip()
            
            # Calculate target length (total - hashtags - spaces)
            hashtag_length = sum(len(tag) for tag in hashtags) + len(hashtags)  # +1 space per hashtag
            target_main_length = max_length - hashtag_length - 1  # -1 for space before hashtags
            
            # Adjust main text length if too long
            if len(main_text) > target_main_length:
                # Truncate at word boundary
                words = main_text.split()
                truncated = ""
                for word in words:
                    if len(truncated + " " + word) <= target_main_length:
                        truncated += (" " + word) if truncated else word
                    else:
                        break
                main_text = truncated
                
                self.logger.info(
                    "Content truncated to fit length requirements",
                    original_main_length=len(content) - hashtag_length,
                    target_main_length=target_main_length,
                    truncated_main_length=len(main_text)
                )
            
            # Reconstruct content
            if hashtags:
                adjusted_content = f"{main_text} {' '.join(hashtags)}"
            else:
                adjusted_content = main_text
            
            final_length = len(adjusted_content)
            
            self.logger.debug(
                "Content length adjustment completed",
                original_length=original_length,
                final_length=final_length,
                max_length=max_length,
                hashtag_count=len(hashtags),
                was_truncated=original_length != final_length
            )
            
            return adjusted_content
            
        except Exception as e:
            self.logger.error(
                "Error adjusting content length",
                error=e,
                content_preview=content[:100] + "...",
                max_length=category.get_effective_max_length(self.config.content_max_length)
            )
            # Return original content if adjustment fails
            return content 