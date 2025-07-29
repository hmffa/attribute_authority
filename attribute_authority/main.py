from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import time
from typing import Callable
from starlette.requests import Request
from starlette.responses import Response
from contextlib import asynccontextmanager
from alembic.config import Config
from alembic import command

from .api import api_router
from .core.config import settings
from .core.logging_config import logger
from .api.endpoints.userinfo import userinfo as versioned_userinfo
from .api.dependencies import get_current_user_claims, get_db_dependency

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME}")
    yield
    logger.info(f"Shutting down {settings.APP_NAME}")

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# Set up CORS middleware
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Logging middleware
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Process the request
        response = await call_next(request)
        
        # Log request details
        process_time = time.time() - start_time
        logger.info(
            f"{request.method} {request.url.path} {response.status_code} "
            f"Completed in {process_time:.4f}s"
        )
        
        return response

# Add middleware
app.add_middleware(LoggingMiddleware)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)

# For backwards compatibility, include a non-versioned route as well
@app.get("/userinfo")
async def legacy_userinfo(response: Response, request: Request):
    """Legacy userinfo endpoint for backward compatibility"""
    
    claims = await get_current_user_claims(request)
    db = await anext(get_db_dependency()())
    
    return await versioned_userinfo(request, claims, db)

@app.get("/")
async def root():
    return {
        "app_name": settings.APP_NAME,
        "message": "Welcome to UserInfo API. Access /userinfo with a valid token."
    }

