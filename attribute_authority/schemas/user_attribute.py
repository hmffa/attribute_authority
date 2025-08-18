from typing import List
from pydantic import BaseModel, Field

class UserAttributeBase(BaseModel):
    key: str = Field(..., description="Attribute key", max_length=1024)
    value: str = Field(..., description="Attribute value", max_length=1024)

class UserAttributeCreate(UserAttributeBase):
    user_id: int = Field(..., description="User ID")
    key: str = Field(..., description="Attribute key", max_length=1024)
    value: str = Field(..., description="Attribute value", max_length=1024)

class UserAttributeUpdate(UserAttributeBase):
    id: int = Field(..., description="User Attribute ID")
    user_id: int = Field(..., description="User ID")

class UserAttribute(UserAttributeBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True

class AttributeMutation(BaseModel):
    values: List[str]