"""Attribute definition endpoints."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import require_privilege
from ...db.session import get_async_db
from ...models.privilege import PrivilegeAction
from ...schemas.attribute import AttributeCreate, AttributeRead
from ...services import attribute_definition as attributes

router = APIRouter()


@router.post("/definitions", response_model=AttributeRead)
async def create_attribute_definition(
    obj_in: AttributeCreate,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(require_privilege(PrivilegeAction.CREATE_ATTR)),
):
    """Define a new attribute in the schema."""
    return await attributes.create(db, obj_in)


@router.get("/definitions", response_model=List[AttributeRead])
async def list_attribute_definitions(
    db: AsyncSession = Depends(get_async_db),
    _=Depends(require_privilege(PrivilegeAction.READ_ATTR)),
):
    """List all attribute definitions."""
    return await attributes.get_all(db)


@router.get("/definitions/{name}", response_model=AttributeRead)
async def get_attribute_definition(
    name: str,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(require_privilege(PrivilegeAction.READ_ATTR)),
):
    """Get a specific attribute definition."""
    attr = await attributes.get_by_name(db, name)
    if not attr:
        raise HTTPException(status_code=404, detail="Attribute definition not found")
    return attr