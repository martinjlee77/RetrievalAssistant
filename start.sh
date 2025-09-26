#!/bin/sh
set -e

# Resolve PORT environment variable with fallback
PORT="${PORT:-5000}"
echo "Using port: $PORT"

# Start Streamlit with resolved port
exec streamlit run home.py --server.port "$PORT" --server.address 0.0.0.0 --server.headless true