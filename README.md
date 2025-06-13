# 🤖 OpenCast Bot

OpenCast Bot is a Python-based automation system that generates short, engaging content using the OpenAI API and automatically posts it to X (Twitter) and Telegram. The bot focuses on modern development topics with English content and exactly 2 hashtags per post.

## ✨ Features

- 🎯 **AI-Powered Content Generation**: Creates engaging development tips using OpenAI API
- 🎨 **Content Variety System**: 50+ writing styles and tones for diverse content
- 📱 **Multi-Platform Publishing**: Automated posting to X (Twitter) and Telegram
- 🔄 **Auto-Commit System**: GitHub Actions integration with automatic repository updates
- 🏗️ **Modern Categories**: 10 curated categories with 200+ unique topics
- 🌍 **English Content**: Professional English content with exactly 2 hashtags
- 📊 **Smart Validation**: 20-220 character limit with comprehensive content validation
- 🔄 **Duplicate Prevention**: Tracks generated content to avoid repetition
- 🧪 **Dry Run Mode**: Test without actually posting content
- 📋 **Enhanced CLI Interface**: User-friendly commands with confirmations
- 🎯 **Exceptional Test Coverage**: 92.69% test coverage with 320 comprehensive tests

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- OpenAI API key
- X (Twitter) API credentials (optional)
- Telegram Bot token (optional)

### Installation

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd opencast-bot
   ```

2. **Create virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -e .
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API credentials
   ```

## ⚙️ Configuration

Create a `.env` file in the project root with the following variables:

```env
# OpenAI Configuration (Required)
OPENAI_API_KEY=sk-your-openai-api-key-here

# X (Twitter) Configuration (Optional)
TWITTER_ENABLED=true
TWITTER_API_KEY=your-twitter-api-key
TWITTER_API_SECRET=your-twitter-api-secret
TWITTER_ACCESS_TOKEN=your-twitter-access-token
TWITTER_ACCESS_TOKEN_SECRET=your-twitter-access-token-secret

# Telegram Configuration (Optional)
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=1234567890

# General Configuration
DRY_RUN=false
LOG_LEVEL=INFO
DATA_DIRECTORY=categories
```

### Getting API Credentials

#### OpenAI API Key

1. Visit [OpenAI Platform](https://platform.openai.com/)
2. Sign up/login and go to API Keys
3. Create a new API key
4. Add billing information (required for API usage)

#### X (Twitter) API

1. Visit [Twitter Developer Portal](https://developer.twitter.com/)
2. Create a new app with OAuth 1.0a permissions
3. Generate API keys and access tokens
4. Ensure your app has read and write permissions

#### Telegram Bot

1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Create a new bot with `/newbot`
3. Get your bot token
4. Add the bot to your channel/group and get the chat ID

## 📁 Project Structure

```
opencast-bot/
├── bot/                    # Main application code
│   ├── models/            # Pydantic data models
│   ├── publisher/         # Platform publishers (Twitter, Telegram)
│   ├── db/               # Database layer (JSON ORM)
│   ├── config.py         # Configuration management
│   ├── generator.py      # Content generation logic
│   ├── cli.py           # Command-line interface
│   └── main.py          # Main application logic
├── categories/           # Category JSON files
├── outputs/             # Generated content outputs
├── scripts/             # Automation scripts
├── tests/              # Test suite
├── memory-bank/        # Project documentation
├── .github/workflows/  # GitHub Actions CI/CD
├── .env               # Environment variables
└── pyproject.toml     # Project configuration
```

## 🎯 Usage

### CLI Commands

#### Generate Content (Development Only)

```bash
# Generate content only (with confirmation prompt)
python -m bot.cli generate "modern-frontend-practices" "React Server Components"

# Note: This command shows a warning and requires Y/N confirmation
# Content is saved to JSON but NOT posted to any platform
```

#### Generate and Post Content

```bash
# Generate new content and post to all enabled platforms
python -m bot.cli post "secure-coding-2025" "Zero-trust architecture"

# This is the recommended command for production use
# Combines content generation + posting in one step
```

#### List Categories

```bash
# List all available categories
python -m bot.cli list-categories
```

#### Validate Configuration

```bash
# Check if your configuration is valid
python -m bot.cli validate-config
```

#### Test Platform Connections

```bash
# Test Twitter connection
python -m bot.cli test-twitter

# Test Telegram connection (via generate command)
python -m bot.cli generate "devex-insights" "Developer productivity metrics"
```

### Automated Execution

```bash
# Run bot with random category and topic selection
python scripts/run_bot.py
```

## 🎨 Content Variety System

OpenCast Bot features a revolutionary content variety system that generates diverse, engaging content using 50+ different writing styles and approaches:

### Writing Tones

- **Professional**: Industry best practices and proven methods
- **Casual**: Friendly, approachable language
- **Enthusiastic**: Exciting and motivational content
- **Analytical**: Technical depth and reasoning
- **Practical**: Immediate actionable benefits
- **Inspirational**: Motivating and encouraging
- **Direct**: Clear, concise instructions
- **Conversational**: Thought-provoking questions
- **Expert**: Advanced knowledge and experience
- **Beginner-friendly**: Simple, clear explanations

### Content Styles

- **Tips**: Quick, actionable advice
- **Warnings**: Important considerations and cautions
- **Best Practices**: Industry standards and methodologies
- **Common Mistakes**: What to avoid and why
- **Quick Wins**: Immediate benefits and shortcuts
- **Deep Insights**: Advanced technical knowledge
- **Comparisons**: Different approaches or tools
- **Step-by-step**: Clear instructions and processes
- **Questions**: Thought-provoking inquiries
- **Facts**: Data-driven insights

### Dynamic Prefixes

Content can start with engaging prefixes like:

- "Pro tip:" - Practical advice
- "Game changer:" - Exciting benefits
- "New to this?" - Beginner guidance
- "Important:" - Critical considerations
- "Quick tip:" - Helpful shortcuts

### Example Variations

The same topic can generate completely different content:

- "New to this? Remember to define resource requests and limits for better pod performance. #Kubernetes #CloudNative"
- "Pro tip: Optimize your cloud costs by leveraging auto-scaling features and monitoring resources. #CloudOptimization #CostSavings"
- "How can we streamline developer workflows to enhance productivity? #DeveloperExperience #Optimization"

## 📝 Content Categories (2025 Focus)

The bot includes 10 modern development categories, each with 20+ unique topics (200+ total):

### 1. 🎨 Modern Frontend Practices

- React Server Components, CSS Container Queries, Web Components
- TypeScript best practices, Core Web Vitals optimization
- Modern bundling strategies, Accessibility automation

### 2. 🤖 AI-Powered Development Workflows

- GitHub Copilot workflows, AI code review tools
- Automated testing with AI, AI-assisted debugging
- Code generation patterns, AI pair programming

### 3. ☁️ Cloud-Native Design Tips

- Microservices patterns, Container orchestration
- Serverless architecture, Event-driven design
- API gateway strategies, Service mesh implementation

### 4. 🔒 Secure Coding in 2025

- Zero-trust architecture, Supply chain security
- OWASP Top 10 updates, Secure by design
- Dependency scanning, Secret management

### 5. 🛠️ Developer Experience (DevEx) Insights

- Developer productivity metrics, IDE optimization
- Local development environments, Documentation strategies
- Onboarding automation, Tool consolidation

### 6. ⚡ Code Performance Micro-Tips

- Memory optimization, Database query optimization
- Caching strategies, Bundle size reduction
- Runtime performance, Algorithm efficiency

### 7. 🧪 Testing in Modern Stacks

- Component testing strategies, E2E testing automation
- API testing patterns, Visual regression testing
- Performance testing, Contract testing

### 8. 🔀 Clean Git Practices in Teams

- Commit message conventions, Branch naming strategies
- Code review workflows, Merge vs rebase strategies
- Git hooks automation, Repository organization

### 9. 🚀 CI/CD Tactics That Actually Work

- Pipeline optimization, Deployment strategies
- Environment management, Automated rollbacks
- Security scanning integration, Feature flag deployment

### 10. 🏗️ Frontend Architecture Patterns

- Micro-frontend patterns, State management strategies
- Component design systems, Module federation
- Build optimization, Scalability patterns

## 🔄 GitHub Actions Automation

The bot includes a complete GitHub Actions workflow for automated content generation and posting:

### 🚀 Automated Features

- **⏰ Hourly Execution**: Runs automatically every hour via cron schedule
- **🎲 Smart Selection**: Intelligently picks random categories and topics
- **📝 Auto-Commit**: Automatically commits generated content back to repository
- **💬 Smart Commit Messages**: Includes category and topic information
- **🛡️ Error Handling**: Comprehensive logging and error recovery
- **🔒 Secure**: All API keys stored as GitHub repository secrets

### 📋 Workflow Setup

1. **Configure Repository Secrets**

   Go to your repository Settings → Secrets and variables → Actions, and add:

   ```
   OPENAI_API_KEY=sk-your-openai-api-key-here
   TWITTER_API_KEY=your-twitter-api-key
   TWITTER_API_SECRET=your-twitter-api-secret
   TWITTER_ACCESS_TOKEN=your-twitter-access-token
   TWITTER_ACCESS_TOKEN_SECRET=your-twitter-access-token-secret
   TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
   TELEGRAM_CHAT_ID=-1001234567890
   ```

2. **Workflow Configuration**

   The workflow is defined in `.github/workflows/ci.yml`:

   ```yaml
   name: OpenCast Bot CI/CD

   on:
     schedule:
       - cron: "0 * * * *" # Run every hour
     push:
       branches: [main]
     pull_request:
       branches: [main]

   jobs:
     test:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - name: Set up Python
           uses: actions/setup-python@v4
           with:
             python-version: "3.11"
         - name: Install dependencies
           run: |
             pip install -r requirements.txt
         - name: Run tests
           run: |
             pytest --cov=bot --cov-fail-under=90

     deploy:
       needs: test
       runs-on: ubuntu-latest
       if: github.event_name == 'schedule'
       steps:
         - uses: actions/checkout@v4
         - name: Set up Python
           uses: actions/setup-python@v4
           with:
             python-version: "3.11"
         - name: Install dependencies
           run: |
             pip install -r requirements.txt
         - name: Run bot
           env:
             OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
             TWITTER_API_KEY: ${{ secrets.TWITTER_API_KEY }}
             TWITTER_API_SECRET: ${{ secrets.TWITTER_API_SECRET }}
             TWITTER_ACCESS_TOKEN: ${{ secrets.TWITTER_ACCESS_TOKEN }}
             TWITTER_ACCESS_TOKEN_SECRET: ${{ secrets.TWITTER_ACCESS_TOKEN_SECRET }}
             TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
             TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
           run: |
             python scripts/run_bot.py
         - name: Auto-commit changes
           run: |
             git config --local user.email "bot@opencast.dev"
             git config --local user.name "OpenCast Bot"
             git add -A
             if ! git diff --staged --quiet; then
               git commit -m "🤖 Auto-update: Generated content $(date '+%Y-%m-%d %H:%M')"
               git push
             fi
   ```

### 🔄 Auto-Commit Process

1. **Content Generation**: Bot selects random category and topic
2. **Content Creation**: OpenAI generates professional development content
3. **Multi-Platform Posting**: Posts to Twitter and Telegram simultaneously
4. **File Updates**: Updates category JSON files with new content
5. **Git Detection**: GitHub Actions detects file changes
6. **Auto-Commit**: Commits with descriptive message including timestamp
7. **Repository Update**: Pushes changes back to main branch

### 📊 Workflow Monitoring

- **GitHub Actions Tab**: View execution logs and status
- **Commit History**: Track auto-generated content commits
- **Error Notifications**: GitHub will notify on workflow failures
- **Content Tracking**: All generated content is versioned in Git

### 🛠️ Manual Triggers

You can also trigger the workflow manually:

```bash
# Via GitHub CLI
gh workflow run ci.yml

# Via GitHub web interface
# Go to Actions tab → Select workflow → Run workflow
```

### 🔧 Customization

Modify the cron schedule in `.github/workflows/ci.yml`:

```yaml
schedule:
  - cron: "0 */2 * * *" # Every 2 hours
  - cron: "0 9,17 * * *" # 9 AM and 5 PM daily
  - cron: "0 12 * * 1-5" # Weekdays at noon
```

## 🧪 Testing

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=bot --cov-report=term-missing

# Run specific test file
pytest tests/test_generator.py -v

# Run integration tests
pytest tests/test_integration.py -v

# Run end-to-end tests
pytest tests/test_e2e.py -v
```

### Test Coverage

The project maintains **92.69% test coverage** with **320 comprehensive tests**:

#### Test Suite Breakdown

- **Unit Tests (301)**: All components individually tested

  - CLI Module: 88% coverage (24 tests)
  - Config Module: 85% coverage (23 tests)
  - Content Generator: 99% coverage (29 tests)
  - Database/JSON ORM: 90% coverage (43 tests)
  - Category Models: 100% coverage (28 tests)
  - Topic Models: 100% coverage (20 tests)
  - Twitter Publisher: 100% coverage (32 tests)
  - Telegram Publisher: 90% coverage (32 tests)
  - Exception Utilities: 100% coverage (27 tests)
  - Logging Utilities: 95% coverage (23 tests)

- **Integration Tests (12)**: Multi-component workflow testing

  - Config integration with publishers
  - Generator integration with category management
  - Multi-platform publishing scenarios
  - Database operations and persistence
  - Complete content generation workflows
  - Concurrency and thread safety validation

- **End-to-End Tests (7)**: Complete system validation
  - Full workflow from generation to publishing
  - Error scenarios and recovery testing
  - Multi-platform content distribution
  - Content validation and format verification

#### Test Quality Features

- **Security**: All external APIs properly mocked, no real credentials
- **Performance**: Concurrent operations and scalability testing
- **Reliability**: 100% test pass rate with comprehensive error handling
- **Coverage**: Significantly exceeds 90% target with 92.69% coverage
- **Automation**: CI/CD pipeline with automated test execution

## 📊 Content Requirements

- **Language**: English only
- **Length**: 20-220 characters (including hashtags)
- **Hashtags**: Exactly 2 hashtags per post
- **Quality**: Professional, actionable, and engaging
- **Uniqueness**: No duplicate content for same topic

## 🚀 Deployment

### Local Development

```bash
# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest --cov=bot

# Run bot locally
python -m bot.cli generate "modern-frontend-practices" "React Server Components"
```

### GitHub Actions

1. Set up repository secrets for API keys
2. Push to main branch
3. GitHub Actions will run tests and deploy automatically
4. Bot will execute hourly and auto-commit new content

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure 90%+ test coverage
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🔗 Links

- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Twitter API Documentation](https://developer.twitter.com/en/docs)
- [Telegram Bot API Documentation](https://core.telegram.org/bots/api)
