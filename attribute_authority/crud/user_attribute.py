from fastapi import HTTPException
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
import datetime

from ..models.user_attribute import UserAttribute
from ..schemas.user_attribute import UserAttributeCreate, UserAttributeUpdate

class CRUDUserAttribute:
    @staticmethod
    async def get_by_user_id(db: AsyncSession, user_id: int) -> Optional[UserAttribute]:
        """
        Get user attributes by user ID.
        """
        query = select(UserAttribute).where(UserAttribute.user_id == user_id)
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_by_user_id_and_key(db: AsyncSession, user_id: int, key: str) -> Optional[UserAttribute]:
        """
        Get a user attribute by user ID and key.
        """
        query = select(UserAttribute).where(UserAttribute.user_id == user_id, UserAttribute.key == key)
        result = await db.execute(query)
        return result.scalars().all()
    

    @staticmethod
    async def create(db: AsyncSession, user_id: int, key: str, value: str) -> UserAttribute:
        """
        Create a new user attribute.
        """
        created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        db_obj = UserAttribute(user_id=user_id, key=key, value=value, created_at=created_at)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    @staticmethod
    async def update(db: AsyncSession, user_id: int, key: str, value: str) -> UserAttribute:
        """
        Update an existing user attribute.
        """
        query = select(UserAttribute).where(UserAttribute.user_id == user_id, UserAttribute.key == key)
        result = await db.execute(query)
        db_obj = result.scalar_one_or_none()
        if not db_obj:
            raise HTTPException(status_code=404, detail="UserAttribute not found")
        db_obj.value = value
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    @staticmethod
    async def delete(
        db: AsyncSession,
        *,
        attr_id: Optional[int] = None,
        user_id: Optional[int] = None,
        key: Optional[str] = None,
        value: Optional[str] = None,
    ) -> None:
        """
        Delete a user attribute.

        Provide attr_id or user_id+key+value. If both are provided, attr_id is used.
        """
        has_id = attr_id is not None
        has_triplet = all(v is not None for v in (user_id, key, value))

        if not (has_id or has_triplet):
            raise HTTPException(status_code=400, detail="Provide attr_id or user_id+key+value.")

        if has_id:
            query = select(UserAttribute).where(UserAttribute.id == attr_id)
        else:
            query = select(UserAttribute).where(
                UserAttribute.user_id == user_id,
                UserAttribute.key == key,
                UserAttribute.value == value,
            )

        result = await db.execute(query)
        db_obj = result.scalar_one_or_none()
        if not db_obj:
            raise HTTPException(status_code=404, detail="UserAttribute not found")
        await db.delete(db_obj)
        await db.commit()

crud_user_attribute = CRUDUserAttribute()