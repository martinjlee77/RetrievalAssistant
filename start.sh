#!/bin/sh
set -e

# Use Railway's assigned PORT with fallback to 3000
PORT="${PORT:-3000}"
echo "Starting Flask marketing website on port: $PORT"

# Start only the Flask backend (marketing website)
exec python backend_api.py --port "$PORT"