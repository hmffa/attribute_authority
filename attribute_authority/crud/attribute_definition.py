from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from ..models.attribute import Attribute
from ..schemas.attribute import AttributeCreate

class CRUDAttributeDefinition:
    @staticmethod
    async def get_by_name(db: AsyncSession, name: str) -> Optional[Attribute]:
        result = await db.execute(select(Attribute).where(Attribute.name == name))
        return result.scalars().first()

    @staticmethod
    async def get_all(db: AsyncSession) -> List[Attribute]:
        result = await db.execute(select(Attribute))
        return result.scalars().all()

    @staticmethod
    async def create(db: AsyncSession, obj_in: AttributeCreate) -> Attribute:
        db_obj = Attribute(
            name=obj_in.name,
            is_multivalue=obj_in.is_multivalue,
            value_restriction=obj_in.value_restriction,
            description=obj_in.description,
            enabled=obj_in.enabled,
            created_at=obj_in.created_at
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

crud_attribute_definition = CRUDAttributeDefinition()