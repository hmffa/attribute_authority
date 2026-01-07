import enum
from typing import Optional
from sqlalchemy import (
    Column,
    Integer,
    ForeignKey,
    String,
    Text,
    Boolean,
    Enum as SAEnum,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from ..db.base_class import Base


class PrivilegeAction(str, enum.Enum):
    """
    Canonical list of actions that a privilege can grant.
    Extend as needed.
    """
    CREATE_ATTR = "create_attr"
    UPDATE_ATTR = "update_attr"
    DELETE_ATTR = "delete_attr"
    READ_ATTR = "read_attr"

    SET_VALUE = "set_value"
    ADD_VALUE = "add_value"
    REMOVE_VALUE = "remove_value"
    DELETE_VALUE = "delete_value"
    READ_VALUE = "read_value"

    ASSIGN_PRIVILEGE = "assign_privilege"


class Privilege(Base):
    """
    Privilege (policy) table.

    Each row grants the grantee_user the right to perform 'action' on
    attribute(s) optionally filtered by attribute_id/value_restriction and
    constrained by target_restriction.

    Columns:
      - grantee_user_id: the user who receives the privilege (who can act)
      - action: one of PrivilegeAction
      - attribute_id: optional FK to attribute_definitions (NULL means applies to any attribute)
      - value_restriction: optional regex (string) that the target attribute value must match
      - target_restriction: optional JSON describing constraints a target user must satisfy
          (e.g. [{"eduPersonAffiliation": "^staff$"}, {"entitlement": "^urn:..."}])
      - is_delegable: whether the grantee may delegate this privilege to others
      - created_at: timestamp
    """
    id = Column(Integer, primary_key=True, index=True)
    grantee_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(SAEnum(PrivilegeAction, name="privilege_action"), nullable=False)
    attribute_id = Column(Integer, ForeignKey("attributes.id", ondelete="CASCADE"), nullable=True, index=True)
    value_restriction = Column(Text, nullable=True)   # regex string or JSON schema reference
    target_restriction = Column(JSON, nullable=True)  # application-specific JSON filters
    is_delegable = Column(Boolean, nullable=False, default=False)
    created_at = Column(String(50), nullable=False)  # ISO format datetime
    # TODO: add updated_at column later for tracking changes

    # Relations
    grantee = relationship("User", back_populates="privileges", lazy="joined")
    attribute = relationship("Attribute", lazy="joined")

    __table_args__ = (
        UniqueConstraint(
            "grantee_user_id", 
            "action", 
            "attribute_id", 
            "value_restriction", 
            name="uq_privilege_scope"
        ), # target_restriction was left out as it is flexible with AND/OR logic and can be updated
        # TODO add indexing later based in usage
    )