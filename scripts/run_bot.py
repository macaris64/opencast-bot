#!/usr/bin/env python3
"""
Auto-run script for OpenCast Bot in GitHub Actions.
Dynamically loads available categories and topics from the bot's database.
"""

import random
import subprocess
import sys
import os
import time
from pathlib import Path

# Seed random with current time for better randomization
random.seed(int(time.time()))

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def get_available_categories_and_topics():
    """Get available categories and topics from the bot's database."""
    try:
        from bot.db.json_orm import JSONCategoryManager
        
        category_manager = JSONCategoryManager()
        categories = category_manager.list_categories()
        
        categories_and_topics = {}
        
        for category_id in categories:
            category = category_manager.load_category(category_id)
            if category and category.topics and len(category.topics) > 0:
                topics = [topic.topic for topic in category.topics]
                categories_and_topics[category_id] = topics
        
        return categories_and_topics
        
    except Exception as e:
        print(f"Error loading categories: {e}")
        # Fallback to a default category
        return {"dev-best-practices": ["Code quality", "Best practices", "Clean code"]}

def run_command(command: list[str]) -> bool:
    """Run a command and return success status."""
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"✅ Command succeeded: {' '.join(command)}")
        if result.stdout:
            print(f"Output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {' '.join(command)}")
        print(f"Error: {e.stderr}")
        return False

def main():
    """Main execution function."""
    print("🤖 Starting OpenCast Bot auto-run...")
    
    # Check environment variables
    print("🔍 Debug: Checking environment...")
    openai_key = os.getenv('OPENAI_API_KEY', '')
    twitter_key = os.getenv('TWITTER_API_KEY', '')
    twitter_secret = os.getenv('TWITTER_API_SECRET', '')
    twitter_token = os.getenv('TWITTER_ACCESS_TOKEN', '')
    twitter_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET', '')
    twitter_bearer = os.getenv('TWITTER_BEARER_TOKEN', '')
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    telegram_chat = os.getenv('TELEGRAM_CHAT_ID', '')
    
    print(f"OPENAI_API_KEY: {'✅ Set' if openai_key else '❌ Missing'} (length: {len(openai_key)})")
    print(f"TWITTER_API_KEY: {'✅ Set' if twitter_key else '❌ Missing'} (length: {len(twitter_key)})")
    print(f"TWITTER_API_SECRET: {'✅ Set' if twitter_secret else '❌ Missing'} (length: {len(twitter_secret)})")
    print(f"TWITTER_ACCESS_TOKEN: {'✅ Set' if twitter_token else '❌ Missing'} (length: {len(twitter_token)})")
    print(f"TWITTER_ACCESS_TOKEN_SECRET: {'✅ Set' if twitter_token_secret else '❌ Missing'} (length: {len(twitter_token_secret)})")
    print(f"TWITTER_BEARER_TOKEN: {'✅ Set' if twitter_bearer else '❌ Missing'} (length: {len(twitter_bearer)})")
    print(f"TELEGRAM_BOT_TOKEN: {'✅ Set' if telegram_token else '❌ Missing'} (length: {len(telegram_token)})")
    print(f"TELEGRAM_CHAT_ID: {'✅ Set' if telegram_chat else '❌ Missing'} (length: {len(telegram_chat)})")
    
    # Validate configuration first
    print("🔍 Debug: Validating bot configuration...")
    if not run_command(["python", "-m", "bot.cli", "validate-config"]):
        print("❌ Configuration validation failed!")
        sys.exit(1)
    
    # Get available categories and topics
    categories_and_topics = get_available_categories_and_topics()
    
    if not categories_and_topics:
        print("❌ No categories available!")
        sys.exit(1)
    
    print(f"📚 Found {len(categories_and_topics)} categories")
    
    # Randomly select 1 category to run (to avoid overwhelming)
    selected_categories = random.sample(list(categories_and_topics.keys()), k=1)
    
    success_count = 0
    total_attempts = 0
    successful_operations = []
    
    for category in selected_categories:
        available_topics = categories_and_topics[category]
        
        # Try up to 5 different topics to find one that works
        max_topic_attempts = min(5, len(available_topics))
        topic_attempts = 0
        category_success = False
        
        while topic_attempts < max_topic_attempts and not category_success:
            topic = random.choice(available_topics)
            
            print(f"\n📝 Processing category: {category}")
            print(f"📋 Topic: {topic} (attempt {topic_attempts + 1}/{max_topic_attempts})")
            
            # Generate and post content using CLI (post command does both)
            total_attempts += 1
            if run_command(["python", "-m", "bot.cli", "post", category, topic]):
                success_count += 1
                successful_operations.append(f"{category}: {topic}")
                print(f"✅ Successfully generated and posted content for {category}: {topic}")
                category_success = True
            else:
                print(f"❌ Failed to generate and post content for {category}: {topic}")
                topic_attempts += 1
                
                if topic_attempts < max_topic_attempts:
                    print(f"🔄 Trying different topic for {category}...")
    
    print(f"\n📊 Summary: {success_count}/{total_attempts} successful operations")
    
    # Write commit info for GitHub Actions
    if successful_operations:
        commit_info = " | ".join(successful_operations)
        print(f"\n📝 COMMIT_INFO: {commit_info}")
        
        # Write to environment file for GitHub Actions
        with open("commit_info.txt", "w") as f:
            f.write(commit_info)
    
    # Exit with appropriate code
    if success_count > 0:
        print("🎉 Bot run completed successfully!")
        sys.exit(0)
    else:
        print("😞 No successful operations")
        sys.exit(1)

if __name__ == "__main__":
    main() 