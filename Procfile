# Railway/Heroku Procfile
# Web server (FastAPI)
web: uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}

# Background worker (continuous polling mode)
worker: python poller.py --loop --interval ${POLL_INTERVAL:-900}
