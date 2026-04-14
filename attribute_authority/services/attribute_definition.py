"""Attribute definition service - combines data access and business logic."""
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..models.attribute import Attribute
from ..schemas.attribute import AttributeCreate, AttributeUpdate


# --- Data Access ---

async def get_by_id(db: AsyncSession, attribute_id: int) -> Optional[Attribute]:
    """Get attribute definition by ID."""
    result = await db.execute(select(Attribute).where(Attribute.id == attribute_id))
    return result.scalars().first()


async def get_by_name(db: AsyncSession, name: str) -> Optional[Attribute]:
    """Get attribute definition by name."""
    result = await db.execute(select(Attribute).where(Attribute.name == name))
    return result.scalars().first()


async def get_all(db: AsyncSession) -> List[Attribute]:
    """Get all attribute definitions."""
    result = await db.execute(select(Attribute).order_by(Attribute.name.asc()))
    return result.scalars().all()


async def create_attribute(db: AsyncSession, attr_in: AttributeCreate) -> Attribute:
    """Create a new attribute definition (internal)."""
    attribute = Attribute(
        name=attr_in.name,
        is_multivalue=attr_in.is_multivalue,
        value_restriction=attr_in.value_restriction,
        description=attr_in.description,
        enabled=attr_in.enabled,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(attribute)
    await db.commit()
    await db.refresh(attribute)
    return attribute


async def delete_attribute(db: AsyncSession, attribute: Attribute) -> None:
    """Delete an attribute definition."""
    await db.delete(attribute)
    await db.commit()


# --- Business Logic ---

async def create(db: AsyncSession, attr_in: AttributeCreate) -> Attribute:
    """Create a new attribute definition with validation."""
    exists = await get_by_name(db, attr_in.name)
    if exists:
        raise HTTPException(status_code=400, detail="Attribute already exists")
    return await create_attribute(db, attr_in)


async def get_or_404(db: AsyncSession, name: str) -> Attribute:
    """Get attribute by name or raise 404."""
    attribute = await get_by_name(db, name)
    if not attribute:
        raise HTTPException(status_code=404, detail="Attribute not found")
    return attribute


async def update(
    db: AsyncSession,
    attribute_id: int,
    attr_in: AttributeUpdate,
) -> Attribute:
    """Update an existing attribute definition."""
    attribute = await get_by_id(db, attribute_id)
    if not attribute:
        raise HTTPException(status_code=404, detail="Attribute not found")

    update_data = attr_in.model_dump(exclude_unset=True)
    new_name = update_data.get("name")
    if new_name and new_name != attribute.name:
        existing = await get_by_name(db, new_name)
        if existing and existing.id != attribute.id:
            raise HTTPException(status_code=400, detail="Attribute already exists")

    for field, value in update_data.items():
        if hasattr(attribute, field):
            setattr(attribute, field, value)

    await db.commit()
    await db.refresh(attribute)
    return attribute


async def delete(db: AsyncSession, attribute_id: int) -> None:
    """Delete an attribute definition by ID."""
    attribute = await get_by_id(db, attribute_id)
    if not attribute:
        raise HTTPException(status_code=404, detail="Attribute not found")
    await delete_attribute(db, attribute)