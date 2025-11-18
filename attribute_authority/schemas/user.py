from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, EmailStr, ConfigDict

class UserBase(BaseModel):
    """Base schema with shared User attributes"""
    sub: str = Field(..., description="Subject identifier", max_length=255)
    iss: str = Field(..., description="Issuer identifier", max_length=255)
    attributes: Optional[List[str]] = Field(
        None,
        description="List of user attributes (e.g. URNs)"
    )

class UserCreate(UserBase):
    """Schema for user creation"""
    pass


class UserUpdate(BaseModel):
    """Schema for user updates"""
    sub: Optional[str] = Field(None, description="Subject identifier", max_length=255)
    iss: Optional[str] = Field(None, description="Issuer identifier", max_length=255)
    attributes: Optional[List[str]] = Field(
        None, description="List of user attributes (e.g. URNs)"
    )


class UserInDBBase(UserBase):
    """Base schema for User from DB"""
    id: int
    model_config = ConfigDict(from_attributes=True)


class User(UserInDBBase):
    """Schema for API responses"""
    pass


class UserInDB(UserInDBBase):
    """Schema for internal use with additional fields"""
    pass


class UserOut(BaseModel):
    id: int
    name: str | None = None
    email: EmailStr | None = None
    sub: str
    iss: str | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)