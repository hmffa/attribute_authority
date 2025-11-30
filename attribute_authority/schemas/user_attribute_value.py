from typing import Optional, List
from pydantic import BaseModel, Field

class UserAttributeValueBase(BaseModel):
    user_id: int = Field(..., description="User ID")
    attribute_id: int = Field(..., description="Attribute definition ID")
    value: str = Field(..., description="Attribute value")
    source: Optional[str] = Field(None, description="Provenance e.g. self/admin/sync")


class UserAttributeValueCreate(UserAttributeValueBase):
    created_at: str = Field(..., description="ISO timestamp when created")
    updated_at: str = Field(..., description="ISO timestamp when last updated")


class UserAttributeValueUpdate(BaseModel):
    value: Optional[str] = None
    source: Optional[str] = None
    updated_at: Optional[str] = None


class UserAttributeValueRead(UserAttributeValueBase):
    id: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class AttributeMutation(BaseModel):
    values: List[str] = Field(..., description="New set of values to apply")
