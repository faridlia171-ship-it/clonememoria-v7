#!/usr/bin/env bash
set -e

echo "==== CloneMemoria Backend Startup ===="

# Detect Render environment
if [[ "$RENDER" == "true" ]]; then
    echo "[MODE] Render Production detected"

    echo "Installing dependencies (Render)..."
    pip install --upgrade pip
    pip install -r backend/requirements.txt

    echo "Starting FastAPI (production mode)..."
    exec uvicorn backend.main:app --host 0.0.0.0 --port $PORT

else
    echo "[MODE] Local Development detected"

    # Create venv if missing
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
    fi

    echo "Activating virtual environment..."
    source venv/bin/activate

    echo "Installing dependencies (local venv)..."
    pip install --upgrade pip
    pip install -r backend/requirements.txt

    echo "Starting FastAPI (with autoreload)..."
    uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
fi
