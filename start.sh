#!/bin/sh
set -e

# Use Railway's assigned PORT with fallback to 5000
PORT="${PORT:-5000}"
echo "Starting app on port: $PORT"

# Start Streamlit with proper port resolution
exec streamlit run home.py --server.port "$PORT" --server.address 0.0.0.0 --server.headless true