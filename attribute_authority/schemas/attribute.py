from typing import List
from pydantic import BaseModel, Field

class AttributeBase(BaseModel):
    key: str = Field(..., description="Attribute key", max_length=1024)
    value: str = Field(..., description="Attribute value", max_length=1024)

class AttributeCreate(AttributeBase):
    user_id: int = Field(..., description="User ID")
    key: str = Field(..., description="Attribute key", max_length=1024)
    value: str = Field(..., description="Attribute value", max_length=1024)

class AttributeUpdate(AttributeBase):
    id: int = Field(..., description="Attribute ID")
    user_id: int = Field(..., description="User ID")

class Attribute(AttributeBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True

class AttributeMutation(BaseModel):
    values: List[str]