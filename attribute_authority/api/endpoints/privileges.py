from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import require_privilege
from ...db.session import get_async_db
from ...services.privilege import privilege_service
from ...schemas.privilege import PrivilegeCreate, PrivilegeRead
from ...models.privilege import PrivilegeAction
from ...crud.privilege import crud_privilege
from ...models.privilege import Privilege

router = APIRouter()

@router.post("/privileges", response_model=PrivilegeRead)
async def grant_privilege(
    privilege_in: PrivilegeCreate,
    db: AsyncSession = Depends(get_async_db),
    # Only superadmins with ASSIGN_PRIVILEGE can do this
    _ = Depends(require_privilege(PrivilegeAction.ASSIGN_PRIVILEGE))
):
    """
    Grant a new privilege to a user.
    Example payload:
    {
        "grantee_user_id": 123,
        "action": "add_value",
        "value_restriction": "^urn:physics:.*"
    }
    """
    # Note: Service expects sub/iss for grantee lookup, 
    # but schema might provide ID directly. 
    # Adapting to schema:
    
    # We might need to fetch the grantee user object if the service requires sub/iss
    # OR update the service to accept ID. 
    # Assuming service update or simple logic here:
    
    # For now, let's assume we pass the raw data to CRUD or Service 
    # if the Service supports ID-based creation (which is efficient).
    
    # Use the CRUD directly if Service is strictly for sub/iss lookup logic
    # or update Service to handle ID.
    
    db_obj = Privilege(
        grantee_user_id=privilege_in.grantee_user_id,
        action=privilege_in.action,
        attribute_id=privilege_in.attribute_id,
        value_restriction=privilege_in.value_restriction,
        target_restriction=privilege_in.target_restriction,
        is_delegable=privilege_in.is_delegable,
        created_at="Now"  # Placeholder, will be set in CRUD
    )
    return await crud_privilege.create(db, db_obj)