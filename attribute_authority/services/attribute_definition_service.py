from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from ..models.attribute import Attribute
from ..schemas.attribute import AttributeCreate

class AttributeDefinitionService:
    """
    Manages the 'Attributes' table (The Schema).
    """
    @staticmethod
    async def create_definition(db: AsyncSession, obj_in: AttributeCreate) -> Attribute:
        # Check if name exists
        query = select(Attribute).where(Attribute.name == obj_in.name)
        result = await db.execute(query)
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail=f"Attribute '{obj_in.name}' already exists")

        db_obj = Attribute(
            name=obj_in.name,
            is_multivalue=obj_in.is_multivalue,
            value_restriction=obj_in.value_restriction,
            description=obj_in.description,
            enabled=obj_in.enabled,
            created_at=obj_in.created_at
        )
        db.add(db_obj)
        try:
            await db.commit()
            await db.refresh(db_obj)
            return db_obj
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=400, detail="Database integrity error")

    @staticmethod
    async def get_all_definitions(db: AsyncSession):
        result = await db.execute(select(Attribute))
        return result.scalars().all()

attribute_definition_service = AttributeDefinitionService()