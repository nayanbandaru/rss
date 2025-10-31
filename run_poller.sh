#!/bin/bash
cd /home/username/reddit-watcher

# Load environment variables
source .env

# Activate virtual environment if you use one
source venv/bin/activate

# Run the poller
python3 poller.py

# Optional: Send yourself an email if it fails
if [ $? -ne 0 ]; then
    echo "Poller failed at $(date)" | mail -s "Reddit Watcher Error" your@email.com
fi