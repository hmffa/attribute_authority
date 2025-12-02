from collections import defaultdict
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
import re


from ..crud.user import crud_user
from ..crud.user_attribute_value import crud_user_attribute_value
from ..crud.attribute_definition import crud_attribute_definition
from ..schemas.user_attribute_value import UserAttributeValueCreate

class UserNotFoundError(Exception):
    pass

class UserAttributeValueService:
    
    @staticmethod
    async def get_user_attributes(db: AsyncSession, sub: str, iss: str) -> Dict[str, List[Any]]:
        """
        Returns a dictionary of {attribute_name: [list of values]}
        """
        user = await crud_user.get_by_sub_and_iss(db, sub, iss)
        if not user:
            raise UserNotFoundError("User not found")

        # Fetch all values for user
        # CRUD must eager-load the 'attribute_definition' relationship
        user_values = await crud_user_attribute_value.get_by_user(db, user.id)

        # Transform: UserAttributeValue(id=1, value="blue") -> "favorite_color": ["blue"]
        result = defaultdict(list)
        for uv in user_values:
            # We access the name via the relationship
            attr_name = uv.attribute_definition.name
            result[attr_name].append({
                "id": uv.id,
                "value": uv.value,
                "source": uv.source
            })

        return result

    @staticmethod
    async def add_value(
        db: AsyncSession, 
        target_user_id: int, 
        attribute_name: str, 
        value: str,
        source: str = "manual"
    ):
        """
        Adds a value to a user, enforcing Schema rules (Multi-value & Regex).
        """
        # 1. Get the Attribute Definition (Schema)
        definition = await crud_attribute_definition.get_by_name(db, attribute_name)
        if not definition:
            raise HTTPException(status_code=404, detail=f"Attribute '{attribute_name}' is not defined in the schema.")

        if not definition.enabled:
            raise HTTPException(status_code=400, detail=f"Attribute '{attribute_name}' is currently disabled.")

        # 2. Check Regex Restriction
        if definition.value_restriction:
            if not re.match(definition.value_restriction, value):
                raise HTTPException(
                    status_code=400, 
                    detail=f"Value '{value}' does not match the required pattern for '{attribute_name}'."
                )

        # 3. Check Multi-Value Constraint
        if not definition.is_multivalue:
            # If not multi-value, check if user already has a value
            existing = await crud_user_attribute_value.get_by_user_and_attr_id(db, target_user_id, definition.id)
            if existing:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Attribute '{attribute_name}' is single-value and already has a value."
                )

        # 4. Create the Value
        return await crud_user_attribute_value.create(
            db, 
            user_id=target_user_id, 
            attribute_id=definition.id, 
            value=value,
            source=source
        )

    @staticmethod
    async def remove_value(db: AsyncSession, user_value_id: int):
        """
        Removes a specific value by its ID (UserAttributeValue.id)
        """
        await crud_user_attribute_value.delete(db, user_value_id)

user_attribute_value_service = UserAttributeValueService()