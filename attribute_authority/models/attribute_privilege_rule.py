from sqlalchemy import Column, Integer, String, Enum, ForeignKey
from sqlalchemy.orm import relationship
from ..db.base_class import Base
import enum


class PrivilegeAction(str, enum.Enum):
    create = "create"
    read   = "read"
    update = "update"
    delete = "delete"


class TargetScope(str, enum.Enum):
    self       = "self"    # only own attributes
    any        = "any"     # any user
    # we can add 'same_vo', 'same_group' later if you introduce those concepts


class AttributePrivilegeRule(Base):
    __tablename__ = "attribute_privilege_rule"

    id = Column(Integer, primary_key=True, index=True)

    description = Column(String(1024), nullable=False)

    # which CRUD operation
    action = Column(Enum(PrivilegeAction), nullable=False)

    # which attribute keys it applies to (regex on Attribute.key)
    attribute_key_regex = Column(String(1024), nullable=False)

    # optional: further restriction on value (regex on Attribute.value)
    attribute_value_regex = Column(String(1024), nullable=True)

    # scope of allowed target users
    target_scope = Column(Enum(TargetScope), nullable=False, default=TargetScope.self)

    # which admin role must the actor have
    required_role_id = Column(Integer, ForeignKey("admin_role.id"), nullable=False)
    required_role = relationship("AdminRole")
