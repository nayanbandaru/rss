# Reddit Alert Monitor

A comprehensive Reddit keyword monitoring system that watches subreddits for specific keywords and sends real-time email notifications. Built with FastAPI, SQLAlchemy, and a modern web interface.

## Features

### Core Functionality
- **Keyword Monitoring**: Track specific keywords across any subreddit
- **Email Notifications**: Instant alerts when keywords appear in posts
- **Web Interface**: Simple, modern UI for managing alerts
- **RESTful API**: Full-featured API with automatic documentation
- **Smart Deduplication**: Three-level system prevents duplicate notifications
- **Case-Insensitive Search**: Matches keywords regardless of capitalization

### Technical Features
- **FastAPI Backend**: Modern, fast, async web framework
- **SQLAlchemy ORM**: Robust database abstraction with SQLite/PostgreSQL support
- **Structured Logging**: Comprehensive logging with file and console output
- **Error Handling**: Retry logic with exponential backoff for API calls
- **Rate Limiting**: Prevents API abuse (20 requests/minute per IP)
- **Responsive Design**: Mobile-friendly web interface
- **Test Coverage**: Comprehensive test suite with pytest

## Quick Start

### Prerequisites
- Python 3.13+ (or 3.10+)
- Gmail account (for sending email notifications)
- Reddit API credentials ([create here](https://www.reddit.com/prefs/apps))

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd rss
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**

   Create a `.env` file in the project root:
   ```bash
   # Database
   DATABASE_URL=sqlite:///./watch.db

   # Reddit API (create app at https://www.reddit.com/prefs/apps)
   REDDIT_CLIENT_ID=your_client_id
   REDDIT_CLIENT_SECRET=your_client_secret
   REDDIT_USER_AGENT=watcher-backend/0.1 by u/yourusername

   # Gmail SMTP (use App Password, not regular password)
   GMAIL_FROM=your-email@gmail.com
   GMAIL_APP_PASSWORD=your_app_password

   # Optional Settings
   FETCH_LIMIT=100
   MAX_RETRIES=3
   RETRY_DELAY=5
   ```

   **Getting Gmail App Password:**
   1. Enable 2-factor authentication on your Google account
   2. Go to [Google App Passwords](https://myaccount.google.com/apppasswords)
   3. Generate a new app password for "Mail"
   4. Use this password in `GMAIL_APP_PASSWORD`

5. **Initialize the database**
   ```bash
   python -c "from db import init_db; init_db()"
   ```

## Usage

### Web Interface (Recommended)

1. **Start the web server**
   ```bash
   ./run_server.sh
   # Or manually: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. **Access the interface**
   - Web UI: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - Alternative Docs: http://localhost:8000/redoc

3. **Create alerts**
   - Enter your email address
   - Specify subreddit (e.g., "watchexchange" or "r/watchexchange")
   - Enter keyword to monitor (e.g., "Seiko SARB")
   - Click "Create Alert"

4. **Manage alerts**
   - View all your alerts by entering your email
   - Delete alerts you no longer need
   - Alerts are automatically active upon creation

### Command Line Interface

**User Management:**
```bash
# Add a new user
python manage.py add-user alice@example.com

# List all users
python manage.py list-users
```

**Alert Management:**
```bash
# Create an alert
python manage.py add-alert alice@example.com watchexchange "Seiko SARB"

# List all alerts
python manage.py list-alerts

# List alerts for specific user
python manage.py list-alerts alice@example.com

# Delete an alert
python manage.py delete-alert <alert_id>

# Toggle alert on/off
python manage.py toggle-alert <alert_id>

# Delete all alerts for a user
python manage.py delete-user-alerts alice@example.com
```

**Running the Poller:**
```bash
# One-time execution
python poller.py

# View logs
tail -f watcher.log
```

**Set up cron job for automatic polling:**
```bash
# Edit crontab
crontab -e

# Add line to run every 15 minutes
*/15 * * * * /path/to/rss/run_poller.sh
```

### API Endpoints

**Create Alert:**
```bash
curl -X POST "http://localhost:8000/api/v1/alerts/" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "subreddit": "watchexchange",
    "keyword": "Seiko SARB"
  }'
```

**List Alerts:**
```bash
curl "http://localhost:8000/api/v1/alerts/?email=user@example.com"
```

**Delete Alert:**
```bash
curl -X DELETE "http://localhost:8000/api/v1/alerts/{alert_id}?email=user@example.com"
```

## Project Structure

```
rss/
├── app/                        # FastAPI web application
│   ├── main.py                # Application entry point
│   ├── config.py              # Settings and environment variables
│   ├── dependencies.py        # Dependency injection (DB, auth)
│   ├── models/                # Pydantic request/response models
│   │   ├── requests.py
│   │   └── responses.py
│   ├── routers/               # API endpoints
│   │   └── alerts.py
│   ├── services/              # Business logic
│   │   └── alert_service.py
│   └── middleware/            # Rate limiting, etc.
│       └── rate_limiter.py
├── templates/                 # HTML templates
│   └── index.html
├── static/                    # CSS, JavaScript
│   ├── css/style.css
│   └── js/app.js
├── tests/                     # Test suite
│   ├── conftest.py           # Test fixtures
│   ├── test_db.py            # Database tests
│   ├── test_poller.py        # Poller logic tests
│   └── test_api.py           # API endpoint tests
├── db.py                      # Database models (SQLAlchemy)
├── manage.py                  # CLI management tool
├── poller.py                  # Reddit polling logic
├── emailer.py                 # Email notification service
├── reddit_client.py           # Reddit API wrapper
├── logger.py                  # Structured logging configuration
├── requirements.txt           # Python dependencies
├── pytest.ini                 # Test configuration
├── run_server.sh             # Web server startup script
├── run_poller.sh             # Poller startup script
├── CLAUDE.md                  # Claude Code documentation
└── README.md                  # This file
```

## How It Works

### Architecture Overview

1. **User Management**: Users create accounts with their email addresses
2. **Alert Creation**: Users define (subreddit, keyword) pairs to monitor
3. **Background Polling**: Cron job runs `poller.py` periodically
4. **Reddit API**: Fetches newest posts from monitored subreddits
5. **Keyword Matching**: Case-insensitive regex search in titles and bodies
6. **Email Delivery**: Sends notifications via Gmail SMTP
7. **Deduplication**: Tracks delivered posts to prevent duplicates

### Deduplication Strategy

**Three-level deduplication ensures no duplicate notifications:**

1. **Checkpoint Table**: Stores last seen timestamp per (subreddit, keyword)
   - Only processes posts newer than checkpoint
   - Prevents refetching old posts

2. **Delivery Table**: Records (alert_id, post_id) pairs
   - Prevents resending same post to same alert
   - Unique constraint enforces this

3. **Alert Table**: Unique constraint on (user_id, subreddit, keyword)
   - Prevents duplicate alert subscriptions
   - Users can't accidentally create duplicates

### Data Flow

```
Web UI / CLI → Database (SQLite) ← Poller (cron job)
                                      ↓
                               Reddit API (PRAW)
                                      ↓
                               Email (Gmail SMTP)
```

## Testing

### Run Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/test_db.py -v

# With coverage
pytest --cov=. --cov-report=term-missing --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Test Coverage

- Database models: 95%
- Logger configuration: 95%
- Overall: 48% (API integration tests need completion)

## Development

### Running in Development Mode

**Terminal 1 - Web Server:**
```bash
./run_server.sh
# Server runs with hot reload at http://localhost:8000
```

**Terminal 2 - Poller (optional):**
```bash
python poller.py
# Or set up cron for automatic execution
```

### Making Changes

- **Backend changes**: Server auto-reloads (FastAPI --reload)
- **Frontend changes**: Refresh browser
- **Database changes**: Modify `db.py`, restart server
- **Always run tests**: `pytest` before committing

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DATABASE_URL` | Database connection string | `sqlite:///./watch.db` | No |
| `REDDIT_CLIENT_ID` | Reddit API client ID | - | Yes |
| `REDDIT_CLIENT_SECRET` | Reddit API secret | - | Yes |
| `REDDIT_USER_AGENT` | Reddit API user agent | `watcher-backend/0.1` | Yes |
| `GMAIL_FROM` | Gmail sender address | - | Yes |
| `GMAIL_APP_PASSWORD` | Gmail app password | - | Yes |
| `FETCH_LIMIT` | Posts to fetch per subreddit | `100` | No |
| `MAX_RETRIES` | API retry attempts | `3` | No |
| `RETRY_DELAY` | Initial retry delay (seconds) | `5` | No |
| `RATE_LIMIT_REQUESTS` | Requests per minute per IP | `20` | No |
| `ENABLE_AUTH` | Enable JWT authentication | `false` | No |

### Database Migration

**Switch to PostgreSQL:**

1. Update `.env`:
   ```bash
   DATABASE_URL=postgresql://user:password@localhost:5432/reddit_alerts
   ```

2. Install PostgreSQL driver:
   ```bash
   pip install psycopg2-binary
   ```

3. Database will auto-initialize on first run

## Security

### Current Security Features

- ✅ Input validation via Pydantic models
- ✅ Email validation with RFC compliance
- ✅ SQL injection prevention (SQLAlchemy ORM)
- ✅ XSS prevention in frontend
- ✅ Rate limiting (20 req/min per IP)
- ✅ CORS restrictions
- ✅ Ownership verification on delete operations

### Security Considerations

- **Credentials**: Never commit `.env` file (already in `.gitignore`)
- **Gmail**: Use App Passwords, not account password
- **Reddit API**: Keep credentials secure, rotate if exposed
- **HTTPS**: Use reverse proxy (nginx) with SSL in production
- **Authentication**: Currently email-based; JWT auth ready to implement

## Troubleshooting

### Common Issues

**Server won't start:**
```bash
# Check if port 8000 is in use
lsof -i :8000

# Kill process if needed
kill -9 <PID>
```

**No emails received:**
- Check Gmail App Password is correct
- Verify Gmail account has 2FA enabled
- Check spam folder
- Review `watcher.log` for errors

**Poller not finding posts:**
- Verify Reddit API credentials
- Check if subreddit exists and is public
- Ensure keyword spelling is correct
- Check `watcher.log` for API errors

**Database errors:**
```bash
# Reset database (WARNING: deletes all data)
rm watch.db
python -c "from db import init_db; init_db()"
```

## TODO

### Planned Features

- [ ] Add dropdown list for subreddit selection and descriptions
- [ ] Edit for user authentication with a password
- [ ] Port code over to a server so that it can run terminally on loop

### Future Enhancements

- [ ] Email verification for new users
- [ ] Email digest mode (daily/weekly summaries)
- [ ] Advanced keyword syntax (regex patterns, boolean operators)
- [ ] Subreddit browsing and search
- [ ] Alert statistics and analytics
- [ ] Post filtering by flair, author, score
- [ ] Webhook support for Discord, Slack
- [ ] Mobile app (React Native)
- [ ] Multi-language support
- [ ] Dark mode UI toggle
- [ ] Alert priority levels
- [ ] Customizable notification templates

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style

- Follow PEP 8 for Python code
- Use type hints where applicable
- Add docstrings to functions
- Write tests for new features
- Update documentation

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [PRAW](https://praw.readthedocs.io/) - Python Reddit API Wrapper
- [SQLAlchemy](https://www.sqlalchemy.org/) - SQL toolkit and ORM
- [Pydantic](https://docs.pydantic.dev/) - Data validation

## Support

For questions, issues, or feature requests:
- Open an issue on GitHub
- Check existing issues for solutions
- Review documentation in `CLAUDE.md`

---

**Built with ❤️ using FastAPI and Python**
