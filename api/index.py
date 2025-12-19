import sys
import os

# Add parent directory to path
parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent not in sys.path:
    sys.path.insert(0, parent)

from mangum import Mangum
from app.main import app

# Export handler as a callable function
# Vercel expects handler(event, context) signature
mangum_app = Mangum(app, lifespan="off")

def handler(event, context):
    return mangum_app(event, context)

