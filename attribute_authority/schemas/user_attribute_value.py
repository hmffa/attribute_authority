from typing import Optional
from pydantic import BaseModel


class UserAttributeValueBase(BaseModel):
    user_id: int
    attribute_id: int
    value: str

class UserAttributeValueCreate(UserAttributeValueBase):
    pass

class UserAttributeValueRead(UserAttributeValueBase):
    id: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

class UserAttributeValueUpdate(BaseModel):
    value: Optional[str] = None