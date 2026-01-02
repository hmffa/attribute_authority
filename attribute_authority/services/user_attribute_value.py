"""User attribute value service - combines data access and business logic."""
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..models.user_attribute_value import UserAttributeValue
from ..models.user import User
from ..models.privilege import PrivilegeAction
from . import user as users
from . import attribute_definition as attributes
from . import authorization


class UserNotFoundError(Exception):
    pass


# --- Data Access ---

async def get_by_user(db: AsyncSession, user_id: int) -> List[UserAttributeValue]:
    """Get all attribute values for a user."""
    result = await db.execute(
        select(UserAttributeValue).where(UserAttributeValue.user_id == user_id)
    )
    return result.scalars().all()


async def get_by_user_and_attr_id(
    db: AsyncSession, user_id: int, attribute_id: int
) -> List[UserAttributeValue]:
    """Get attribute values for a specific user and attribute."""
    result = await db.execute(
        select(UserAttributeValue).where(
            UserAttributeValue.user_id == user_id,
            UserAttributeValue.attribute_id == attribute_id,
        )
    )
    return result.scalars().all()


async def get_all(db: AsyncSession) -> List[UserAttributeValue]:
    """Get all user attribute values."""
    result = await db.execute(select(UserAttributeValue))
    return result.scalars().all()


async def create_value(
    db: AsyncSession, user_id: int, attribute_id: int, value: str
) -> UserAttributeValue:
    """Create a new user attribute value."""
    now = datetime.now(timezone.utc).isoformat()
    db_obj = UserAttributeValue(
        user_id=user_id,
        attribute_id=attribute_id,
        value=value,
        created_at=now,
        updated_at=now,
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def delete_value(db: AsyncSession, value_id: int) -> None:
    """Delete a user attribute value by ID."""
    result = await db.execute(
        select(UserAttributeValue).where(UserAttributeValue.id == value_id)
    )
    db_obj = result.scalar_one_or_none()
    if db_obj:
        await db.delete(db_obj)
        await db.commit()


# --- Business Logic ---

async def get_user_attributes(
    db: AsyncSession, sub: str, iss: str
) -> Dict[str, List[Any]]:
    """Get user attributes as {attribute_name: [values]}."""
    user = await users.get_by_sub_and_iss(db, sub, iss)
    if not user:
        raise UserNotFoundError("User not found")

    user_values = await get_by_user(db, user.id)

    result = defaultdict(list)
    for uv in user_values:
        attr_name = uv.attribute_definition.name
        result[attr_name].append({"id": uv.id, "value": uv.value})

    return result


async def get_all_user_attributes(
    db: AsyncSession,
) -> Dict[int, Dict[str, List[Any]]]:
    """Get all user attributes grouped by user ID."""
    all_values = await get_all(db)

    result = defaultdict(lambda: defaultdict(list))
    for uv in all_values:
        user_id = uv.user_id
        attr_name = uv.attribute_definition.name
        result[user_id][attr_name].append({"id": uv.id, "value": uv.value})

    return result


async def add_value(
    db: AsyncSession,
    target_user_id: int,
    attribute_name: str,
    value: str,
    actor: User,
) -> UserAttributeValue:
    """Add an attribute value with authorization and validation."""
    target_user = await users.get_by_id(db, target_user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")

    attribute = await attributes.get_or_404(db, attribute_name)

    is_allowed = await authorization.has_privilege(
        db,
        actor=actor,
        action=PrivilegeAction.ADD_VALUE,
        target_user=target_user,
        attribute_id=attribute.id,
        value=value,
    )
    if not is_allowed:
        raise HTTPException(
            status_code=403, detail="Not authorized to add this attribute value."
        )

    # Check Multi-Value Constraint
    if not attribute.is_multivalue:
        existing = await get_by_user_and_attr_id(db, target_user_id, attribute.id)
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Attribute '{attribute_name}' is single-value and cannot add more values.",
            )

    return await create_value(
        db, user_id=target_user_id, attribute_id=attribute.id, value=value
    )


async def remove_value(db: AsyncSession, value_id: int) -> None:
    """Remove a specific attribute value by ID."""
    await delete_value(db, value_id)