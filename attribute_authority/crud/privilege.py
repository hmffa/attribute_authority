from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from ..models.privilege import Privilege

class CRUDPrivilege:
    @staticmethod
    async def create(db: AsyncSession, obj_in) -> Privilege:
        db.add(obj_in)
        await db.commit()
        await db.refresh(obj_in)
        return obj_in

    @staticmethod
    async def get_by_grantee(db: AsyncSession, user_id: int) -> List[Privilege]:
        query = select(Privilege).where(Privilege.grantee_user_id == user_id)
        result = await db.execute(query)
        return result.scalars().all()

crud_privilege = CRUDPrivilege()