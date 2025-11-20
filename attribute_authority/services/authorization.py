from __future__ import annotations

from typing import Optional, Set, List
import re

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.user import User
from ..models.attribute_privilege_rule import PrivilegeAction, TargetScope, AttributePrivilegeRule
from ..crud.admin_role import crud_admin_role
from ..crud.attribute_privilege_rule import crud_attribute_privilege_rule


class AuthorizationService:
    """
    Business logic for Attribute Authority authorization:

    - Checking which admin roles a user has
    - Checking if an actor can CRUD a (key, value) attribute on a target user
    """

    @staticmethod
    async def get_user_admin_role_names(db: AsyncSession, user: User) -> List[str]:
        """
        Return a list of AA internal admin role names assigned to this user.
        Example:
           ["GLOBAL_ATTR_ADMIN", "ENTITLEMENT_ADMIN"]
        """
        roles = await crud_admin_role.get_roles_for_user(db, user)
        return [role.name for role in roles]

    @staticmethod
    async def has_attribute_privilege(
        db: AsyncSession,
        actor: User,
        action: PrivilegeAction,
        attribute_key: str,
        attribute_value: Optional[str],
        target_user: User,
    ) -> bool:
        """
        The *core* authorization decision for the Attribute Authority.

        Checks:

        1) Does the actor have required internal AA admin roles?
        2) Does the rule for this action match:
           - attribute key regex?
           - attribute value regex? (if present)
           - target scope (self/any)?
        """
        # 1) Get actor admin roles
        actor_roles: Set[str] = set(
            await AuthorizationService.get_user_admin_role_names(db, actor)
        )

        if not actor_roles:
            # No admin roles → no privileges unless you give everyone a default role
            return False

        # 2) Load rules for this CRUD action
        rules: List[AttributePrivilegeRule] = (
            await crud_attribute_privilege_rule.get_by_action(db, action)
        )

        # 3) Evaluate rules
        for rule in rules:
            # Actor must have required role
            if rule.required_role.name not in actor_roles:
                continue

            # Attribute key must match regex
            if not AuthorizationService._matches_regex(
                rule.attribute_key_regex, attribute_key
            ):
                continue

            # If value restriction exists & value is provided, match regex
            if rule.attribute_value_regex and attribute_value is not None:
                if not AuthorizationService._matches_regex(
                    rule.attribute_value_regex,
                    attribute_value,
                ):
                    continue

            # Target scope check
            if not AuthorizationService._target_scope_satisfied(
                rule.target_scope,
                actor,
                target_user,
            ):
                continue

            # This rule grants permission
            return True

        # If no rule matched: deny
        return False

    # ---------------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------------

    @staticmethod
    def _matches_regex(pattern: str, text: str) -> bool:
        """
        Wrapper to safely match regex patterns.
        """
        try:
            return re.fullmatch(pattern, text) is not None
        except re.error:
            # If pattern is invalid → deny for safety
            return False

    @staticmethod
    def _target_scope_satisfied(
        scope: TargetScope,
        actor: User,
        target_user: User,
    ) -> bool:
        """
        Evaluate target scope:
          - self → only operate on own attributes
          - any → operate on any user
        """
        if scope == TargetScope.self:
            return actor.id == target_user.id

        if scope == TargetScope.any:
            return True

        # Extend here later for same_vo / same_group etc.
        return False


authorization_service = AuthorizationService()
