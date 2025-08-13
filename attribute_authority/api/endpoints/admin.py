from typing import List, Dict, Any
from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from ...core.config import settings
from ..dependencies import require_admin_claims, get_db_dependency, get_current_user_claims
from ...crud.user import crud_user
from ...crud.user_attribute import crud_user_attribute
from ...schemas.user import UserCreate
from ...schemas.user_attribute import AttributeMutation, UserAttributeCreate
from ...core.logging_config import logger

router = APIRouter()

@router.put("/admin/attributes/{key}", response_model=Dict[str, List[str]])
async def set_attributes(
    key: str,
    body: AttributeMutation,
    claims: Dict[str, Any] = Depends(get_current_user_claims),
    db: AsyncSession = Depends(get_db_dependency()),
):
    sub = claims.get("sub")
    iss = claims.get("iss")
    if not sub or not iss:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing sub or iss in token")

    user = await crud_user.get_by_sub_and_iss(db, sub=sub, iss=iss)
    if not user:
        user = await crud_user.create(db, UserCreate(sub=sub, iss=iss))

    current = {ua.value for ua in await crud_user_attribute.get_by_user_id_and_key(db, user.id, key)}
    desired = set(body.values)

    for v in desired - current:
        await crud_user_attribute.add_value(db, user.id, key, v)
    for v in current - desired:
        await crud_user_attribute.remove_value(db, user.id, key, v)

    updated = await crud_user_attribute.get_by_user_id_and_key(db, user.id, key)
    return {key: [ua.value for ua in updated]}

@router.post("/admin/attributes/{key}", response_model=Dict[str, List[str]])
async def add_attributes(
    key: str,
    body: AttributeMutation,
    # claims: Dict[str, Any] = Depends(require_admin_claims),
    claims: Dict[str, Any] = Depends(get_current_user_claims),
    db: AsyncSession = Depends(get_db_dependency()),
):
    sub = claims.get("sub")
    iss = claims.get("iss")
    if not sub or not iss:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing sub or iss in token")

    user = await crud_user.get_by_sub_and_iss(db, sub=sub, iss=iss)
    if not user:
        user = await crud_user.create(db, UserCreate(sub=sub, iss=iss))

    for v in body.values:
        user_attribute_create_obj = UserAttributeCreate(user_id=user.id, key=key, value=v)
        await crud_user_attribute.create(db, obj_in=user_attribute_create_obj)

    updated = await crud_user_attribute.get_by_user_id_and_key(db, user.id, key)
    return {key: [ua.value for ua in updated]}

@router.delete("/admin/attributes/{key}", response_model=Dict[str, List[str]])
async def remove_attributes(
    key: str,
    body: AttributeMutation,
    claims: Dict[str, Any] = Depends(require_admin_claims),
    db: AsyncSession = Depends(get_db_dependency()),
):
    sub = claims.get("sub")
    iss = claims.get("iss")
    if not sub or not iss:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing sub or iss in token")

    user = await crud_user.get_by_sub_and_iss(db, sub=sub, iss=iss)
    if not user:
        return {key: []}

    for v in body.values:
        await crud_user_attribute.remove_value(db, user.id, key, v)

    updated = await crud_user_attribute.get_by_user_id_and_key(db, user.id, key)
    return {key: [ua.value for ua in updated]}