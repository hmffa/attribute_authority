"""Authorization service - handles privilege checking logic."""
import re
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.user import User
from ..models.privilege import PrivilegeAction
from . import privilege as privileges
from . import user_attribute_value as user_attributes


async def has_privilege(
    db: AsyncSession,
    actor: User,
    action: PrivilegeAction,
    target_user: Optional[User] = None,
    attribute_id: Optional[int] = None,
    value: Optional[str] = None,
) -> bool:
    """Check if actor has the specified privilege."""
    actor_privileges = await privileges.get_by_grantee_and_action(
        db, user_id=actor.id, action=action
    )

    if not actor_privileges:
        return False

    for priv in actor_privileges:
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
            target_attrs = await _get_user_attrs(db, target_user.id)
            if not _check_target_restriction(priv.target_restriction, target_attrs):
                continue

        return True  # Access granted

    return False


async def _get_user_attrs(db: AsyncSession, user_id: int) -> Dict[str, List[str]]:
    """Get target user attributes for restriction checking."""
    user_values = await user_attributes.get_by_user(db, user_id)

    attr_dict: Dict[str, List[str]] = {}
    for uv in user_values:
        attr_name = uv.attribute_definition.name
        if attr_name not in attr_dict:
            attr_dict[attr_name] = []
        attr_dict[attr_name].append(uv.value)

    return attr_dict


def _check_target_restriction(
    restriction: List[dict], user_attrs: Dict[str, List[str]]
) -> bool:
    """
    Evaluate target restriction JSON logic.
    Schema: List[Dict[str, regex]] -> OR(AND(key match regex))
    """
    if not restriction:
        return True

    # OR Logic: Returns True if ANY block matches
    for rule_block in restriction:
        block_match = True

        # AND Logic: Returns True only if ALL keys in block match
        for key, regex in rule_block.items():
            user_values = user_attrs.get(key, [""])
            values_to_check = user_values if user_values else [""]

            # if not user_values or not any(re.search(regex, v) for v in user_values):
            
            # NOTE: Strict deny is avoided; missing attributes are treated as empty strings
            if not any(re.search(regex, v) for v in values_to_check):
                block_match = False
                break

        if block_match:
            return True

    return False