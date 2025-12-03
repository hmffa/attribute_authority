from fastapi import APIRouter

from .endpoints import (
    attributes, 
    invitations, 
    auth, 
    users, 
    attribute_definitions,
    privileges
)

# API router for version 1
api_router = APIRouter()
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(users.router, tags=["users"])
api_router.include_router(attributes.router, tags=["user_attributes"])
api_router.include_router(attribute_definitions.router, tags=["schema_definitions"])
api_router.include_router(privileges.router, tags=["privileges"])
api_router.include_router(invitations.router, tags=["invitations"])
