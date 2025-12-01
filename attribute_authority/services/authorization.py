import re
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..models.user import User
from ..models.privilege import Privilege, PrivilegeAction
from ..models.user_attribute_value import UserAttributeValue
from ..models.attribute import Attribute

class AuthorizationService:
    @staticmethod
    async def has_privilege(
        db: AsyncSession,
        actor: User,
        action: PrivilegeAction,
        target_user: Optional[User] = None,
        attribute_id: Optional[int] = None,
        value: Optional[str] = None,
    ) -> bool:
        # 1. Fetch privileges for this actor & action
        query = select(Privilege).where(
            Privilege.grantee_user_id == actor.id,
            Privilege.action == action
        )
        result = await db.execute(query)
        privileges = result.scalars().all()

        for priv in privileges:
            # Check 1: Attribute Scope (If privilege is bound to specific Attribute ID)
            if priv.attribute_id is not None:
                if attribute_id is not None and priv.attribute_id != attribute_id:
                    continue
            
            # Check 2: Value Restriction (Regex)
            if priv.value_restriction and value:
                if not re.search(priv.value_restriction, value):
                    continue

            # Check 3: Target Restriction (JSON Logic)
            if priv.target_restriction and target_user:
                # Fetch target user's attributes to compare against restriction
                target_attrs = await AuthorizationService._get_user_attrs(db, target_user.id)
                if not AuthorizationService._check_target_restriction(priv.target_restriction, target_attrs):
                    continue

            return True # All checks passed
        
        return False

    @staticmethod
    async def _get_user_attrs(db: AsyncSession, user_id: int) -> dict:
        """Helper to get target user attributes as simple dict for matching"""
        query = select(UserAttributeValue).where(UserAttributeValue.user_id == user_id)
        result = await db.execute(query)
        values = result.scalars().all()
        # In real impl, you'd join with Attribute to get names. 
        # For now assuming we match on Attribute ID or similar.
        return {} 

    @staticmethod
    def _check_target_restriction(restriction: List[dict], user_attrs: dict) -> bool:
        # Implementation of your OR(AND(...)) logic
        return True # Placeholder: Implement strict logic here

authorization_service = AuthorizationService()