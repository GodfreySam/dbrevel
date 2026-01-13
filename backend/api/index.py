"""
Vercel Serverless Function Handler for FastAPI
This file wraps the FastAPI app for Vercel's serverless environment.
"""
import sys
from pathlib import Path

from app.main import app
from mangum import Mangum

# Add parent directory to path so we can import app modules
# This must be done BEFORE importing app modules
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


# Create Mangum adapter for FastAPI
# Mangum converts ASGI (FastAPI) to the format expected by serverless platforms
# lifespan="off" because Vercel serverless functions don't support lifespan events
handler = Mangum(app, lifespan="off")
