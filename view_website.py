#!/usr/bin/env python3
"""
Simple script to open the website proof of concept in your default browser
"""
import webbrowser
import os
from pathlib import Path

def open_website():
    # Get the full path to the HTML file
    html_file = Path("website_proof_of_concept.html").absolute()
    
    if html_file.exists():
        # Convert to file:// URL
        file_url = f"file://{html_file}"
        print(f"Opening website preview: {file_url}")
        webbrowser.open(file_url)
        print("Website should now be open in your default browser!")
    else:
        print("Error: website_proof_of_concept.html not found")
        print("Make sure you're running this from the project root directory")

if __name__ == "__main__":
    open_website()