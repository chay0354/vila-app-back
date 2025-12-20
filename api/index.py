import sys
import os

# Add parent directory to path
parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent not in sys.path:
    sys.path.insert(0, parent)

from app.main import app

# Export app directly - Vercel natively supports ASGI applications like FastAPI
# Do NOT use 'handler' variable name as Vercel expects that to be a BaseHTTPRequestHandler subclass

