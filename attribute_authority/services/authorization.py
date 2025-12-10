# services/authorization.py
import re
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.user import User
from ..models.privilege import PrivilegeAction
from ..crud.privilege import crud_privilege
from ..crud.user_attribute_value import crud_user_attribute_value

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
        # 1. Fetch privileges
        privileges = await crud_privilege.get_by_grantee_and_action(
            db, 
            user_id=actor.id, 
            action=action
        )

        if not privileges:
            return False

        # 2. Iterate and check restrictions (Business Logic)
        for priv in privileges:
            # Check 1: Attribute Scope
            if priv.attribute_id is not None:
                if attribute_id is not None and priv.attribute_id != attribute_id:
                    continue
            
            # Check 2: Value Restriction (Regex)
            if priv.value_restriction and value:
                if not re.search(priv.value_restriction, value):
                    continue

            # Check 3: Target Restriction
            if priv.target_restriction and target_user:
                target_attrs = await AuthorizationService._get_user_attrs(db, target_user.id)
                if not AuthorizationService._check_target_restriction(priv.target_restriction, target_attrs):
                    continue

            return True # Access granted
        
        return False

    @staticmethod
    async def _get_user_attrs(db: AsyncSession, user_id: int) -> Dict[str, List[str]]:
        """
        Helper to get target user attributes in a format suitable for checking restrictions.
        Returns: {'eduPersonAffiliation': ['staff', 'member']}
        """
        # Use CRUD to fetch data
        user_values = await crud_user_attribute_value.get_by_user(db, user_id)
        
        # Transform data for logic check
        attr_dict = {}
        for uv in user_values:
            # Note: This assumes uv.attribute_definition is eager loaded in CRUD
            # or available via lazy load if session is active
            attr_name = uv.attribute_definition.name
            if attr_name not in attr_dict:
                attr_dict[attr_name] = []
            attr_dict[attr_name].append(uv.value)
            
        return attr_dict

    @staticmethod
    def _check_target_restriction(restriction: List[dict], user_attrs: Dict[str, List[str]]) -> bool:
        """
        Evaluates the target restriction JSON logic.
        Restriction schema: List[Dict[str, regex]] -> OR(AND(key match regex))
        """
        if not restriction:
            return True

        # OR Logic: Returns True if ANY block matches
        for rule_block in restriction:
            block_match = True
            
            # AND Logic: Returns True only if ALL keys in block match
            for key, regex in rule_block.items():
                user_values = user_attrs.get(key, [])
                
                # If user has no values for this key, or none match regex -> Fail
                if not user_values or not any(re.search(regex, v) for v in user_values):
                    block_match = False
                    break
            
            if block_match:
                return True

        return False

authorization_service = AuthorizationService()