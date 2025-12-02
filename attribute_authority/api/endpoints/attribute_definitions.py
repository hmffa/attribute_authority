from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from ..dependencies import get_db_dependency, require_attribute_privilege
from ...schemas.attribute import AttributeCreate, AttributeRead
from ...services.attribute_definition import attribute_definition_service
from ...models.privilege import PrivilegeAction

router = APIRouter()

@router.post("/attributes", response_model=AttributeRead)
async def create_attribute_definition(
    obj_in: AttributeCreate,
    db: AsyncSession = Depends(get_db_dependency()),
    # Check if user has 'CREATE_ATTR' privilege
    _ = Depends(require_attribute_privilege(PrivilegeAction.CREATE_ATTR))
):
    return await attribute_definition_service.create(db, obj_in)