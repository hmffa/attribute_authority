from sqlalchemy import Column, Integer, String, Boolean, Text, UniqueConstraint, Index
from sqlalchemy.orm import relationship

from ..db.base_class import Base


class Attribute(Base):
    """
    Schema-level definition of an attribute.

    Fields:
      - name: logical attribute name (e.g. "entitlement", "eduPersonAffiliation")
      - is_multivalue: whether attribute can have multiple values per user
      - value_restriction: optional regex that constrains allowed values at definition time
      - description: human-readable description
      - enabled: whether this attribute is currently active
      - created_at: creation timestamp
    """
    __table_args__ = (
        UniqueConstraint("name", name="uq_attribute_name"),
        # TODO add indexing later based in usage
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)            # business name of attribute
    is_multivalue = Column(Boolean, nullable=False, default=True)
    value_restriction = Column(Text, nullable=True) # TODO Should it be called key restriction       # recommended: store regex or JSON schema
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(String(50), nullable=False)  # ISO format datetime

    # relation to actual values
    values = relationship(
        "UserAttributeValue",
        back_populates="attribute_definition",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
