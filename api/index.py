"""
Vercel serverless function wrapper for FastAPI app.
Uses Mangum to convert ASGI app to Lambda/API Gateway format.
"""
import sys
import os

# Add parent directory to path
parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent)

from mangum import Mangum
from app.main import app

# Initialize Mangum handler - this converts FastAPI (ASGI) to Lambda format
_app_handler = Mangum(app, lifespan="off")

# Vercel expects a 'handler' function that takes (event, context)
def handler(event, context=None):
    """Vercel serverless function handler"""
    return _app_handler(event, context or {})

