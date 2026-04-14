"""Privilege endpoints."""
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_current_actor, require_privilege
from ...db.session import get_async_db
from ...models.privilege import PrivilegeAction
from ...models.user import User
from ...schemas.privilege import PrivilegeCreate, PrivilegeDelegate, PrivilegeRead, PrivilegeUpdate
from ...services import privilege as privileges

router = APIRouter()


@router.get("/privileges", response_model=List[PrivilegeRead])
async def list_privileges(
    db: AsyncSession = Depends(get_async_db),
    _=Depends(require_privilege(PrivilegeAction.ASSIGN_PRIVILEGE)),
):
    """List all privileges."""
    return await privileges.get_all(db)


@router.get("/privileges/{privilege_id}", response_model=PrivilegeRead)
async def get_privilege(
    privilege_id: int,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(require_privilege(PrivilegeAction.ASSIGN_PRIVILEGE)),
):
    """Get a single privilege."""
    return await privileges.get_or_404(db, privilege_id)


@router.post("/privileges", response_model=PrivilegeRead)
async def grant_privilege(
    privilege_in: PrivilegeCreate,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(require_privilege(PrivilegeAction.ASSIGN_PRIVILEGE)),
):
    """Grant a new privilege to a user."""
    return await privileges.assign_privilege_by_id(
        db,
        grantee_user_id=privilege_in.grantee_user_id,
        action=privilege_in.action,
        attribute_id=privilege_in.attribute_id,
        value_restriction=privilege_in.value_restriction,
        target_restriction=privilege_in.target_restriction,
        is_delegable=privilege_in.is_delegable,
    )

@router.put("/privileges/{privilege_id}", response_model=PrivilegeRead)
async def update_privilege(
    privilege_id: int,
    privilege_in: PrivilegeUpdate,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(require_privilege(PrivilegeAction.ASSIGN_PRIVILEGE)),
):
    """
    Update an existing privilege. 
    Fields not sent in the payload will remain unchanged.
    """
    return await privileges.update_privilege(
        db,
        privilege_id=privilege_id,
        privilege_in=privilege_in
    )


@router.delete("/privileges/{privilege_id}")
async def delete_privilege(
    privilege_id: int,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(require_privilege(PrivilegeAction.ASSIGN_PRIVILEGE)),
):
    """Delete an existing privilege."""
    await privileges.delete(db, privilege_id=privilege_id)
    return {"status": "success", "message": "Privilege deleted"}


@router.post("/privileges/delegate", response_model=PrivilegeRead)
async def delegate_privilege(
    delegation_request: PrivilegeDelegate,
    db: AsyncSession = Depends(get_async_db),
    actor: User = Depends(get_current_actor),
):
    """
    Delegate a privilege to another user.
    
    The calling user must have a delegable privilege (is_delegable=True) that 
    covers the requested delegation. The delegated privilege must be equal to 
    or a subset of the delegator's privilege:
    
    - Same action
    - Same or more specific attribute_id
    - Same or more restrictive value_restriction
    - Same or more restrictive target_restriction
    
    If the requested privilege is broader than what the user can delegate,
    the request will be rejected with a 403 error.
    """
    return await privileges.delegate_privilege(
        db,
        delegator=actor,
        delegation_request=delegation_request,
    )