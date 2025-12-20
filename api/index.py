import sys
import os

# Add parent directory to path
parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent not in sys.path:
    sys.path.insert(0, parent)

from mangum import Mangum
from app.main import app

# Create Mangum adapter for AWS Lambda/Vercel compatibility
# lifespan="off" disables ASGI lifespan events which aren't supported in serverless
mangum_handler = Mangum(app, lifespan="off")

# Export handler - Vercel Python runtime expects this variable name
# The handler must be callable and compatible with AWS Lambda event format
handler = mangum_handler

