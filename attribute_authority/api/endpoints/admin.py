from typing import List, Literal
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from ...core.config import settings
from ..dependencies import get_db_dependency
from ...crud.user import crud_user
from ...crud.user_attribute import crud_user_attribute
from ...schemas.user import UserCreate

router = APIRouter()

class AttributeMutation(BaseModel):
    iss: str
    values: List[str]
    mode: Literal["add", "remove", "set"] = "set"

async def require_admin(x_aa_admin_token: str = Header(default="")):
    if not settings.ADMIN_TOKEN or x_aa_admin_token != settings.ADMIN_TOKEN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

@router.put("/admin/users/{sub}/attributes/{key}", dependencies=[Depends(require_admin)])
async def mutate_attributes(
    sub: str,
    key: str,
    body: AttributeMutation,
    db: AsyncSession = Depends(get_db_dependency()),
):
    # Ensure user exists (create if missing to ease bootstrap)
    user = await crud_user.get_by_sub_and_iss(db, sub=sub, iss=body.iss)
    if not user:
        user = await crud_user.create(db, UserCreate(sub=sub, iss=body.iss))

    if body.mode == "set":
        # fetch current values for the key
        current = {ua.value for ua in await crud_user_attribute.get_by_user_id_and_key(db, user.id, key)}
        desired = set(body.values)

        # add missing
        for v in desired - current:
            await crud_user_attribute.add_value(db, user.id, key, v)
        # remove extras
        for v in current - desired:
            await crud_user_attribute.remove_value(db, user.id, key, v)
    elif body.mode == "add":
        for v in body.values:
            await crud_user_attribute.add_value(db, user.id, key, v)
    elif body.mode == "remove":
        for v in body.values:
            await crud_user_attribute.remove_value(db, user.id, key, v)

    # Return the updated values for the key
    updated = await crud_user_attribute.get_by_user_id_and_key(db, user.id, key)
    return {key: [ua.value for ua in updated]}