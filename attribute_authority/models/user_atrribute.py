from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from ..db.base_class import Base

# TODO: The below design leads to same attribute key values for different users as id is the primary key and other columns are not unique.
class UserAttribute(Base):
    __table_args__ = (UniqueConstraint('user_id', 'key', 'value', name='uq_user_attribute_user_id_key_value'),)
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    key = Column(String(1024), nullable=False)
    value = Column(String(1024), nullable=False)

    user = relationship("User", back_populates="attributes")