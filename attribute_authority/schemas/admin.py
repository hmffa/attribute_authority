from __future__ import annotations

from typing import Optional, List

from pydantic import BaseModel, Field

from ..models.attribute_privilege_rule import PrivilegeAction, TargetScope


# ---------------------------------------------------------------------------
# Admin roles
# ---------------------------------------------------------------------------

class AdminRoleBase(BaseModel):
    name: str = Field(..., example="GLOBAL_ATTR_ADMIN")
    description: Optional[str] = Field(
        None,
        example="Global attribute administrator",
    )


class AdminRoleCreate(AdminRoleBase):
    pass


class AdminRoleRead(AdminRoleBase):
    id: int

    class Config:
        from_attributes = True  # Pydantic v2; use orm_mode=True if v1


class AdminRoleAssignmentBase(BaseModel):
    user_id: int = Field(..., example=1)
    role_name: str = Field(..., example="GLOBAL_ATTR_ADMIN")


class AdminRoleAssignmentResponse(BaseModel):
    user_id: int
    role_name: str


# ---------------------------------------------------------------------------
# Attribute privilege rules
# ---------------------------------------------------------------------------

class AttributePrivilegeRuleBase(BaseModel):
    description: str = Field(..., example="Global admin can CRUD all attributes")
    action: PrivilegeAction = Field(..., example=PrivilegeAction.update)
    attribute_key_regex: str = Field(..., example="^.*$")
    attribute_value_regex: Optional[str] = Field(
        None,
        example="^urn:example:vo1:group:.*$",
    )
    target_scope: TargetScope = Field(
        TargetScope.self,
        example=TargetScope.any,
    )
    required_role_name: str = Field(
        ...,
        example="GLOBAL_ATTR_ADMIN",
        description="Name of AdminRole that this rule requires",
    )


class AttributePrivilegeRuleCreate(AttributePrivilegeRuleBase):
    pass


class AttributePrivilegeRuleUpdate(BaseModel):
    """
    Partial update of a rule.
    All fields optional; only provided ones are changed.
    """

    description: Optional[str] = None
    action: Optional[PrivilegeAction] = None
    attribute_key_regex: Optional[str] = None
    attribute_value_regex: Optional[str] = None
    target_scope: Optional[TargetScope] = None
    required_role_name: Optional[str] = None


class AttributePrivilegeRuleRead(BaseModel):
    id: int
    description: str
    action: PrivilegeAction
    attribute_key_regex: str
    attribute_value_regex: Optional[str]
    target_scope: TargetScope
    required_role_name: str

    class Config:
        from_attributes = True


class AttributePrivilegeRuleList(BaseModel):
    items: List[AttributePrivilegeRuleRead]
