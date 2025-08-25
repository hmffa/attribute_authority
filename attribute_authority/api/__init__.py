from fastapi import APIRouter

from .endpoints import user_attributes, admin, invitations

# API router for version 1
api_router = APIRouter()
api_router.include_router(user_attributes.router, tags=["userinfo"])
api_router.include_router(admin.router, tags=["admin"])
api_router.include_router(invitations.router, tags=["invitations"])
