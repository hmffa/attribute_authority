from typing import Optional, List
import re
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_

from ..models.user import User
from ..models.privilege import Privilege, PrivilegeAction
from ..models.user_attribute_value import UserAttributeValue
from ..models.attribute import Attribute

class AuthorizationService:
    """
    Decides if 'actor' can perform 'action' on 'target_user' regarding 'attribute'.
    """

    @staticmethod
    async def has_privilege(
        db: AsyncSession,
        actor: User,
        action: PrivilegeAction,
        target_user: Optional[User] = None,
        attribute_id: Optional[int] = None,
        proposed_value: Optional[str] = None,
    ) -> bool:
        """
        1. Fetch all privileges granted to the actor for this specific action.
        2. Filter by Attribute ID (if the privilege is specific to an attribute).
        3. Check Value Restrictions (Regex).
        4. Check Target Restrictions (Does target_user match the JSON criteria?).
        """
        
        # 1. Fetch relevant privileges for this actor and action
        query = select(Privilege).where(
            Privilege.grantee_user_id == actor.id,
            Privilege.action == action
        )
        result = await db.execute(query)
        privileges = result.scalars().all()

        if not privileges:
            return False

        for priv in privileges:
            # 2. Attribute Restriction Check
            # If privilege has an attribute_id, it must match the request. 
            # If privilege attribute_id is None, it applies to ALL attributes (Superadmin style).
            if priv.attribute_id is not None:
                if attribute_id is None or priv.attribute_id != attribute_id:
                    continue

            # 3. Value Restriction Check (Regex)
            # If the action involves setting/adding a value, check against regex.
            if priv.value_restriction and proposed_value:
                if not AuthorizationService._matches_regex(priv.value_restriction, proposed_value):
                    continue

            # 4. Target Restriction Check
            # If the privilege has constraints on WHO can be targeted
            if priv.target_restriction and target_user:
                # We need to fetch the target user's current attributes to compare against restriction
                target_attributes = await AuthorizationService._get_user_attributes_dict(db, target_user.id)
                if not AuthorizationService._check_target_restriction(priv.target_restriction, target_attributes):
                    continue

            # If we survived all checks, access is granted
            return True

        return False

    @staticmethod
    def _matches_regex(pattern: str, text: str) -> bool:
        try:
            return re.search(pattern, text) is not None
        except re.error:
            return False

    @staticmethod
    async def _get_user_attributes_dict(db: AsyncSession, user_id: int) -> dict:
        """
        Helper to get a flat dictionary of target user's attributes for restriction checking.
        Returns: {'eduPersonAffiliation': ['staff', 'member'], 'orgUnit': ['IT']}
        """
        query = select(UserAttributeValue, Attribute.name).join(Attribute).where(
            UserAttributeValue.user_id == user_id
        )
        result = await db.execute(query)
        rows = result.all()
        
        attr_dict = {}
        for uav, attr_name in rows:
            if attr_name not in attr_dict:
                attr_dict[attr_name] = []
            attr_dict[attr_name].append(uav.value)
        return attr_dict

    @staticmethod
    def _check_target_restriction(restriction: List[dict], user_attrs: dict) -> bool:
        """
        Parses the JSON target restriction from design doc.
        Example JSON: [{"eduPersonAffiliation": "^staff$", "orgUnit": "^D3A$"}]
        Logic: OR between list items, AND within dict keys.
        """
        if not restriction:
            return True # No restriction means applies to everyone

        # Iterate through list (OR logic: if ANY rule block matches, return True)
        for rule_block in restriction:
            block_match = True
            # Iterate through keys in the block (AND logic: ALL keys must match)
            for key, regex in rule_block.items():
                user_values = user_attrs.get(key, [])
                # If user doesn't have the attribute, or none of the values match the regex
                if not any(AuthorizationService._matches_regex(regex, val) for val in user_values):
                    block_match = False
                    break
            
            if block_match:
                return True

        return False

authorization_service = AuthorizationService()