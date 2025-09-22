from fastapi import APIRouter, Depends, Request
from pathlib import Path
from typing import Dict, Any
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_current_user_claims, get_db_dependency, optional_user_claims
from ...services.user_service import user_service
from ...core.logging_config import logger

router = APIRouter()

# Set up templates directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

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


@router.get("/myattributes", response_model=Dict[str, Any])
async def myattributes(
    request: Request,
    claims: Dict[str, Any] = Depends(optional_user_claims),
    db: AsyncSession = Depends(get_db_dependency()),
):
    """
    Attribute Authority My Attributes Endpoint.
    Returns all attributes of the current user.
    """
    if not claims:
        login_url = f"/api/v1/auth/login?next=/api/v1/myattributes"
        return RedirectResponse(url=login_url)

    logger.info(f"Processing myattributes request for sub: {claims.get('sub')}")

    # Fetch user attributes using your existing service
    attributes = await user_service.get_userattributes(db, claims)

    display_claims = {
        "sub": claims.get("sub"),
        "iss": claims.get("iss"),
        "name": claims.get("name") or claims.get("preferred_username"),
        "email": claims.get("email"),
    }

    return templates.TemplateResponse(
        "user_attributes.html",
        {
            "request": request,
            "claims": display_claims,
            "attributes": attributes,
        },
    )




