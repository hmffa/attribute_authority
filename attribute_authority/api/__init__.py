from fastapi import APIRouter

from .endpoints import user_attributes

# API router for version 1
api_router = APIRouter()
api_router.include_router(user_attributes.router, tags=["userinfo"])
