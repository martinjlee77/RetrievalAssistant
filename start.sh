#!/bin/sh
set -e

# Use Railway's assigned PORT with fallback to 5000
PORT="${PORT:-5000}"
echo "Starting both services..."

# Set backend URL to localhost for internal communication
export BACKEND_URL="http://127.0.0.1:3000/api"

# Start Flask backend on port 3000 in background
echo "Starting Flask backend on port 3000..."
python backend_api.py --port 3000 &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 3

# Start Streamlit on main port
echo "Starting Streamlit frontend on port: $PORT"
exec streamlit run home.py --server.port "$PORT" --server.address 0.0.0.0 --server.headless true