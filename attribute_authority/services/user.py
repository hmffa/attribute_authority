from typing import Any, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession

from ..crud.user import crud_user

class UserService:
    @staticmethod
    async def list_users(db: AsyncSession, offset: int = 0, limit: int = 50) -> Dict[str, Any]:
        """
        List users with pagination. Serialize in the API layer.
        """
        users = await crud_user.list(db, offset=offset, limit=limit)  # add in CRUD if missing
        total = await crud_user.count(db)  # add in CRUD if missing
        return {"items": users, "total": total, "offset": offset, "limit": limit}

user_service = UserService()