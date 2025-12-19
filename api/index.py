"""
Vercel serverless function wrapper for FastAPI app.
This file is required for Vercel to properly route requests to the FastAPI app.
"""
import sys
import os

# Add the parent directory to the path so we can import app
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from mangum import Mangum
from app.main import app

# Create ASGI handler for Vercel
# Mangum converts ASGI app to AWS Lambda/API Gateway format that Vercel uses
# Export as a callable handler function
def handler(event, context):
    """Vercel serverless function handler"""
    asgi_handler = Mangum(app, lifespan="off")
    return asgi_handler(event, context)

