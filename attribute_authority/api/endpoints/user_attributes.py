from fastapi import APIRouter, Depends, Request
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_current_user_claims, get_db_dependency
from ...services.user_service import user_service
from ...core.logging_config import logger

router = APIRouter()

@router.get("/userattributes", response_model=Dict[str, Any])
async def userattributes(
    request: Request,
    claims: Dict[str, Any] = Depends(get_current_user_claims),
    db: AsyncSession = Depends(get_db_dependency()),
):
    """
    Attribute Authority User Attributes Endpoint.
    Returns user attributes based on the provided access token.
    """
    logger.info(f"Processing userattributes request for sub: {claims.get('sub')}")
    return await user_service.get_userattributes(db, claims)

@router.get("/userattributes/{key}", response_model=Dict[str, Any])
async def userattribute(
    key: str,
    request: Request,
    claims: Dict[str, Any] = Depends(get_current_user_claims),
    db: AsyncSession = Depends(get_db_dependency()),
):
    """
    Attribute Authority User Attribute Endpoint.
    Returns a specific user attribute based on the provided access token.
    """
    logger.info(f"Processing userattribute request for sub: {claims.get('sub')} and key: {key}")
    return await user_service.get_userattribute(db, claims, key)
