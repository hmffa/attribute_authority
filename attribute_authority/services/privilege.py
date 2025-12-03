from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.privilege import PrivilegeAction, Privilege
from ..schemas.privilege import PrivilegeCreate
from ..crud.user import crud_user
from ..crud.privilege import crud_privilege

class PrivilegeService:

    @staticmethod
    async def assign_privilege(
        db: AsyncSession, 
        grantee_sub: str, 
        grantee_iss: str,
        action: PrivilegeAction,
        attribute_id: int | None = None,
        value_restriction: str | None = None,
        target_restriction: list | None = None,
        is_delegable: bool = False
    ) -> Privilege:
        """
        Assigns a privilege to a user (grantee).
        """
        grantee = await crud_user.get_by_sub_and_iss(db, grantee_sub, grantee_iss)
        if not grantee:
            raise HTTPException(status_code=404, detail="Grantee user not found")
        
        db_obj = Privilege(
            grantee_user_id=grantee.id,
            action=action,
            attribute_id=attribute_id,
            value_restriction=value_restriction,
            target_restriction=target_restriction,
            is_delegable=is_delegable
        )
        
        return await crud_privilege.create(db, db_obj)

privilege_service = PrivilegeService()