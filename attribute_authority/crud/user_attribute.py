from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..models.user_attribute import UserAttribute
from ..schemas.user_attribute import UserAttributeCreate

class CRUDUserAttribute:
    @staticmethod
    async def get_by_user_id(db: AsyncSession, user_id: str) -> Optional[UserAttribute]:
        """
        Get user attributes by user ID.
        """
        query = select(UserAttribute).where(UserAttribute.user_id == user_id)
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_by_user_id_and_key(db: AsyncSession, user_id: str, key: str) -> Optional[UserAttribute]:
        """
        Get a user attribute by user ID and key.
        """
        query = select(UserAttribute).where(UserAttribute.user_id == user_id, UserAttribute.key == key)
        result = await db.execute(query)
        return result.scalars().all()

crud_user_attribute = CRUDUserAttribute()