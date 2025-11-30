from sqlalchemy import Column, Integer, String, UniqueConstraint, Index
from sqlalchemy.orm import relationship

from ..db.base_class import Base


class User(Base):
    """
    Principal model. A 'subject' in the AA.

    Note:
      - 'sub' and 'iss' store the OIDC subject and issuer so the AA can
        map external identities to local rows.
      - UniqueConstraint ensures we don't create duplicate users for the same
        external identity.
    """
    __table_args__ = (
        UniqueConstraint("sub", "iss", name="uq_user_sub_iss"),
        # TODO add indexing later based in usage
    )

    id = Column(Integer, primary_key=True, index=True)
    sub = Column(String(255), nullable=False, index=True)   # OIDC subject
    iss = Column(String(255), nullable=False, index=True)   # OIDC issuer
    name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    created_at = Column(String(50), nullable=False)  # ISO format datetime

    # relationships
    attribute_values = relationship(
        "UserAttributeValue",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    privileges = relationship(
        "Privilege",
        back_populates="grantee",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
