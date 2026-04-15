from contextlib import asynccontextmanager
import time
from typing import Callable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from .api import api_router
from .core.config import settings
from .core.logging_config import logger
from .web.routes import router as ui_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME}")
    # insert_user_from_config() # TODO populate DB from config automatically
    yield
    logger.info(f"Shutting down {settings.APP_NAME}")

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
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

app.mount("/static", StaticFiles(directory="attribute_authority/web/static"), name="static")

# app.add_middleware(
#     SessionMiddleware,
#     secret_key=settings.SECRET_KEY,
#     session_cookie="aa_session",
#     same_site="lax",
#     https_only=settings.ENVIRONMENT == "production",
#     max_age=3600,
# )


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
    same_site="lax",
    https_only=settings.ENVIRONMENT == "production",
    max_age=3600,
)

# Include API router
app.include_router(ui_router)
app.include_router(api_router, prefix=settings.API_V1_STR)



