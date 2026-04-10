"""Privilege service - combines data access and business logic."""
import re
from datetime import datetime, timezone
from typing import List, Optional, Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..models.privilege import Privilege, PrivilegeAction
from ..models.user import User
from ..schemas.privilege import PrivilegeDelegate, PrivilegeUpdate
from . import user as users


# --- Data Access ---

async def get_by_id(db: AsyncSession, privilege_id: int) -> Optional[Privilege]:
    """Get a privilege by ID."""
    result = await db.execute(select(Privilege).where(Privilege.id == privilege_id))
    return result.scalars().first()


async def find_duplicate_privilege(
    db: AsyncSession,
    grantee_id: int,
    action: PrivilegeAction,
    attribute_id: Optional[int],
    value_res: Optional[str]
) -> Optional[Privilege]:
    """
    Finds if a privilege exists with the same Grantee, Action, Attribute, and Value.
    """
    query = select(Privilege).where(
        Privilege.grantee_user_id == grantee_id,
        Privilege.action == action,
        Privilege.attribute_id == attribute_id,
        Privilege.value_restriction == value_res
    )
    result = await db.execute(query)
    return result.scalars().first()


async def get_by_grantee(db: AsyncSession, user_id: int) -> List[Privilege]:
    """Get all privileges for a user."""
    result = await db.execute(
        select(Privilege).where(Privilege.grantee_user_id == user_id)
    )
    return result.scalars().all()


async def get_by_grantee_and_action(
    db: AsyncSession, user_id: int, action: PrivilegeAction
) -> List[Privilege]:
    """Get privileges for a specific user and action."""
    result = await db.execute(
        select(Privilege).where(
            Privilege.grantee_user_id == user_id,
            Privilege.action == action,
        )
    )
    return result.scalars().all()


async def create_privilege(db: AsyncSession, privilege: Privilege) -> Privilege:
    """Create a new privilege record."""
    now = datetime.now(timezone.utc).isoformat()
    privilege.created_at = now
    db.add(privilege)
    await db.commit()
    await db.refresh(privilege)
    return privilege


# --- Business Logic ---

async def update_privilege(
    db: AsyncSession, 
    privilege_id: int, 
    privilege_in: PrivilegeUpdate
) -> Privilege:
    """Update an existing privilege."""

    db_obj = await get_by_id(db, privilege_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Privilege not found")

    update_data = privilege_in.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if hasattr(db_obj, field):
            setattr(db_obj, field, value)

    # TODO: consider updating an 'updated_at' timestamp here
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def assign_privilege(
    db: AsyncSession,
    grantee_sub: str,
    grantee_iss: str,
    action: PrivilegeAction,
    attribute_id: Optional[int] = None,
    value_restriction: Optional[str] = None,
    target_restriction: Optional[list] = None,
    is_delegable: bool = False,
) -> Privilege:
    """Assign a privilege to a user (grantee) by sub/iss."""
    grantee = await users.get_by_sub_and_iss(db, grantee_sub, grantee_iss)
    if not grantee:
        raise HTTPException(status_code=404, detail="Grantee user not found")

    privilege = Privilege(
        grantee_user_id=grantee.id,
        action=action,
        attribute_id=attribute_id,
        value_restriction=value_restriction,
        target_restriction=target_restriction,
        is_delegable=is_delegable,
    )

    return await create_privilege(db, privilege)


async def assign_privilege_by_id(
    db: AsyncSession,
    grantee_user_id: int,
    action: PrivilegeAction,
    attribute_id: Optional[int] = None,
    value_restriction: Optional[str] = None,
    target_restriction: Optional[list] = None,
    is_delegable: bool = False,
) -> Privilege:
    """Assign a privilege to a user by user ID."""
    existing = await find_duplicate_privilege(
        db, 
        grantee_user_id, 
        action, 
        attribute_id, 
        value_restriction
    )
    if existing:
        raise HTTPException(
            status_code=409, 
            detail=(
                f"Privilege already exists (ID: {existing.id})."
            )
        )
    privilege = Privilege(
        grantee_user_id=grantee_user_id,
        action=action,
        attribute_id=attribute_id,
        value_restriction=value_restriction,
        target_restriction=target_restriction,
        is_delegable=is_delegable,
    )

    return await create_privilege(db, privilege)


# --- Delegation Logic ---

async def get_delegable_privileges(
    db: AsyncSession, 
    user_id: int, 
    action: PrivilegeAction
) -> List[Privilege]:
    """Get all delegable privileges for a user and action."""
    result = await db.execute(
        select(Privilege).where(
            Privilege.grantee_user_id == user_id,
            Privilege.action == action,
            Privilege.is_delegable == True,
        )
    )
    return result.scalars().all()


def _extract_literal_prefix(pattern: str) -> str:
    """
    Extract the literal (non-regex) prefix from a regex pattern.
    Stops at the first character that has special regex meaning.
    """
    special_chars = set(r'\.^$*+?{}[]|()')
    prefix = []
    i = 0
    while i < len(pattern):
        ch = pattern[i]
        if ch == '\\' and i + 1 < len(pattern):
            # Escaped character — the next char is literal
            prefix.append(pattern[i + 1])
            i += 2
        elif ch in special_chars:
            break
        else:
            prefix.append(ch)
            i += 1
    return ''.join(prefix)


def _is_value_restriction_subset(
    source_restriction: Optional[str],
    delegated_restriction: Optional[str]
) -> bool:
    """
    Check if the delegated value restriction is equal to or more restrictive
    than the source.

    Rules:
    - If source is None (no restriction), any delegated restriction is valid
    - If source has a restriction, delegated must match exactly or be more restrictive
    - If delegated is None but source has a restriction, it's NOT valid (would be broader)

    For regex patterns, checks that every string the delegated pattern can match
    is also matched by the source pattern. This is done by verifying that the
    delegated pattern's literal prefix is matched by the source pattern and
    that the variable (regex) suffix of the delegated pattern is equal to or
    more restrictive than the source's.
    """
    if source_restriction is None:
        return True

    if delegated_restriction is None:
        return False

    if delegated_restriction == source_restriction:
        return True

    # Use the source pattern as a regex and check if any string that the
    # delegated pattern can match would also be matched by the source pattern.
    #
    # Strategy: extract the literal prefix of the delegated pattern and check
    # if the source pattern can match strings starting with that prefix.
    # Then verify the regex tail is compatible.

    try:
        source_re = re.compile(source_restriction)
    except re.error:
        return False

    # Extract literal prefixes from both patterns
    source_prefix = _extract_literal_prefix(source_restriction)
    delegated_prefix = _extract_literal_prefix(delegated_restriction)

    # The delegated prefix must start with the source prefix (or extend it)
    # e.g., "urn:geant:kit:" starts with "urn:geant:" ✓
    if not delegated_prefix.startswith(source_prefix):
        return False

    # Check that the delegated literal prefix is matched by the source regex.
    # We need to test a representative string: the delegated prefix + a
    # sample suffix that satisfies the regex tail of the delegated pattern.
    delegated_tail = delegated_restriction[len(delegated_prefix):]
    source_tail = source_restriction[len(source_prefix):]

    # If the delegated prefix is longer (more specific) and the regex tails
    # are the same, the delegated pattern is definitely more restrictive.
    if delegated_tail == source_tail and len(delegated_prefix) >= len(source_prefix):
        # Verify by testing a sample match: use the delegated prefix + a
        # sample character that satisfies common tail patterns
        sample = delegated_prefix + "x"
        if source_re.fullmatch(sample):
            return True

    # General check: generate sample strings from the delegated pattern and
    # verify they all match the source pattern.
    # Use the delegated prefix plus various test suffixes.
    test_suffixes = ["x", "test", "abc123", "a:b:c", "hello-world_123"]
    try:
        delegated_re = re.compile(delegated_restriction)
    except re.error:
        return False

    for suffix in test_suffixes:
        test_string = delegated_prefix + suffix
        # Only test strings that the delegated pattern actually matches
        if delegated_re.fullmatch(test_string):
            if not source_re.fullmatch(test_string):
                return False

    # Also verify that at least one test string was matched by the delegated
    # pattern (to ensure we actually tested something meaningful)
    any_matched = any(
        delegated_re.fullmatch(delegated_prefix + s) for s in test_suffixes
    )
    if not any_matched:
        return False

    return True


def _is_target_restriction_subset(
    source_restriction: Optional[list],
    delegated_restriction: Optional[list]
) -> bool:
    """
    Check if delegated target restriction is equal to or more restrictive.
    
    Rules:
    - If source is None, any delegated restriction is valid
    - If delegated is None but source exists, it's broader (not allowed)
    - If both exist, delegated must contain all rules from source (AND logic)
    """
    if source_restriction is None:
        return True
    
    if delegated_restriction is None:
        return False
    
    # Delegated must include all source restrictions (can add more)
    # Each rule block in source must appear in delegated
    for source_rule in source_restriction:
        found = False
        for delegated_rule in delegated_restriction:
            # Check if delegated_rule contains all key-value pairs from source_rule
            if all(
                key in delegated_rule and delegated_rule[key] == value
                for key, value in source_rule.items()
            ):
                found = True
                break
        if not found:
            return False
    
    return True


def _can_delegate_privilege(
    source_privilege: Privilege,
    delegated: PrivilegeDelegate,
) -> tuple[bool, str]:
    """
    Validate if a privilege can be delegated based on the source privilege.
    
    Returns (is_valid, error_message).
    """
    # Check 1: Source must be delegable
    if not source_privilege.is_delegable:
        return False, "Source privilege is not delegable"
    
    # Check 2: Actions must match
    if source_privilege.action != delegated.action:
        return False, f"Cannot delegate action '{delegated.action.value}' from privilege with action '{source_privilege.action.value}'"
    
    # Check 3: Attribute scope - delegated must be same or more specific
    if source_privilege.attribute_id is not None:
        if delegated.attribute_id is None:
            return False, "Delegated privilege cannot have broader attribute scope than source"
        if delegated.attribute_id != source_privilege.attribute_id:
            return False, f"Attribute ID must match source privilege (expected {source_privilege.attribute_id})"
    
    # Check 4: Value restriction - delegated must be same or more restrictive
    if not _is_value_restriction_subset(
        source_privilege.value_restriction, 
        delegated.value_restriction
    ):
        return False, "Delegated value restriction must be equal to or more restrictive than source"
    
    # Check 5: Target restriction - delegated must be same or more restrictive
    if not _is_target_restriction_subset(
        source_privilege.target_restriction,
        delegated.target_restriction
    ):
        return False, "Delegated target restriction must be equal to or more restrictive than source"
    
    # Check 6: is_delegable - can only delegate as delegable if source is delegable
    # (already checked in Check 1, but we allow setting is_delegable=False on delegated)
    
    return True, ""


async def find_covering_privilege(
    db: AsyncSession,
    delegator: User,
    delegated: PrivilegeDelegate,
) -> Optional[Privilege]:
    """
    Find a delegable privilege that covers the requested delegation.
    Returns the covering privilege if found, None otherwise.
    """
    delegable_privileges = await get_delegable_privileges(
        db, delegator.id, delegated.action
    )
    
    for priv in delegable_privileges:
        is_valid, _ = _can_delegate_privilege(priv, delegated)
        if is_valid:
            return priv
    
    return None


async def delegate_privilege(
    db: AsyncSession,
    delegator: User,
    delegation_request: PrivilegeDelegate,
) -> Privilege:
    """
    Delegate a privilege from delegator to grantee.
    
    Validates that:
    1. Delegator has a delegable privilege that covers the request
    2. The delegated privilege is equal to or a subset of the source
    """
    # Find a covering privilege
    covering_privilege = await find_covering_privilege(
        db, delegator, delegation_request
    )
    
    if not covering_privilege:
        # Get more specific error message
        delegable_privileges = await get_delegable_privileges(
            db, delegator.id, delegation_request.action
        )
        
        if not delegable_privileges:
            raise HTTPException(
                status_code=403,
                detail=f"You do not have any delegable privileges for action '{delegation_request.action.value}'"
            )
        
        # Check each one for specific error
        errors = []
        for priv in delegable_privileges:
            is_valid, error = _can_delegate_privilege(priv, delegation_request)
            if not is_valid:
                errors.append(f"Privilege {priv.id}: {error}")
        
        raise HTTPException(
            status_code=403,
            detail=f"Cannot delegate this privilege. The requested privilege exceeds your delegable privileges. Details: {'; '.join(errors)}"
        )
    
    # Check for duplicate
    existing = await find_duplicate_privilege(
        db,
        delegation_request.grantee_user_id,
        delegation_request.action,
        delegation_request.attribute_id,
        delegation_request.value_restriction,
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Privilege already exists (ID: {existing.id})."
        )
    
    # Create the delegated privilege
    privilege = Privilege(
        grantee_user_id=delegation_request.grantee_user_id,
        action=delegation_request.action,
        attribute_id=delegation_request.attribute_id,
        value_restriction=delegation_request.value_restriction,
        target_restriction=delegation_request.target_restriction,
        is_delegable=delegation_request.is_delegable,
    )
    
    return await create_privilege(db, privilege)