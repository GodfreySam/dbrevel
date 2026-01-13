"""
Vercel Serverless Function Handler for FastAPI
This file wraps the FastAPI app for Vercel's serverless environment.
"""
from mangum import Mangum
from app.main import app
from app.core.config import settings
import logging
import sys
from pathlib import Path

# Ensure project root is on path BEFORE importing app modules
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Configure console logging so Vercel captures logs from stdout/stderr
# Uses LOG_LEVEL from app settings when available

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")


# Create Mangum adapter for FastAPI
# Mangum converts ASGI (FastAPI) to the format expected by serverless platforms
# lifespan="off" because Vercel serverless functions don't support lifespan events
handler = Mangum(app, lifespan="off")
