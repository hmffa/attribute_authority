"""Attribute definition service - combines data access and business logic."""
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..models.attribute import Attribute
from ..schemas.attribute import AttributeCreate


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
    result = await db.execute(select(Attribute))
    return result.scalars().all()


async def create_attribute(db: AsyncSession, attr_in: AttributeCreate) -> Attribute:
    """Create a new attribute definition (internal)."""
    attribute = Attribute(
        name=attr_in.name,
        is_multivalue=attr_in.is_multivalue,
        value_restriction=attr_in.value_restriction,
        description=attr_in.description,
        enabled=attr_in.enabled,
        created_at=attr_in.created_at,
    )
    db.add(attribute)
    await db.commit()
    await db.refresh(attribute)
    return attribute


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