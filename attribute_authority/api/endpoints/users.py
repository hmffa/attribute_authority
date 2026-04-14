"""User endpoints."""
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_current_actor
from ...db.session import get_async_db
from ...models.user import User
from ...schemas.user import UserWithAttributes
from ...services import user as users

router = APIRouter()


@router.get("/users/allattributes", response_model=List[UserWithAttributes])
async def get_all_users_attributes(
    db: AsyncSession = Depends(get_async_db),
    actor: User = Depends(get_current_actor),
):
    """Returns all users with only attributes the caller has permission to read."""
    return await users.get_all_users_with_visible_attributes(db, actor)