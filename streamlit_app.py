#!/usr/bin/env python3
"""
Production startup script for VeritasLogic Analysis Platform (Streamlit)
This file just imports the main Streamlit app - Railway handles the actual startup
"""
import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Simply import the main Streamlit app
# Railway will run: streamlit run streamlit_app.py
# This file just needs to execute the main app
import home