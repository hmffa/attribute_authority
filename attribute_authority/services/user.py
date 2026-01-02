"""User service - combines data access and business logic."""
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..models.user import User
from ..models.privilege import PrivilegeAction
from ..schemas.user import UserCreate, UserUpdate, UserWithAttributes
from . import authorization


# --- Data Access ---

async def get_all(db: AsyncSession) -> list[User]:
    """Get all users."""
    result = await db.execute(select(User))
    return result.scalars().all()


async def get_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """Get a user by ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalars().first()


async def get_by_sub_and_iss(db: AsyncSession, sub: str, iss: str) -> Optional[User]:
    """Get a user by subject identifier (sub) and issuer (iss)."""
    result = await db.execute(
        select(User).where(User.sub == sub, User.iss == iss)
    )
    return result.scalars().first()


async def list_paginated(
    db: AsyncSession, offset: int = 0, limit: int = 100
) -> List[User]:
    """List users with pagination."""
    result = await db.execute(select(User).offset(offset).limit(limit))
    return result.scalars().all()


async def count(db: AsyncSession) -> int:
    """Count total users."""
    result = await db.execute(select(func.count(User.id)))
    return result.scalar_one()


async def create(db: AsyncSession, user_in: UserCreate) -> User:
    """Create a new user."""
    now = datetime.now(timezone.utc).isoformat()
    user = User(
        sub=user_in.sub,
        iss=user_in.iss,
        created_at=now,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update(db: AsyncSession, user: User, user_in: UserUpdate) -> User:
    """Update a user."""
    update_data = user_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(user, field):
            setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return user


# --- Business Logic ---

async def get_or_create(db: AsyncSession, sub: str, iss: str) -> User:
    """Get existing user or create new one."""
    user = await get_by_sub_and_iss(db, sub, iss)
    if not user:
        user = await create(db, UserCreate(sub=sub, iss=iss))
    return user


async def list_users_paginated(
    db: AsyncSession, page: int, per_page: int
) -> Dict[str, Any]:
    """Get paginated user list with metadata."""
    offset = (page - 1) * per_page
    users = await list_paginated(db, offset=offset, limit=per_page)
    total = await count(db)

    return {
        "items": users,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


async def get_all_users_with_visible_attributes(
    db: AsyncSession, actor: User
) -> List[UserWithAttributes]:
    """
    Fetch all users and filter attributes based on actor's READ privileges.
    Users with no visible attributes are excluded.
    """
    users = await get_all(db)
    results = []

    for target_user in users:
        visible_attributes = defaultdict(list)

        for user_attr in target_user.attribute_values:
            is_allowed = await authorization.has_privilege(
                db,
                actor=actor,
                action=PrivilegeAction.READ_VALUE,
                target_user=target_user,
                attribute_id=user_attr.attribute_id,
                value=user_attr.value,
            )

            if is_allowed:
                attr_name = user_attr.attribute_definition.name
                visible_attributes[attr_name].append(user_attr.value)

        if visible_attributes:
            results.append(
                UserWithAttributes(
                    id=target_user.id,
                    sub=target_user.sub,
                    iss=target_user.iss,
                    name=target_user.name,
                    email=target_user.email,
                    created_at=target_user.created_at,
                    attributes=visible_attributes,
                )
            )

    return results