"""Privilege service - combines data access and business logic."""
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..models.privilege import Privilege, PrivilegeAction
from . import user as users


# --- Data Access ---

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
    privilege = Privilege(
        grantee_user_id=grantee_user_id,
        action=action,
        attribute_id=attribute_id,
        value_restriction=value_restriction,
        target_restriction=target_restriction,
        is_delegable=is_delegable,
    )

    return await create_privilege(db, privilege)