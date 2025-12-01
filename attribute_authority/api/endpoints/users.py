from typing import List, Dict, Any
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from math import ceil

from ..dependencies import require_admin_claims, get_db_dependency, get_current_user_claims, optional_user_claims
from ...crud.user import crud_user
from ...crud.user_attribute_value import crud_attribute
from ...services.attribute import attribute_service
from ...schemas.user import UserOut
from ...core.logging_config import logger
from ...web.templating import templates

router = APIRouter()



@router.get("/admin/users", response_model=List[UserOut])
async def list_users(
    request: Request,
    page: int = Query(1, ge=1),
    claims: Dict[str, Any] = Depends(optional_user_claims), # TODO change in a way that only admins can access require_admin_claims
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
    per_page = 5
    total_users = len(users)
    page_count = max(1, ceil(total_users / per_page))
    if page > page_count:
        page = page_count
    
    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    page_users = users[start_index:end_index]

    display_claims = {
        "sub": claims.get("sub"),
        "iss": claims.get("iss"),
        "name": claims.get("name") or claims.get("preferred_username"),
        "email": claims.get("email"),
    }


    return templates.TemplateResponse(
        "users.html",
        {
            "request": request,
            "claims": display_claims, # Current Admin
            "users": page_users, # Rows rendered from actual users
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total_users,
                "page_count": page_count,
                "has_prev": page > 1,
                "has_next": page < page_count,
            },
        },
    )