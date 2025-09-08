#!/usr/bin/env python3
"""
Production startup script for VeritasLogic Website (Flask)
"""
import os
import sys
from backend_api import app

def main():
    # Get port from environment or default to 5000
    port = int(os.environ.get('PORT', 5000))
    
    # Production configuration
    app.config['DEBUG'] = False
    app.config['ENV'] = 'production'
    
    print(f"Starting VeritasLogic Website on port {port}")
    print(f"Environment: {app.config['ENV']}")
    
    # Run the application
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False
    )

if __name__ == '__main__':
    main()