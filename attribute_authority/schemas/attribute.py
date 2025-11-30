from typing import Optional
from pydantic import BaseModel, Field


class AttributeBase(BaseModel):
    name: str = Field(..., description="Business name of attribute", max_length=255)
    is_multivalue: bool = Field(True, description="Whether attribute can have multiple values")
    value_restriction: Optional[str] = Field(
        None,
        description="Optional regex or schema limiting allowed values",
    )
    description: Optional[str] = Field(None, description="Human-readable description")
    enabled: bool = Field(True, description="Whether this attribute is active")


class AttributeCreate(AttributeBase):
    created_at: str = Field(..., description="ISO timestamp when created")


class AttributeUpdate(BaseModel):
    name: Optional[str] = None
    is_multivalue: Optional[bool] = None
    value_restriction: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None


class AttributeRead(AttributeBase):
    id: int
    created_at: str

    class Config:
        from_attributes = True