"""
Content seeds system for generating diverse content variations.

This module provides different writing styles, tones, and approaches
to make generated content more varied and interesting.
"""

import random
from typing import List, Dict, Any
from enum import Enum


class WritingTone(Enum):
    """Different writing tones for content generation."""
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    ENTHUSIASTIC = "enthusiastic"
    ANALYTICAL = "analytical"
    PRACTICAL = "practical"
    INSPIRATIONAL = "inspirational"
    DIRECT = "direct"
    CONVERSATIONAL = "conversational"
    EXPERT = "expert"
    BEGINNER_FRIENDLY = "beginner_friendly"


class ContentStyle(Enum):
    """Different content styles and approaches."""
    TIP = "tip"
    WARNING = "warning"
    BEST_PRACTICE = "best_practice"
    COMMON_MISTAKE = "common_mistake"
    QUICK_WIN = "quick_win"
    DEEP_INSIGHT = "deep_insight"
    COMPARISON = "comparison"
    STEP_BY_STEP = "step_by_step"
    QUESTION = "question"
    FACT = "fact"


class ContentSeed:
    """A seed configuration for content generation."""
    
    def __init__(
        self,
        tone: WritingTone,
        style: ContentStyle,
        prefix: str = "",
        suffix: str = "",
        approach: str = "",
        length_preference: str = "medium"
    ):
        self.tone = tone
        self.style = style
        self.prefix = prefix
        self.suffix = suffix
        self.approach = approach
        self.length_preference = length_preference
    
    def apply_to_prompt(self, base_prompt: str) -> str:
        """Apply this seed to a base prompt template."""
        # Add tone and style instructions
        enhanced_prompt = f"{base_prompt}\n\n"
        enhanced_prompt += f"Writing tone: {self.tone.value}\n"
        enhanced_prompt += f"Content style: {self.style.value}\n"
        
        if self.approach:
            enhanced_prompt += f"Approach: {self.approach}\n"
        
        if self.prefix:
            enhanced_prompt += f"Start with: {self.prefix}\n"
        
        if self.suffix:
            enhanced_prompt += f"End with: {self.suffix}\n"
        
        enhanced_prompt += f"Length preference: {self.length_preference}"
        
        return enhanced_prompt


class ContentSeedManager:
    """Manages and provides content seeds for variety."""
    
    def __init__(self):
        self.seeds = self._create_seed_collection()
    
    def _create_seed_collection(self) -> List[ContentSeed]:
        """Create a diverse collection of content seeds."""
        seeds = []
        
        # Professional tips
        seeds.extend([
            ContentSeed(
                WritingTone.PROFESSIONAL,
                ContentStyle.TIP,
                approach="Focus on industry best practices and proven methods"
            ),
            ContentSeed(
                WritingTone.PROFESSIONAL,
                ContentStyle.BEST_PRACTICE,
                approach="Emphasize standards and methodologies"
            ),
            ContentSeed(
                WritingTone.ANALYTICAL,
                ContentStyle.DEEP_INSIGHT,
                approach="Provide technical depth and reasoning"
            ),
        ])
        
        # Practical advice
        seeds.extend([
            ContentSeed(
                WritingTone.PRACTICAL,
                ContentStyle.QUICK_WIN,
                prefix="Pro tip:",
                approach="Focus on immediate actionable benefits"
            ),
            ContentSeed(
                WritingTone.DIRECT,
                ContentStyle.STEP_BY_STEP,
                approach="Give clear, concise instructions"
            ),
            ContentSeed(
                WritingTone.PRACTICAL,
                ContentStyle.COMMON_MISTAKE,
                prefix="Avoid this:",
                approach="Highlight what not to do and why"
            ),
        ])
        
        # Engaging styles
        seeds.extend([
            ContentSeed(
                WritingTone.ENTHUSIASTIC,
                ContentStyle.TIP,
                prefix="Game changer:",
                approach="Show excitement about the benefits"
            ),
            ContentSeed(
                WritingTone.CONVERSATIONAL,
                ContentStyle.QUESTION,
                approach="Start with a thought-provoking question"
            ),
            ContentSeed(
                WritingTone.INSPIRATIONAL,
                ContentStyle.BEST_PRACTICE,
                approach="Motivate and encourage adoption"
            ),
        ])
        
        # Expert insights
        seeds.extend([
            ContentSeed(
                WritingTone.EXPERT,
                ContentStyle.DEEP_INSIGHT,
                approach="Share advanced knowledge and experience"
            ),
            ContentSeed(
                WritingTone.EXPERT,
                ContentStyle.COMPARISON,
                approach="Compare different approaches or tools"
            ),
            ContentSeed(
                WritingTone.ANALYTICAL,
                ContentStyle.FACT,
                approach="Present data-driven insights"
            ),
        ])
        
        # Beginner-friendly
        seeds.extend([
            ContentSeed(
                WritingTone.BEGINNER_FRIENDLY,
                ContentStyle.TIP,
                prefix="New to this?",
                approach="Explain concepts simply and clearly"
            ),
            ContentSeed(
                WritingTone.BEGINNER_FRIENDLY,
                ContentStyle.STEP_BY_STEP,
                approach="Break down complex topics into simple steps"
            ),
        ])
        
        # Warning and caution styles
        seeds.extend([
            ContentSeed(
                WritingTone.DIRECT,
                ContentStyle.WARNING,
                prefix="Important:",
                approach="Highlight critical considerations"
            ),
            ContentSeed(
                WritingTone.PROFESSIONAL,
                ContentStyle.WARNING,
                prefix="Remember:",
                approach="Emphasize key points to avoid issues"
            ),
        ])
        
        # Casual and conversational
        seeds.extend([
            ContentSeed(
                WritingTone.CASUAL,
                ContentStyle.TIP,
                approach="Use friendly, approachable language"
            ),
            ContentSeed(
                WritingTone.CONVERSATIONAL,
                ContentStyle.QUICK_WIN,
                prefix="Quick tip:",
                approach="Share helpful shortcuts or tricks"
            ),
        ])
        
        return seeds
    
    def get_random_seed(self) -> ContentSeed:
        """Get a random content seed."""
        return random.choice(self.seeds)
    
    def get_seed_for_category(self, category_id: str) -> ContentSeed:
        """Get a seed that's appropriate for a specific category."""
        # For now, return random seed
        # In the future, we could have category-specific seed preferences
        return self.get_random_seed()
    
    def get_seeds_by_tone(self, tone: WritingTone) -> List[ContentSeed]:
        """Get all seeds with a specific tone."""
        return [seed for seed in self.seeds if seed.tone == tone]
    
    def get_seeds_by_style(self, style: ContentStyle) -> List[ContentSeed]:
        """Get all seeds with a specific style."""
        return [seed for seed in self.seeds if seed.style == style]


# Global instance
_seed_manager = None

def get_seed_manager() -> ContentSeedManager:
    """Get the global content seed manager instance."""
    global _seed_manager
    if _seed_manager is None:
        _seed_manager = ContentSeedManager()
    return _seed_manager 