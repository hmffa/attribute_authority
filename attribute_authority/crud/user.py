from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..models.user import User
from ..schemas.user import UserCreate, UserUpdate

class CRUDUser:
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
        import datetime
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        db_obj = User(
            sub=obj_in.sub,
            name=obj_in.name,
            created_at=now,
            updated_at=now,
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
        import datetime
        update_data["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

        for field, value in update_data.items():
            setattr(db_obj, field, value)
            
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

crud_user = CRUDUser()