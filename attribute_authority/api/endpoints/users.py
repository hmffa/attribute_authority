from typing import List, Dict, Any
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import require_admin_claims, get_db_dependency, get_current_user_claims
from ...crud.user import crud_user
from ...crud.attribute import crud_attribute
from ...services.attribute_service import attribute_service
from ...schemas.user import UserOut
from ...core.logging_config import logger

router = APIRouter()



@router.get("/admin/users", response_model=List[UserOut])
async def list_users(
    request: Request,
    claims: Dict[str, Any] = Depends(require_admin_claims),
    db: AsyncSession = Depends(get_db_dependency()),
):
    """
    Attribute Authority List Users Endpoint.
    Return list of all users and their information
    """
    current_url = request.url.path
    if not claims:
        login_url = f"/api/v1/auth/login?next={current_url}"
        return RedirectResponse(url=login_url)
    
    logger.info(f"Processing list_users request by admin sub: {claims.get('sub')}")
    users = await crud_user.get_all(db)
    return users
