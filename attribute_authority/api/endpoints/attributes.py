from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_db_dependency, get_current_user_claims, require_privilege
from ...services.user_attribute_value import user_attribute_value_service
from ...models.privilege import PrivilegeAction
from ...schemas.user_attribute_value import UserAttributeValueRead

router = APIRouter()

# --- Self Service (My Attributes) ---

@router.get("/user/myattributes")
async def read_my_attributes(
    claims: Dict[str, Any] = Depends(get_current_user_claims),
    db: AsyncSession = Depends(get_db_dependency())
):
    """
    Get logged-in user's own attributes.
    """
    return await user_attribute_value_service.get_user_attributes(
        db, sub=claims.get("sub"), iss=claims.get("iss")
    )

# --- Admin / Manager Actions (On Target Users) ---
    

@router.post("/users/{user_id}/attributes/{attribute_name}", response_model=UserAttributeValueRead)
async def add_user_attribute_value(
    user_id: int,
    attribute_name: str,
    value: str = Body(..., embed=True), # Expects JSON: {"value": "foo"}
    db: AsyncSession = Depends(get_db_dependency()),
    # Check Privilege: ADD_VALUE
    _ = Depends(require_privilege(PrivilegeAction.ADD_VALUE)) 
):
    """
    Add a value to a specific user's attribute. 
    Enforces regex and multi-value constraints defined in schema.
    """
    return await user_attribute_value_service.add_value(
        db, 
        target_user_id=user_id, 
        attribute_name=attribute_name, 
        value=value,
        source="admin_api"
    )

@router.delete("/users/{user_id}/values/{value_id}")
async def remove_user_attribute_value(
    user_id: int,
    value_id: int,
    db: AsyncSession = Depends(get_db_dependency()),
    # Check Privilege: REMOVE_VALUE
    _ = Depends(require_privilege(PrivilegeAction.REMOVE_VALUE))
):
    """
    Remove a specific value from a user.
    """
    await user_attribute_value_service.remove_value(db, user_value_id=value_id)
    return {"status": "success", "message": "Value removed"}