"""User endpoints."""
from math import ceil
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_current_actor, optional_user_claims
from ...db.session import get_async_db
from ...models.user import User
from ...schemas.user import UserOut, UserWithAttributes
from ...services import user as users
from ...web.templating import templates

router = APIRouter()


@router.get("/admin/users", response_model=List[UserOut])
async def list_users(
    request: Request,
    page: int = Query(1, ge=1),
    claims: Dict[str, Any] = Depends(optional_user_claims),
    db: AsyncSession = Depends(get_async_db),
):
    """Attribute Authority List Users Endpoint (Admin UI)."""
    if not claims:
        login_url = f"/api/v1/auth/login?next={request.url.path}"
        return RedirectResponse(url=login_url)

    per_page = 5
    result = await users.list_users_paginated(db, page=page, per_page=per_page)

    total_users = result["total"]
    page_count = max(1, ceil(total_users / per_page))

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
            "users": result["items"],
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
    db: AsyncSession = Depends(get_async_db),
    actor: User = Depends(get_current_actor),
):
    """Returns all users with only attributes the caller has permission to read."""
    return await users.get_all_users_with_visible_attributes(db, actor)