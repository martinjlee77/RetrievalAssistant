#!/usr/bin/env python3
"""
Production startup script for VeritasLogic Analysis Platform (Streamlit)
"""
import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    import streamlit.web.cli as stcli
    
    # Get port from environment or default to 8501
    port = int(os.environ.get('PORT', 8501))
    
    # Streamlit configuration
    sys.argv = [
        "streamlit", 
        "run", 
        "home.py",
        "--server.port", str(port),
        "--server.address", "0.0.0.0",
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false"
    ]
    
    sys.exit(stcli.main())