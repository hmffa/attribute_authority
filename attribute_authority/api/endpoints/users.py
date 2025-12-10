from typing import List, Dict, Any
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from math import ceil

from ..dependencies import get_db_dependency, optional_user_claims, get_current_actor
from ...crud.user import crud_user
from ...models.user import User
from ...schemas.user import UserOut, UserWithAttributes
from ...services.user import user_service
from ...core.logging_config import logger
from ...web.templating import templates

router = APIRouter()



@router.get("/admin/users", response_model=List[UserOut])
async def list_users(
    request: Request,
    page: int = Query(1, ge=1),
    claims: Dict[str, Any] = Depends(optional_user_claims), # TODO change in a way that users can access here based on privileges (Can all users list other users?)
    db: AsyncSession = Depends(get_db_dependency()),
):
    """
    Attribute Authority List Users Endpoint (Admin UI).
    """
    # 1. Auth Check (Redirect to login if missing)
    if not claims:
        login_url = f"/api/v1/auth/login?next={request.url.path}"
        return RedirectResponse(url=login_url)
    
    # 2. Call Service (Efficient Pagination)
    per_page = 5
    result = await user_service.list_users(db, page=page, per_page=per_page)
    
    # 3. Calculate Pagination Metadata for Template
    total_users = result["total"]
    page_count = max(1, ceil(total_users / per_page))
    
    # 4. Prepare Context
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
            "claims": display_claims,
            "users": result["items"], # The slice from DB
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

@router.get("/users/allattributes", response_model=List[UserWithAttributes])
async def get_all_users_attributes(
    db: AsyncSession = Depends(get_db_dependency),
    actor: User = Depends(get_current_actor)
):
    """
    Returns a list of ALL users and ONLY the attributes/values the caller has permission to read.
    """
    return await user_service.get_all_users_with_visible_attributes(db, actor)