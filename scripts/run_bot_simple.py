#!/usr/bin/env python3
"""
Simplified auto-run script for OpenCast Bot in GitHub Actions.
"""

import random
import subprocess
import sys
import os
import time
import signal
from pathlib import Path

# Seed random with current time for better randomization
random.seed(int(time.time()))

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Timeout handler
def timeout_handler(signum, frame):
    print("⏰ Script timeout reached! Exiting...")
    sys.exit(1)

# Set timeout for the entire script (5 minutes)
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(300)  # 5 minutes timeout

def run_command_simple(command: list[str], timeout: int = 120) -> tuple[bool, str]:
    """Run a command and return success status and output."""
    try:
        print(f"🔍 Running: {' '.join(command)}")
        result = subprocess.run(
            command, 
            check=True, 
            capture_output=True, 
            text=True, 
            timeout=timeout
        )
        print(f"✅ Success: {' '.join(command)}")
        return True, result.stdout
    except subprocess.TimeoutExpired:
        print(f"⏰ Timeout after {timeout}s: {' '.join(command)}")
        return False, f"Command timed out after {timeout}s"
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed: {' '.join(command)}")
        print(f"Error: {e.stderr}")
        return False, e.stderr
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False, str(e)

def main():
    """Main execution function."""
    print("🤖 Starting OpenCast Bot (Simple Version)...")
    
    # Step 1: Validate configuration
    print("\n🔍 Step 1: Validating configuration...")
    success, output = run_command_simple(["python", "-m", "bot.cli", "validate-config"])
    if not success:
        print("❌ Configuration validation failed!")
        sys.exit(1)
    print("✅ Configuration validated")
    
    # Step 2: Try to generate and post content
    print("\n🔍 Step 2: Generating and posting content...")
    
    # Use a simple, known working category and topic
    category = "cloud-native-design"
    topic = "Microservices architecture patterns"
    
    print(f"📝 Category: {category}")
    print(f"📋 Topic: {topic}")
    
    success, output = run_command_simple([
        "python", "-m", "bot.cli", "post", category, topic
    ])
    
    if success:
        print("✅ Content generated and posted successfully!")
        
        # Write commit info for GitHub Actions
        commit_info = f"{category}: {topic}"
        print(f"📝 COMMIT_INFO: {commit_info}")
        
        with open("commit_info.txt", "w") as f:
            f.write(commit_info)
        
        print("🎉 Bot run completed successfully!")
        sys.exit(0)
    else:
        print("❌ Failed to generate and post content")
        sys.exit(1)

if __name__ == "__main__":
    main() 