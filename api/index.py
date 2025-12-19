"""
Vercel serverless function wrapper for FastAPI app.
This file is required for Vercel to properly route requests to the FastAPI app.
"""
import sys
import os

# Add the parent directory to the path so we can import app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mangum import Mangum
from app.main import app

# Create ASGI handler for Vercel
handler = Mangum(app, lifespan="off")

# Export handler for Vercel
__all__ = ["handler"]

