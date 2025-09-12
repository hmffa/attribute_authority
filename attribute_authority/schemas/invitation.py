from typing import Optional, List
from pydantic import BaseModel, Field, model_validator
import datetime

class InvitationBase(BaseModel):
    group_key: str = Field(..., description="Attribute key for the group")
    group_value: str = Field(..., description="Group value to give access to")
    
class InvitationCreate(InvitationBase):
    invited_user_sub: Optional[str] = Field(None, description="Optional: specific user subject to invite")
    invited_user_iss: Optional[str] = Field(None, description="Optional: specific user issuer to invite")
    max_uses: int = Field(1, description="Maximum number of times this invitation can be used")
    expires_in_seconds: Optional[int] = Field(None, description="Invitation expiration time in seconds (default 24h)")
    expires_at_epoch_seconds: Optional[int] = Field(None, description="Optional: exact expiration time as epoch seconds")

    @model_validator(mode="before")   
    def check_expiration(cls, values):
        expires_in = values.get('expires_in_seconds')
        expires_at = values.get('expires_at_epoch_seconds')
        if expires_in is None and expires_at is None:
            raise ValueError("Either expires_in_seconds or expires_at_epoch_seconds must be provided.")
        elif expires_in is not None and expires_at is not None:
            raise ValueError("Only one of expires_in_seconds or expires_at_epoch_seconds should be provided.")
        return values
    
    @property
    def expires_at(self) -> str:
        """Calculate expiration date and time in UTC ISO format"""
        if self.expires_at_epoch_seconds:
            dt = datetime.datetime.fromtimestamp(self.expires_at_epoch_seconds, tz=datetime.timezone.utc)
        elif self.expires_in_seconds:
            dt = datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(seconds=self.expires_in_seconds)
        else:
            raise ValueError("Either expires_in_seconds or expires_at_epoch_seconds must be provided.")
        return dt.isoformat() + 'Z'
    
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
    invitation_url: str
    expires_at_utc: str
    max_uses: int

class InvitationList(BaseModel):
    invitations: List[Invitation]

class InvitationDetails(Invitation):
    pass