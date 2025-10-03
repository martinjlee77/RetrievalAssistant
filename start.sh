#!/bin/sh
set -e

# Use Railway's assigned PORT with fallback to 8080
PORT="${PORT:-8080}"
echo "Starting Flask marketing website with Gunicorn on port: $PORT"

# Start Flask backend with Gunicorn (production server)
exec gunicorn backend_api:app --bind 0.0.0.0:$PORT --workers 4 --access-logfile - --error-logfile -