from typing import Optional, List
from pydantic import BaseModel, Field

class InvitationBase(BaseModel):
    group_key: str = Field(..., description="Attribute key for the group")
    group_value: str = Field(..., description="Group value to give access to")
    
class InvitationCreate(InvitationBase):
    invited_user_sub: Optional[str] = Field(None, description="Optional: specific user subject to invite")
    invited_user_iss: Optional[str] = Field(None, description="Optional: specific user issuer to invite")
    max_uses: int = Field(1, description="Maximum number of times this invitation can be used")
    expires_in_minutes: int = Field(1440, description="Invitation expiration time in minutes (default 24h)")

class Invitation(InvitationBase):
    id: int
    hash: str
    created_by_user_id: int
    invited_user_sub: Optional[str] = None
    invited_user_iss: Optional[str] = None
    max_uses: int
    current_uses: int
    expires_at: str
    created_at: str
    status: str
    
    class Config:
        from_attributes = True

class InvitationResponse(BaseModel):
    hash: str
    approve_url: str
    reject_url: str
    expires_at: str
    max_uses: int

class InvitationList(BaseModel):
    invitations: List[Invitation]

class InvitationDetails(Invitation):
    pass