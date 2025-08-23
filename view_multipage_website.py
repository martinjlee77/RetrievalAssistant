#!/usr/bin/env python3
"""
Standalone viewer for the VeritasLogic multi-page website
Run this to preview your multi-page website independently
"""
import streamlit as st

# Set page config
st.set_page_config(
    page_title="VeritasLogic Multi-Page Website Preview",
    page_icon="🌐",
    layout="wide"
)

# Import the preview functionality
import sys
import os
sys.path.append('pages')

# Load the multipage website preview
exec(open('pages/multipage_website_preview.py').read())