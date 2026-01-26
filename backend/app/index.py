"""
Vercel Serverless Function Handler for FastAPI
This file wraps the FastAPI app for Vercel's serverless environment.
"""

import logging
import sys
import traceback
from pathlib import Path

# Ensure project root is on path BEFORE importing app modules
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

try:
    from app.core.config import settings  # noqa: E402

    # Configure console logging so Vercel captures logs from stdout/stderr
    # Uses LOG_LEVEL from app settings when available
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # Import the FastAPI app — Vercel's @vercel/python runtime has native ASGI
    # support and will detect the `app` variable automatically
    from app.main import app  # noqa: E402, F401

except Exception:
    # Log the real error so it appears in Vercel function logs
    traceback.print_exc()
    print(
        "ERROR: Failed to initialize the application. See traceback above.",
        file=sys.stderr,
        flush=True,
    )
    raise
