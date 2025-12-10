from typing import List, Optional
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import datetime

from ..models.user import User
from ..schemas.user import UserCreate, UserUpdate

class CRUDUser:
    @staticmethod
    async def get_all(db: AsyncSession) -> list[User]:
        """
        Get all users
        """
        query = select(User)
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def list(db: AsyncSession, offset: int = 0, limit: int = 100) -> List[User]:
        query = select(User).offset(offset).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def count(db: AsyncSession) -> int:
        query = select(func.count(User.id))
        result = await db.execute(query)
        return result.scalar_one()
    
    @staticmethod
    async def get_by_sub_and_iss(db: AsyncSession, sub: str, iss: str) -> Optional[User]:
        """
        Get a user by subject identifier (sub) and issuer (iss)
        """
        query = select(User).where(User.sub == sub, User.iss == iss)
        result = await db.execute(query)
        return result.scalars().first()


    @staticmethod
    async def create(db: AsyncSession, obj_in: UserCreate) -> User:
        """
        Create a new user
        """
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        db_obj = User(
            sub=obj_in.sub,
            iss=obj_in.iss,
            created_at=now,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    @staticmethod
    async def update(db: AsyncSession, db_obj: User, obj_in: UserUpdate) -> User:
        """
        Update a user
        """
        update_data = obj_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
            
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

crud_user = CRUDUser()