from sqlalchemy import Column, Integer, String, Boolean, Date, ForeignKey
from sqlalchemy.orm import relationship

from ..db.base_class import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    sub = Column(String(255), unique=True, index=True)
    iss = Column(String(255), index=True)
    bw_card_number = Column(String(100))
    bw_card_valid_to = Column(Date)
    bw_card_uid = Column(String(100))
    preferred_username = Column(String(100))
    given_name = Column(String(100))
    family_name = Column(String(100))
    display_name = Column(String(255))
    email = Column(String(255), index=True)
    email_verified = Column(Boolean, default=False)
    picture = Column(String, unique=True, nullable=True)
    name = Column(String(255))
    ou = Column(String(100))
    upn = Column(String(255))
    eduperson_principal_name = Column(String(255))
    
    # Relationships
    affiliations = relationship("UserAffiliation", back_populates="user")
    groups = relationship("UserGroup", back_populates="user")


class UserAffiliation(Base):
    __tablename__ = "user_affiliations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    affiliation = Column(String(255))
    
    # Relationship
    user = relationship("User", back_populates="affiliations")


class UserGroup(Base):
    __tablename__ = "user_groups"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    group_name = Column(String(255))
    
    # Relationship
    user = relationship("User", back_populates="groups")

