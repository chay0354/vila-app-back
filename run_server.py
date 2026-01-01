#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Entry point script to run the FastAPI server.
This script properly sets up the Python path and runs the app.
"""

import sys
import os
import io

# Fix Windows console encoding to support emojis and Unicode
if sys.platform == 'win32':
    try:
        # Set stdout and stderr to UTF-8 encoding
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8')
        # Also set environment variable for subprocesses
        os.environ['PYTHONIOENCODING'] = 'utf-8'
    except Exception:
        # If reconfiguration fails, wrap stdout/stderr with UTF-8 encoder
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

# Now we can import the app
from app.main import app

if __name__ == '__main__':
    import uvicorn
    
    # Get port from environment or use default
    port = int(os.getenv('PORT', 4000))
    host = os.getenv('HOST', '0.0.0.0')
    
    print(f"Starting server on {host}:{port}")
    print("Press Ctrl+C to stop")
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=True,
        reload_dirs=["app"]
    )





