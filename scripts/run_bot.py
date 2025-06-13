#!/usr/bin/env python3
"""
Auto-run script for OpenCast Bot in GitHub Actions.
Randomly selects categories and topics to generate diverse content.
"""

import random
import subprocess
import sys
from pathlib import Path

# Available categories and sample topics (2025 modern development focus)
CATEGORIES_AND_TOPICS = {
    "modern-frontend-practices": [
        "React Server Components",
        "CSS Container Queries",
        "Web Components adoption",
        "Progressive Enhancement",
        "Core Web Vitals optimization",
        "TypeScript best practices",
        "Modern bundling strategies",
        "Accessibility automation"
    ],
    "ai-powered-development": [
        "GitHub Copilot workflows",
        "AI code review tools",
        "Automated testing with AI",
        "AI-assisted debugging",
        "Code generation patterns",
        "AI pair programming",
        "Prompt engineering for devs",
        "AI documentation tools"
    ],
    "cloud-native-design": [
        "Microservices patterns",
        "Container orchestration",
        "Serverless architecture",
        "Event-driven design",
        "API gateway strategies",
        "Service mesh implementation",
        "Cloud security patterns",
        "Observability design"
    ],
    "secure-coding-2025": [
        "Zero-trust architecture",
        "Supply chain security",
        "OWASP Top 10 updates",
        "Secure by design",
        "Dependency scanning",
        "Secret management",
        "Security testing automation",
        "Threat modeling practices"
    ],
    "devex-insights": [
        "Developer productivity metrics",
        "IDE optimization",
        "Local development environments",
        "Documentation strategies",
        "Onboarding automation",
        "Developer feedback loops",
        "Tool consolidation",
        "Cognitive load reduction"
    ],
    "code-performance-tips": [
        "Memory optimization",
        "Database query optimization",
        "Caching strategies",
        "Bundle size reduction",
        "Runtime performance",
        "Network optimization",
        "Algorithm efficiency",
        "Profiling techniques"
    ],
    "testing-modern-stacks": [
        "Component testing strategies",
        "E2E testing automation",
        "API testing patterns",
        "Visual regression testing",
        "Performance testing",
        "Contract testing",
        "Test data management",
        "Testing in production"
    ],
    "clean-git-practices": [
        "Commit message conventions",
        "Branch naming strategies",
        "Code review workflows",
        "Merge vs rebase strategies",
        "Git hooks automation",
        "Conflict resolution",
        "Repository organization",
        "Release management"
    ],
    "cicd-tactics": [
        "Pipeline optimization",
        "Deployment strategies",
        "Environment management",
        "Automated rollbacks",
        "Security scanning integration",
        "Artifact management",
        "Monitoring integration",
        "Feature flag deployment"
    ],
    "frontend-architecture": [
        "Micro-frontend patterns",
        "State management strategies",
        "Component design systems",
        "Module federation",
        "Build optimization",
        "Runtime architecture",
        "Performance budgets",
        "Scalability patterns"
    ]
}

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
    
    # Randomly select 1-2 categories to run
    selected_categories = random.sample(list(CATEGORIES_AND_TOPICS.keys()), k=random.randint(1, 2))
    
    success_count = 0
    total_attempts = 0
    successful_operations = []
    
    for category in selected_categories:
        # Randomly select a topic for this category
        topic = random.choice(CATEGORIES_AND_TOPICS[category])
        
        print(f"\n📝 Processing category: {category}")
        print(f"📋 Topic: {topic}")
        
        # Generate content
        total_attempts += 1
        if run_command(["python", "-m", "bot.cli", "generate", category, topic]):
            # If generation succeeded, try to post
            if run_command(["python", "-m", "bot.cli", "post", category, topic]):
                success_count += 1
                successful_operations.append(f"{category}: {topic}")
                print(f"✅ Successfully posted content for {category}: {topic}")
            else:
                print(f"⚠️ Generated but failed to post for {category}: {topic}")
        else:
            print(f"❌ Failed to generate content for {category}: {topic}")
    
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