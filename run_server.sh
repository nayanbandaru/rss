#!/bin/bash

# Reddit Alert Monitor - Web Server Startup Script

echo "Starting Reddit Alert Monitor Web Server..."
echo "=========================================="

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Run FastAPI server with hot reload (development mode)
echo "Starting server at http://localhost:8000"
echo "API docs available at http://localhost:8000/docs"
echo "Press Ctrl+C to stop"
echo ""

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
