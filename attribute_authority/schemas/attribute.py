from typing import Optional
from pydantic import BaseModel

class AttributeBase(BaseModel):
    name: str
    is_multivalue: bool = True
    value_restriction: Optional[str] = None
    description: Optional[str] = None
    enabled: bool = True

class AttributeCreate(AttributeBase):
    created_at: str # ISO timestamp

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

