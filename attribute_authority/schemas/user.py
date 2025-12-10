from typing import Optional, Any
from pydantic import BaseModel, Field, EmailStr, ConfigDict

class UserBase(BaseModel):
    """Base schema with shared User attributes"""
    sub: str = Field(..., description="OIDC subject identifier", max_length=255)
    iss: str = Field(..., description="OIDC issuer identifier", max_length=255)
    name: Optional[str] = Field(None, description="Display name")
    email: Optional[EmailStr] = Field(None, description="Email address")

class UserCreate(UserBase):
    """Schema for user creation"""
    pass


class UserUpdate(BaseModel):
    """Schema for user updates"""
    sub: Optional[str] = Field(None, description="OIDC subject identifier", max_length=255)
    iss: Optional[str] = Field(None, description="OIDC issuer identifier", max_length=255)
    name: Optional[str] = Field(None, description="Display name")
    email: Optional[EmailStr] = Field(None, description="Email address")


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
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    sub: str
    iss: str
    created_at: str
    model_config = ConfigDict(from_attributes=True)

class UserWithAttributes(UserOut):
    """
    User details combined with a dictionary of their visible attributes.
    Format: { "attribute_name": ["value1", "value2"] }
    """
    attributes: dict[str, list[Any]] = {}