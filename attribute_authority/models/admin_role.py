from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from ..db.base_class import Base


class AdminRole(Base):
    __tablename__ = "admin_role"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(255), unique=True, nullable=False)   # e.g. "GLOBAL_ATTR_ADMIN"
    description = Column(String(1024), nullable=True)

    assignments = relationship("UserAdminRole", back_populates="role", cascade="all, delete-orphan")


class UserAdminRole(Base):
    __tablename__ = "user_admin_role"

    __table_args__ = (
        UniqueConstraint('user_id', 'role_id', name='uq_user_admin_role'),
    )

    id      = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    role_id = Column(Integer, ForeignKey("admin_role.id", ondelete="CASCADE"), nullable=False)

    user = relationship("User")
    role = relationship("AdminRole", back_populates="assignments")
