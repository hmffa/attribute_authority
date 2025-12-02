# services/attribute_definition_service.py
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from ..crud.attribute_definition import crud_attribute_definition
from ..schemas.attribute import AttributeCreate

class AttributeDefinitionService:
    @staticmethod
    async def create(db: AsyncSession, obj_in: AttributeCreate):
        exists = await crud_attribute_definition.get_by_name(db, obj_in.name)
        if exists:
            raise HTTPException(status_code=400, detail="Attribute already exists")
        return await crud_attribute_definition.create(db, obj_in)

attribute_definition_service = AttributeDefinitionService()