#!/usr/bin/env python3
"""
Entry point script to run the FastAPI server.
This script properly sets up the Python path and runs the app.
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

# Now we can import the app
from app.main import app

if __name__ == '__main__':
    import uvicorn
    
    # Get port from environment or use default
    port = int(os.getenv('PORT', 8000))
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


