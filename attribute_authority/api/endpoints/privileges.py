"""Privilege endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import require_privilege
from ...db.session import get_async_db
from ...models.privilege import PrivilegeAction
from ...schemas.privilege import PrivilegeCreate, PrivilegeRead
from ...services import privilege as privileges

router = APIRouter()


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