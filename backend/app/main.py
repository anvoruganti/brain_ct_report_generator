"""FastAPI application entry point."""

import sys
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from backend.app.api.routes import router
from backend.app.config import get_settings

# Check Python version on startup
logger = logging.getLogger(__name__)
python_version = sys.version_info
BACKEND_PYTHON_VERSION = f"{python_version.major}.{python_version.minor}.{python_version.micro}"

print(f"BACKEND_PYTHON_VERSION: {BACKEND_PYTHON_VERSION}")
logger.info(f"Python version: {BACKEND_PYTHON_VERSION}")

if python_version.major == 3 and python_version.minor == 13:
    error_msg = (
        "⚠️ WARNING: Python 3.13 is not recommended for medical imaging!\n"
        "PyTorch, MONAI, and pixel decoding libraries may not work correctly.\n"
        "Please use Python 3.10 or 3.11 instead.\n"
        "Create venv: python3.11 -m venv .venv"
    )
    print(error_msg)
    logger.warning(error_msg)
elif python_version.major == 3 and python_version.minor >= 10:
    logger.info(f"✅ Python {python_version.major}.{python_version.minor} is supported")
else:
    logger.warning(f"Python {python_version.major}.{python_version.minor} may not be fully supported")

settings = get_settings()

app = FastAPI(
    title="Brain CT Report Generator API",
    description="API for generating clinical reports from Brain CT images using MONAI and LLM",
    version="0.1.0",
)

# Configure maximum upload size (500 MB default)
MAX_UPLOAD_SIZE = settings.max_upload_size_mb * 1024 * 1024  # Convert MB to bytes

class UploadSizeMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce maximum upload size."""
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            size = int(content_length)
            if size > MAX_UPLOAD_SIZE:
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Maximum upload size is {settings.max_upload_size_mb} MB. "
                           f"Received {size / 1024 / 1024:.2f} MB."
                )
        return await call_next(request)

app.add_middleware(UploadSizeMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    pass


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    pass
