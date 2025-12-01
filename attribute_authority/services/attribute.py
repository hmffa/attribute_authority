# services/user_service.py
from collections import defaultdict
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List

from ..crud.user import crud_user
from ..crud.user_attribute_value import crud_attribute

class UserNotFoundError(Exception):
    pass

class AttributeService:
    @staticmethod
    async def get_attributes_with_user_id(db: AsyncSession, claims: Dict[str, Any]) -> Dict[str, Any]:
        sub = claims.get("sub")
        iss = claims.get("iss")

        user = await crud_user.get_by_sub_and_iss(db, sub, iss)
        attributes = await crud_attribute.get_by_user_id(db, user.id)

        result: Dict[str, list[dict]] = defaultdict(list)
        for attr in attributes:
            result[attr.key].append({"id": attr.id, "value": attr.value})

        return result
    
    @staticmethod
    async def get_attribute(db: AsyncSession, claims: Dict[str, Any], key: str) -> Dict[str, Any]:
        """
        Get a specific user attribute by key.
        """
        sub = claims.get("sub")
        iss = claims.get("iss")
        user = await crud_user.get_by_sub_and_iss(db, sub, iss)
        attribute = await crud_attribute.get_by_user_id_and_key(db, user.id, key)
        result = defaultdict(list)
        if attribute:
            for att in attribute:
                result[att.key].append(att.value)
        else:
            raise UserNotFoundError(f"Attribute with key '{key}' not found for user.")
        return result
    

    @staticmethod
    async def attribute_key_counts(db: AsyncSession) -> List[Dict[str, Any]]:
        """
        Return counts per attribute key (admin).
        """
        return await crud_attribute.grouped_counts(db)  # add in CRUD if missing


attribute_service = AttributeService()