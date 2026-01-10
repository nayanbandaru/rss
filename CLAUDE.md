# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a Reddit keyword monitoring system that watches subreddits for specific keywords and sends email alerts to users. The system runs as a periodic poller (cron job) that:
1. Fetches new posts from subreddits users are monitoring
2. Matches posts against user-defined keywords (case-insensitive)
3. Sends email notifications via Gmail SMTP
4. Tracks what has been sent to avoid duplicate notifications

## Commands

### Database Management
```bash
# User management
python manage.py add-user <email>
python manage.py list-users
python manage.py delete-user-alerts <email>

# Alert management
python manage.py add-alert <email> <subreddit> "<keyword>"
python manage.py list-alerts [email]
python manage.py delete-alert <alert_id>
python manage.py toggle-alert <alert_id>

# Examples
python manage.py add-user alice@example.com
python manage.py add-alert alice@example.com watchexchange "Seiko SARB"
```

### Running the Poller
```bash
# One-time execution (with distributed lock)
python poller.py

# Continuous mode (runs every 15 minutes by default)
python poller.py --loop

# Continuous mode with custom interval (e.g., 5 minutes)
python poller.py --loop --interval 300

# Skip lock for local debugging only
python poller.py --skip-lock

# Production: run via cron OR use --loop mode
# Cron example: */15 * * * * /path/to/run_poller.sh
# Railway/container: python poller.py --loop
```

### Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Configure .env file with:
# - DATABASE_URL (defaults to sqlite:///./watch.db)
# - REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT
# - GMAIL_FROM, GMAIL_APP_PASSWORD
# - FETCH_LIMIT (default: 100)
# - MAX_RETRIES (default: 3) - Number of retry attempts for API calls
# - RETRY_DELAY (default: 5) - Initial delay in seconds for exponential backoff
# - POLL_INTERVAL (default: 900) - Polling interval in seconds for --loop mode
# - LOCK_FILE_PATH (default: /tmp/poller.lock) - File lock path for SQLite mode
```

### Testing
```bash
# Run all tests
pytest

# Run tests with verbose output
pytest -v

# Run tests with coverage report
pytest --cov=. --cov-report=term-missing --cov-report=html

# Run specific test file
pytest tests/test_db.py

# Run specific test class or function
pytest tests/test_poller.py::TestKeywordRegex::test_key_regex_basic
```

## Architecture

### Core Components

**db.py** - SQLAlchemy data models and database initialization
- `User`: email-based user accounts (email used as ID in MVP)
- `Alert`: user subscriptions to (subreddit, keyword) pairs with active/inactive toggle
- `Delivery`: tracks sent emails to prevent duplicates (alert_id + reddit_post_id)
- `Checkpoint`: maintains per-(subreddit, keyword) high-water marks (last_seen_created_utc)

**poller.py** - Main polling logic that runs periodically
- Aggregates active alerts into unique (subreddit, keyword) pairs to minimize Reddit API calls
- Comprehensive error handling with try-catch blocks for all operations
- Retry logic with exponential backoff for Reddit API and email sending
- Structured logging throughout (replaces print statements)
- For each pair:
  - Fetches FETCH_LIMIT newest posts from subreddit
  - Processes posts chronologically (oldest to newest)
  - Only processes posts newer than checkpoint timestamp
  - Case-insensitive regex matching on post title and body
  - Sends one email per matched post per subscribed user
  - Records deliveries to prevent duplicates
  - Advances checkpoint to highest seen timestamp
- Graceful degradation: continues processing other alerts if one fails
- Proper database session cleanup in finally block

**logger.py** - Structured logging configuration
- Console handler for stdout (INFO level)
- File handler for persistent logs (DEBUG level, written to watcher.log)
- Formatted timestamps and log levels
- Function name and line number tracking in file logs

**manage.py** - CLI for user and alert CRUD operations
- All database management goes through this interface
- Validates emails before creating users
- Prevents duplicate alerts with unique constraint on (user_id, subreddit, keyword)

**emailer.py** - Gmail SMTP integration
- Sends HTML emails with text fallback
- Requires Gmail App Password (not regular password)

**reddit_client.py** - PRAW Reddit API wrapper
- Supports both read-only and authenticated access
- Rate limiting configured at 5 seconds

### Data Flow

1. Users and alerts created via `manage.py`
2. Cron job runs `poller.py` periodically (e.g., every 15 minutes)
3. Poller fetches new posts since last checkpoint
4. Matched posts trigger emails to all subscribed users
5. Checkpoints advance to avoid reprocessing

### Key Implementation Details

- **Deduplication**: Three levels - checkpoint prevents refetching old posts, delivery table prevents resending same post to same alert, alert uniqueness constraint prevents duplicate subscriptions
- **Case-insensitive matching**: Uses `re.compile(re.escape(keyword), re.IGNORECASE)`
- **Subreddit normalization**: Strips "r/" prefix and whitespace, lowercases for comparison
- **Chronological processing**: Posts sorted by created_utc before processing to maintain correct checkpoint advancement
- **Multi-user support**: Multiple users can watch same (subreddit, keyword) pair; poller groups them to minimize API calls
- **Email as ID**: MVP uses email address as user.id for simplicity

### Database Schema Notes

- SQLite by default, designed to be Postgres-compatible via DATABASE_URL
- Cascading deletes: deleting user deletes alerts; deleting alert deletes deliveries
- Composite primary key on Checkpoint (subreddit, keyword)
- Unique constraints prevent duplicate alerts and deliveries

## Testing Infrastructure

**Test Framework**: pytest with pytest-cov for coverage reporting

**Test Structure**:
- `tests/conftest.py` - Shared fixtures for test database and sample data
  - `test_engine` - In-memory SQLite database for tests
  - `test_session` - Database session fixture
  - `sample_user`, `sample_alert` - Preloaded test data
- `tests/test_db.py` - Database model tests (9 tests)
  - User, Alert, Delivery, Checkpoint CRUD operations
  - Unique constraint validation
  - Relationship testing
- `tests/test_poller.py` - Poller logic tests (10 tests)
  - Keyword regex matching (case-insensitive, special chars, multi-word)
  - Timezone conversion
  - Retry logic with exponential backoff
  - Subreddit normalization

**Current Coverage**: 48% overall
- db.py: 95%
- logger.py: 95%
- Test files: 100%
- poller.py: 24% (integration tests needed for full coverage)
- emailer.py: 36% (needs email mocking tests)
- manage.py: 0% (CLI testing requires different approach)

**Running Tests**:
- All tests use in-memory SQLite (no impact on production database)
- Tests are isolated - each test gets fresh database session
- Fixtures automatically clean up after tests
- Coverage reports generated in `htmlcov/` directory

## Error Handling and Retry Strategy

**Retry Mechanism**:
- Exponential backoff: delays double with each retry (5s, 10s, 20s by default)
- Configurable via MAX_RETRIES and RETRY_DELAY environment variables
- Applies to: Reddit API calls, email sending
- Logs all retry attempts with detailed error messages

**Error Types Handled**:
- Reddit API errors: RedditAPIException, ResponseException, RequestException, PRAWException
- Database errors: SQLAlchemyError with automatic rollback
- Email errors: SMTP exceptions with retry logic
- Unexpected errors: logged with full traceback, execution continues

**Graceful Degradation**:
- If one subreddit fails, processing continues with remaining subreddits
- If email to one user fails, other users still receive notifications
- Database session always closed in finally block
- Checkpoints only advanced after successful processing

## Logging

**Log Files**: `watcher.log` (automatically created, gitignored)

**Log Levels**:
- DEBUG: Detailed information (checkpoint updates, duplicate detection)
- INFO: General flow (polling start/end, matches found, emails sent)
- WARNING: Recoverable issues (retry attempts, missing users)
- ERROR: Failures (API errors, email failures, database errors)

**Log Format**:
- Console: `timestamp - name - level - message`
- File: `timestamp - name - level - function:line - message`

**Key Logged Events**:
- Polling cycle start/end with statistics
- Alert aggregation and processing
- Reddit API calls and post fetching
- Keyword matches with post titles
- Email sending success/failure
- Checkpoint updates
- All errors with full context
