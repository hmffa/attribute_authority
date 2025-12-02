from sqlalchemy import Column, Integer, ForeignKey, Text, String, UniqueConstraint, Index
from sqlalchemy.orm import relationship

from ..db.base_class import Base


class UserAttributeValue(Base):
    """
    Actual stored attribute values per user.

    This table stores one row per (user, attribute_definition, value).
    For single-valued attributes you may have at most one row per (user, attribute).
    For multi-valued attributes you can have multiple rows with different 'value'.

    Constraints:
      - Unique(user_id, attribute_id, value) prevents exact duplicates.
    """
    __table_args__ = (
        UniqueConstraint("user_id", "attribute_id", "value", name="uq_user_attribute_value_triplet"),
        # TODO add indexing later based in usage
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    attribute_id = Column(Integer, ForeignKey("attributes.id", ondelete="CASCADE"), nullable=False, index=True)
    value = Column(Text, nullable=False)
    created_at = Column(String(50), nullable=False)  # ISO format datetime
    updated_at = Column(String(50), nullable=False)  # ISO format datetime

    user = relationship("User", back_populates="attribute_values", lazy="joined")
    attribute_definition = relationship("Attribute", back_populates="values", lazy="joined")