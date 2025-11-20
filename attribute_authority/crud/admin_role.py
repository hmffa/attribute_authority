from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..models.admin_role import AdminRole, UserAdminRole
from ..models.user import User


class CRUDAdminRole:
    @staticmethod
    async def get_by_name(db: AsyncSession, name: str) -> Optional[AdminRole]:
        """
        Get an admin role by name.
        """
        query = select(AdminRole).where(AdminRole.name == name)
        result = await db.execute(query)
        return result.scalars().first()

    @staticmethod
    async def get_all(db: AsyncSession) -> List[AdminRole]:
        """
        Get all admin roles.
        """
        query = select(AdminRole)
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def create(
        db: AsyncSession,
        name: str,
        description: Optional[str] = None,
    ) -> AdminRole:
        """
        Create a new admin role.
        """
        db_obj = AdminRole(name=name, description=description)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    @staticmethod
    async def assign_to_user(
        db: AsyncSession,
        user: User,
        role: AdminRole,
    ) -> UserAdminRole:
        """
        Assign an admin role to a user.
        If the user already has the role, return the existing assignment.
        """
        query = select(UserAdminRole).where(
            UserAdminRole.user_id == user.id,
            UserAdminRole.role_id == role.id,
        )
        result = await db.execute(query)
        assignment = result.scalar_one_or_none()
        if assignment:
            return assignment

        assignment = UserAdminRole(user_id=user.id, role_id=role.id)
        db.add(assignment)
        await db.commit()
        await db.refresh(assignment)
        return assignment

    @staticmethod
    async def revoke_from_user(
        db: AsyncSession,
        user: User,
        role: AdminRole,
    ) -> None:
        """
        Remove an admin role from a user.
        """
        query = select(UserAdminRole).where(
            UserAdminRole.user_id == user.id,
            UserAdminRole.role_id == role.id,
        )
        result = await db.execute(query)
        assignment = result.scalar_one_or_none()
        if not assignment:
            return

        await db.delete(assignment)
        await db.commit()

    @staticmethod
    async def get_roles_for_user(
        db: AsyncSession,
        user: User,
    ) -> List[AdminRole]:
        """
        Get all admin roles assigned to a user.
        """
        query = (
            select(AdminRole)
            .join(UserAdminRole, UserAdminRole.role_id == AdminRole.id)
            .where(UserAdminRole.user_id == user.id)
        )
        result = await db.execute(query)
        return result.scalars().all()


crud_admin_role = CRUDAdminRole()
