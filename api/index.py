import sys
import os

# Add parent directory to path
parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent not in sys.path:
    sys.path.insert(0, parent)

from mangum import Mangum
from app.main import app

# Export handler directly - Vercel expects this variable name
handler = Mangum(app)

