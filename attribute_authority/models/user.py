from sqlalchemy import Column, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from ..db.base_class import Base

class User(Base):
    __table_args__ = (UniqueConstraint('sub', 'iss', name='uq_user_sub_iss'),)
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    sub = Column(String(255), index=True)
    iss = Column(String(255), index=True)
    created_at = Column(String(50), nullable=False)

    attributes = relationship("Attribute", back_populates="user", cascade="all, delete-orphan")