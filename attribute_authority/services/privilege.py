from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException

from ..models.privilege import Privilege, PrivilegeAction
from ..schemas.privilege import PrivilegeCreate
from ..crud.user import crud_user

class PrivilegeService:

    @staticmethod
    async def assign_privilege(
        db: AsyncSession, 
        grantee_sub: str, 
        grantee_iss: str,
        privilege_data: PrivilegeCreate
    ):
        """
        Assigns a privilege to a user (grantee).
        """
        # 1. Resolve Grantee
        grantee = await crud_user.get_by_sub_and_iss(db, grantee_sub, grantee_iss)
        if not grantee:
            raise HTTPException(status_code=404, detail="Grantee user not found")

        # 2. Create Privilege Tuple
        # Note: You might want to add logic here to check if the *Caller* has 'ASSIGN_PRIVILEGE' rights
        # via the AuthorizationService before proceeding.

        db_obj = Privilege(
            grantee_user_id=grantee.id,
            action=privilege_data.action,
            attribute_id=privilege_data.attribute_id,
            value_restriction=privilege_data.value_restriction,
            target_restriction=privilege_data.target_restriction,
            is_delegable=privilege_data.is_delegable,
            created_at=privilege_data.created_at
        )
        
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    @staticmethod
    async def get_my_privileges(db: AsyncSession, user_id: int) -> List[Privilege]:
        result = await db.execute(
            select(Privilege).where(Privilege.grantee_user_id == user_id)
        )
        return result.scalars().all()

privilege_service = PrivilegeService()