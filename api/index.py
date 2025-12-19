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

try:
    from mangum import Mangum
    from app.main import app
    
    # Create ASGI handler for Vercel
    # Mangum converts ASGI app to AWS Lambda/API Gateway format that Vercel uses
    handler = Mangum(app, lifespan="off")
except Exception as e:
    # Fallback for debugging
    def handler(event, context):
        return {
            "statusCode": 500,
            "body": f"Error initializing app: {str(e)}"
        }

