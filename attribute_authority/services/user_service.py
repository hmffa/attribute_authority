from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from collections import defaultdict

from ..crud.user import crud_user
from ..crud.user_attribute import crud_user_attribute
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
        attributes = await crud_user_attribute.get_by_user_id(db, user.id)
        result = defaultdict(list)
        for attr in attributes:
            result[attr.key].append(attr.value)

        return result
    
    @staticmethod
    async def get_userattribute(db: AsyncSession, claims: Dict[str, Any], key: str) -> Dict[str, Any]:
        """
        Get a specific user attribute by key.
        """
        sub = claims.get("sub")
        iss = claims.get("iss")
        user = await UserService.get_user(db, sub, iss)
        attribute = await crud_user_attribute.get_by_user_id_and_key(db, user.id, key)
        result = defaultdict(list)
        if attribute:
            for att in attribute:
                result[att.key].append(att.value)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User attribute with key {key} not found for user {sub}",
            )
        return result

    @staticmethod
    async def get_userattributes_with_ids(db: AsyncSession, claims: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate OIDC-compliant userattributes from user data, including attribute IDs.
        """
        sub = claims.get("sub")
        iss = claims.get("iss")
        user = await UserService.get_user(db, sub, iss)
        attributes = await crud_user_attribute.get_by_user_id(db, user.id)
        result = defaultdict(list)
        for attr in attributes:
            result[attr.key].append({"id": attr.id, "value": attr.value})

        return result

user_service = UserService()