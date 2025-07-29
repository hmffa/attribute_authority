from fastapi import APIRouter

from .endpoints import userinfo

# API router for version 1
api_router = APIRouter()
api_router.include_router(userinfo.router, tags=["userinfo"])
