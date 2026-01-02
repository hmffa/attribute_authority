"""User attribute endpoints."""
from typing import Any, Dict

from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_current_actor, get_current_user_claims
from ...db.session import get_async_db
from ...models.user import User
from ...schemas.user_attribute_value import UserAttributeValueRead
from ...services import user_attribute_value as user_attributes

router = APIRouter()


# --- Self Service (My Attributes) ---

@router.get("/user/myattributes")
async def read_my_attributes(
    claims: Dict[str, Any] = Depends(get_current_user_claims),
    db: AsyncSession = Depends(get_async_db),
):
    """Get logged-in user's own attributes."""
    return await user_attributes.get_user_attributes(
        db, sub=claims.get("sub"), iss=claims.get("iss")
    )


# --- Admin / Manager Actions (On Target Users) ---

@router.post(
    "/users/{user_id}/attributes/{attribute_name}",
    response_model=UserAttributeValueRead,
)
async def add_user_attribute_value(
    user_id: int,
    attribute_name: str,
    value: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_async_db),
    actor: User = Depends(get_current_actor),
):
    """Add a value to a specific user's attribute."""
    return await user_attributes.add_value(
        db,
        target_user_id=user_id,
        attribute_name=attribute_name,
        value=value,
        actor=actor,
    )


@router.delete("/users/{user_id}/values/{value_id}")
async def remove_user_attribute_value(
    user_id: int,
    value_id: int,
    db: AsyncSession = Depends(get_async_db),
    actor: User = Depends(get_current_actor),
):
    """Remove a specific value from a user."""
    # TODO: Add authorization check for REMOVE_VALUE
    await user_attributes.remove_value(db, value_id=value_id)
    return {"status": "success", "message": "Value removed"}