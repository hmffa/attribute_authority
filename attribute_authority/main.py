from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
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
from .api.endpoints.user_attributes import userattributes as versioned_userattributes
from .api.dependencies import get_current_user_claims, get_db_dependency
from .scripts.startup import insert_user_from_config

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME}")
    # insert_user_from_config() # TODO populate DB from config automatically
    yield
    logger.info(f"Shutting down {settings.APP_NAME}")

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
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

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,  
    max_age=86400 * 30,              # Optional: session expiry (30 days)
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)

# For backwards compatibility, include a non-versioned route as well
@app.get("/userattributes")
async def legacy_userattributes(response: Response, request: Request):
    """Legacy userattributes endpoint for backward compatibility"""

    claims = await get_current_user_claims(request)
    db = await anext(get_db_dependency()())

    return await versioned_userattributes(request, claims, db)

@app.get("/")
async def root():
    return {
        "app_name": settings.APP_NAME,
        "message": "Welcome to UserInfo API. Access /userinfo with a valid token."
    }

