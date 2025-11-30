from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from ..db.base_class import Base

class Invitation(Base):
    id = Column(Integer, primary_key=True, index=True)
    hash = Column(String(255), unique=True, index=True, nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    invited_user_sub = Column(String(1024), nullable=True)  # Optional: specific user sub
    invited_user_iss = Column(String(1024), nullable=True)  # Optional: specific user issuer
    group_key = Column(String(1024), nullable=False)
    group_value = Column(String(1024), nullable=False)
    max_uses = Column(Integer, default=1)
    current_uses = Column(Integer, default=0)
    expires_at = Column(String(50), nullable=False)  # ISO format datetime
    created_at = Column(String(50), nullable=False)  # ISO format datetime
    status = Column(String(50), default="active")  # active, used, expired
    
    # Relationship with the user who created the invitation
    creator = relationship("User", foreign_keys=[created_by_user_id])