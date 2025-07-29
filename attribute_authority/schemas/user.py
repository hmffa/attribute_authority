from typing import Optional, List
from pydantic import BaseModel, EmailStr
from datetime import date

class UserAffiliationBase(BaseModel):
    affiliation: str

class UserAffiliation(UserAffiliationBase):
    id: int
    user_id: int
    
    class Config:
        from_attributes = True

class UserGroupBase(BaseModel):
    group_name: str

class UserGroup(UserGroupBase):
    id: int
    user_id: int
    
    class Config:
        from_attributes = True

class UserBase(BaseModel):
    email: Optional[EmailStr] = None
    email_verified: Optional[bool] = None
    name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    preferred_username: Optional[str] = None
    picture: Optional[str] = None
    display_name: Optional[str] = None
    
    # New fields
    bw_card_number: Optional[str] = None
    bw_card_valid_to: Optional[date] = None
    bw_card_uid: Optional[str] = None
    ou: Optional[str] = None
    upn: Optional[str] = None
    eduperson_principal_name: Optional[str] = None

class UserCreate(UserBase):
    sub: str
    iss: str
    email: EmailStr

class UserUpdate(UserBase):
    pass

class UserInDBBase(UserBase):
    id: int
    sub: str
    iss: str
    
    class Config:
        from_attributes = True

class User(UserInDBBase):
    """User model returned to clients"""
    affiliations: List[UserAffiliation] = []
    groups: List[UserGroup] = []

class UserInDB(UserInDBBase):
    """User model stored in DB with potential extra internal fields"""
    created_at: str
    updated_at: str
    affiliations: List[UserAffiliation] = []
    groups: List[UserGroup] = []