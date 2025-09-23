#!/usr/bin/env python3
"""
Production startup script for VeritasLogic Analysis Platform (Streamlit)
"""
import os
import sys
import subprocess

def main():
    # Get port from environment or default to 5000 (Railway will override with $PORT)
    port = int(os.environ.get('PORT', 5000))
    
    print(f"Starting VeritasLogic Analysis Platform on port {port}")
    
    # Streamlit command
    cmd = [
        sys.executable, '-m', 'streamlit', 'run',
        'home.py',
        '--server.port', str(port),
        '--server.address', '0.0.0.0',
        '--server.headless', 'true',
        '--server.enableCORS', 'false',
        '--server.enableXsrfProtection', 'false'
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    
    # Execute Streamlit
    subprocess.run(cmd)

if __name__ == '__main__':
    main()