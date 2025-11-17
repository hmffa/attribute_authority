from fastapi import APIRouter

from .endpoints import attributes, invitations, auth, users

# API router for version 1
api_router = APIRouter()
api_router.include_router(attributes.router, tags=["userinfo"])
api_router.include_router(users.router, tags=["admin"])
api_router.include_router(invitations.router, tags=["invitations"])
api_router.include_router(auth.router, tags=["auth"])
