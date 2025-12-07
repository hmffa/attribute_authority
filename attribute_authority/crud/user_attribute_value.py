from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..models.user_attribute_value import UserAttributeValue
from ..models.attribute import Attribute

class CRUDUserAttributeValue:
    
    @staticmethod
    async def get_by_user(db: AsyncSession, user_id: int) -> List[UserAttributeValue]:
        # Fetch values and join with definition to get the name (key)
        query = select(UserAttributeValue).where(UserAttributeValue.user_id == user_id)
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def create(
        db: AsyncSession, 
        user_id: int, 
        attribute_id: int, 
        value: str, 
        source: str = "manual"
    ) -> UserAttributeValue:
        db_obj = UserAttributeValue(
            user_id=user_id,
            attribute_id=attribute_id,
            value=value,
            source=source,
            created_at="now", # TODO: Use real timestamp
            updated_at="now"
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    @staticmethod
    async def delete(db: AsyncSession, id: int) -> None:
        query = select(UserAttributeValue).where(UserAttributeValue.id == id)
        result = await db.execute(query)
        db_obj = result.scalar_one_or_none()
        if db_obj:
            await db.delete(db_obj)
            await db.commit()

crud_user_attribute_value = CRUDUserAttributeValue()