from typing import Optional, Dict

from pydantic import BaseModel, Field

from ..models.privilege import PrivilegeAction


class PrivilegeBase(BaseModel):
    grantee_user_id: int = Field(..., description="User who receives the privilege")
    action: PrivilegeAction = Field(..., description="Granted action")
    attribute_id: Optional[int] = Field(
        None,
        description="Optional attribute definition scope",
    )
    value_restriction: Optional[str] = Field(
        None,
        description="Optional regex/schema restricting attribute values",
    )
    target_restriction: Optional[list[Dict]] = Field(
        None,
        description="Optional JSON constraints for target user",
    )
    is_delegable: bool = Field(False, description="Whether privilege can be delegated")


class PrivilegeCreate(PrivilegeBase):
    pass


class PrivilegeDelegate(PrivilegeBase):
    """Schema for delegating a privilege to another user."""
    pass


class PrivilegeUpdate(BaseModel):
    action: Optional[PrivilegeAction] = None
    attribute_id: Optional[int] = None
    value_restriction: Optional[str] = None
    target_restriction: Optional[Dict] = None
    is_delegable: Optional[bool] = None


class PrivilegeRead(PrivilegeBase):
    id: int
    created_at: str

    class Config:
        from_attributes = True
