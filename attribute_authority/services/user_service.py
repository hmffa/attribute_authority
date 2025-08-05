from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..crud.user import crud_user
from ..schemas.user import User as UserSchema

class UserService:
    @staticmethod
    async def get_user(db: AsyncSession, sub: str, iss: str) -> UserSchema:
        """
        Get user information by subject identifier (sub) and issuer (iss).
        """
        user = await crud_user.get_by_sub_and_iss(db, sub, iss)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with sub {sub} not found",
            )
        return user

    @staticmethod
    async def get_userattributes(db: AsyncSession, claims: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate OIDC-compliant userattributes from user data
        """
        sub = claims.get("sub")
        iss = claims.get("iss")
        user = await UserService.get_user(db, sub, iss)

        return user.attributes if user.attributes else {}

user_service = UserService()