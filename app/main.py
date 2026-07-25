"""
main.py

WHY THIS FILE EXISTS:
This is the single entrypoint of your application — the file uvicorn actually
runs. Its job is narrow and disciplined:
1. Create the FastAPI app instance.
2. Wire up logging.
3. Register global exception handlers (so every part of the app that raises
   an AppException gets turned into a clean JSON response, automatically).
4. Include routers from other files (Phase 3 onward — WhatsApp webhook,
   registration, login, etc. each live in their own router file).
5. Expose a health-check endpoint so you (and later, your monitoring/uptime
   tool) can confirm the server is alive.

Notice what's NOT here: no business logic, no database queries directly in
this file. That logic belongs in dedicated modules we'll build in later
phases. main.py just assembles the pieces.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.core.exceptions import AppException
from app.logging_config import setup_logging

settings = get_settings()
setup_logging(debug=settings.debug)

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    description="AI-powered WhatsApp Customer Service Platform for H-Engineers Enterprise",
    version="0.1.0",
)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """
    Catches any of our custom exceptions (see core/exceptions.py) raised
    ANYWHERE in the app and converts them into a consistent JSON shape.
    Without this, FastAPI would return a generic, unhelpful 500 error.
    """
    logger.warning(f"AppException on {request.url.path}: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": exc.message},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    Safety net: catches anything we DIDN'T anticipate, logs it with full
    detail (so you can debug it), but shows the customer a safe generic
    message instead of a stack trace.
    """
    logger.error(f"Unhandled exception on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "Internal server error"},
    )


@app.get("/health", tags=["System"])
async def health_check():
    """
    Simple liveness check. In Phase 14 (Deployment) this is what your
    monitoring / uptime tool will poll to confirm the server is up.
    """
    return {"status": "ok", "app": settings.app_name, "environment": settings.environment}


@app.get("/", tags=["System"])
async def root():
    return {"message": f"{settings.app_name} is running."}


# Routers will be added here in later phases, e.g.:
# from app.routers import whatsapp
# app.include_router(whatsapp.router, prefix="/webhook", tags=["WhatsApp"])
from app.core.exceptions import NotFoundException

@app.get("/ping", tags=["System"])
async def ping():
   return {"pong": True}