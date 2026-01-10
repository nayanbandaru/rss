# Deployment Guide - Railway

This guide walks you through deploying the Reddit Alert Monitor to Railway.

## Prerequisites

1. A [Railway account](https://railway.app)
2. Reddit API credentials ([create app here](https://www.reddit.com/prefs/apps))
3. Gmail App Password ([generate here](https://myaccount.google.com/apppasswords))

## Quick Deploy (Recommended)

### 1. Create Railway Project

```bash
# Install Railway CLI (optional but helpful)
npm install -g @railway/cli
railway login
```

Or use the Railway dashboard: https://railway.app/new

### 2. Connect GitHub Repository

1. Go to Railway dashboard
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your repository
4. Railway will auto-detect the Python app

### 3. Add PostgreSQL Database

1. In your Railway project, click "New" → "Database" → "PostgreSQL"
2. Railway automatically injects `DATABASE_URL` into your app

### 4. Configure Environment Variables

In Railway dashboard → Your service → "Variables" tab, add:

```
# Required
JWT_SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_urlsafe(32))">
REDDIT_CLIENT_ID=<your reddit client id>
REDDIT_CLIENT_SECRET=<your reddit secret>
REDDIT_USER_AGENT=RedditAlertBot/1.0
GMAIL_FROM=<your gmail>
GMAIL_APP_PASSWORD=<your app password>
PASSWORD_RESET_BASE_URL=https://<your-app>.up.railway.app

# Optional (defaults shown)
FETCH_LIMIT=100
POLL_INTERVAL=900
MAX_RETRIES=3
```

### 5. Deploy Services

Railway will deploy the `web` service automatically. For the poller worker:

**Option A: Continuous Worker (Recommended)**
1. In Railway, click "New" → "Empty Service"
2. Connect same GitHub repo
3. Set start command: `python poller.py --loop`
4. Add same environment variables (or use shared variable group)

**Option B: Cron Job**
1. Use Railway's cron feature (requires Pro plan)
2. Set schedule: `*/15 * * * *`
3. Command: `python poller.py`

## Project Structure on Railway

```
┌─────────────────────────────────────────┐
│           Railway Project               │
├─────────────────────────────────────────┤
│  ┌─────────────────────────────────┐    │
│  │ Service: web                    │    │
│  │ Command: uvicorn app.main:app   │    │
│  │ Port: $PORT (auto-assigned)     │    │
│  └─────────────────────────────────┘    │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │ Service: worker                 │    │
│  │ Command: python poller.py --loop│    │
│  │ No port needed                  │    │
│  └─────────────────────────────────┘    │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │ Database: PostgreSQL            │    │
│  │ Auto-injects DATABASE_URL       │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

## Environment Variable Groups (Optional)

To share variables between web and worker services:

1. Go to Project Settings → Shared Variables
2. Add all your env vars there
3. Both services will inherit them

## Custom Domain (Optional)

1. Go to your web service → Settings → Domains
2. Add custom domain or use Railway's free `*.up.railway.app` subdomain
3. Update `PASSWORD_RESET_BASE_URL` to match

## Monitoring

### Logs
- Railway dashboard → Service → "Logs" tab
- Or CLI: `railway logs`

### Health Check
- Your app exposes `/health` endpoint
- Railway uses this to verify deployment success

## Costs

| Tier | Monthly Cost | Includes |
|------|--------------|----------|
| Hobby | ~$5 | 500 hours, 1GB RAM, small Postgres |
| Pro | $20+ | Unlimited hours, more resources |

The free trial includes $5 credit to get started.

## Troubleshooting

### Database connection errors
- Ensure PostgreSQL service is running
- Check `DATABASE_URL` is properly injected (Variables tab)
- Verify `psycopg2-binary` is in requirements.txt

### Poller not running
- Check worker service logs for errors
- Verify Reddit API credentials are correct
- Ensure `POLL_INTERVAL` is set (default: 900 seconds)

### Emails not sending
- Verify Gmail App Password (not regular password)
- Check Gmail account has "Less secure apps" or App Passwords enabled
- Look for SMTP errors in worker logs

### JWT errors
- Ensure `JWT_SECRET_KEY` is set and matches between services
- Check token expiration (`JWT_ACCESS_TOKEN_EXPIRE_MINUTES`)

## Local Testing with Production Config

```bash
# Test with PostgreSQL locally
docker run -d --name postgres \
  -e POSTGRES_PASSWORD=testpass \
  -e POSTGRES_DB=alerts \
  -p 5432:5432 \
  postgres:15

export DATABASE_URL=postgresql://postgres:testpass@localhost:5432/alerts
python -c "from db import init_db; init_db()"  # Create tables
python poller.py --skip-lock  # Test poller
```

## Updating

Push to your main branch - Railway auto-deploys on git push.

```bash
git add .
git commit -m "Update feature"
git push origin main
# Railway deploys automatically
```
