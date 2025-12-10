from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import require_privilege
from ...db.session import get_async_db
from ...schemas.attribute import AttributeCreate, AttributeRead, AttributeUpdate
from ...services.attribute_definition import attribute_definition_service
from ...crud.attribute_definition import crud_attribute_definition
from ...models.privilege import PrivilegeAction

router = APIRouter()

@router.post("/definitions", response_model=AttributeRead)
async def create_attribute_definition(
    obj_in: AttributeCreate,
    db: AsyncSession = Depends(get_async_db),
    _ = Depends(require_privilege(PrivilegeAction.CREATE_ATTR))
):
    """
    Define a new attribute in the schema (e.g. 'eduPersonEntitlement').
    """
    return await attribute_definition_service.create(db, obj_in)

@router.get("/definitions", response_model=List[AttributeRead])
async def list_attribute_definitions(
    db: AsyncSession = Depends(get_async_db),
    # READ_ATTR privilege might be required, or public? Assuming protected:
    _ = Depends(require_privilege(PrivilegeAction.READ_ATTR))
):
    return await crud_attribute_definition.get_all(db)

@router.get("/definitions/{name}", response_model=AttributeRead)
async def get_attribute_definition(
    name: str,
    db: AsyncSession = Depends(get_async_db),
    _ = Depends(require_privilege(PrivilegeAction.READ_ATTR))
):
    attr = await crud_attribute_definition.get_by_name(db, name)
    if not attr:
        raise HTTPException(status_code=404, detail="Attribute definition not found")
    return attr