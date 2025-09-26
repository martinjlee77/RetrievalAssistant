#!/bin/sh
set -e

# Unset problematic Streamlit env var that Railway sets to literal "$PORT"
unset STREAMLIT_SERVER_PORT

# Resolve PORT environment variable with fallback
PORT="${PORT:-5000}"
echo "Using port: $PORT"

# Start Streamlit with resolved port
exec streamlit run home.py --server.port "$PORT" --server.address 0.0.0.0 --server.headless true