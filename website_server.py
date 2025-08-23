#!/usr/bin/env python3
"""
Simple HTTP Server for VeritasLogic.ai Multi-Page Website Preview
Serves the complete website on port 8000 for easy Chrome browser preview
"""

import http.server
import socketserver
import os
import threading
import webbrowser
from pathlib import Path

class WebsiteHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory="veritaslogic_multipage_website", **kwargs)
    
    def end_headers(self):
        # Add CORS headers for development
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_GET(self):
        # Serve index.html for root path
        if self.path == '/':
            self.path = '/index.html'
        
        return super().do_GET()
    
    def log_message(self, format, *args):
        # Custom logging to show which pages are being accessed
        print(f"[Website Server] {args[0]} - {args[1]} {args[2]}")

def start_server():
    """Start the website server"""
    PORT = 8000
    
    # Check if the website directory exists
    if not os.path.exists("veritaslogic_multipage_website"):
        print("❌ Website directory not found!")
        return False
    
    # Check if all required files exist
    required_files = [
        "index.html", "about.html", "features.html", 
        "pricing.html", "blog.html", "contact.html",
        "styles.css", "script.js"
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(f"veritaslogic_multipage_website/{file}"):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing files: {', '.join(missing_files)}")
        return False
    
    try:
        # Create server
        with socketserver.TCPServer(("", PORT), WebsiteHandler) as httpd:
            print(f"""
🚀 VeritasLogic.ai Website Server Started!

📱 Access your website at:
   http://localhost:{PORT}
   
🌐 Available pages:
   • Home:     http://localhost:{PORT}/
   • About:    http://localhost:{PORT}/about.html
   • Features: http://localhost:{PORT}/features.html
   • Pricing:  http://localhost:{PORT}/pricing.html
   • Blog:     http://localhost:{PORT}/blog.html
   • Contact:  http://localhost:{PORT}/contact.html

💡 Tips:
   • Open in Chrome for best experience
   • All styling and JavaScript fully functional
   • No need to download files - just browse!
   • Press Ctrl+C to stop the server

🔧 Server running from: {os.path.abspath('veritaslogic_multipage_website')}
            """)
            
            # Serve forever
            httpd.serve_forever()
            
    except OSError as e:
        if e.errno == 48:  # Address already in use
            print(f"❌ Port {PORT} is already in use. Trying port {PORT + 1}...")
            PORT += 1
            return start_server_on_port(PORT)
        else:
            print(f"❌ Error starting server: {e}")
            return False
    
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
        return True

def start_server_on_port(port):
    """Start server on specific port"""
    try:
        with socketserver.TCPServer(("", port), WebsiteHandler) as httpd:
            print(f"🚀 Server started on http://localhost:{port}")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
        return True

if __name__ == "__main__":
    # Change to the correct directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    print("🌐 Starting VeritasLogic.ai Website Server...")
    start_server()