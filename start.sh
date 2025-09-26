#!/bin/sh
set -e

# Completely bypass Railway's PORT variable - just use 5000
echo "Starting app on hardcoded port 5000"

# Start Streamlit with hardcoded port 5000
exec streamlit run home.py --server.port 5000 --server.address 0.0.0.0 --server.headless true