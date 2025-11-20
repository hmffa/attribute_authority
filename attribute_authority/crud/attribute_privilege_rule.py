from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..models.attribute_privilege_rule import AttributePrivilegeRule, PrivilegeAction, TargetScope
from ..models.admin_role import AdminRole


class CRUDAtttributePrivilegeRule:
    @staticmethod
    async def get_all(db: AsyncSession) -> List[AttributePrivilegeRule]:
        """
        Get all attribute privilege rules.
        """
        query = select(AttributePrivilegeRule)
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        rule_id: int,
    ) -> Optional[AttributePrivilegeRule]:
        """
        Get a single rule by ID.
        """
        return await db.get(AttributePrivilegeRule, rule_id)

    @staticmethod
    async def get_by_action(
        db: AsyncSession,
        action: PrivilegeAction,
    ) -> List[AttributePrivilegeRule]:
        """
        Get all rules for a given action.
        """
        query = select(AttributePrivilegeRule).where(
            AttributePrivilegeRule.action == action
        )
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def create(
        db: AsyncSession,
        *,
        description: str,
        action: PrivilegeAction,
        attribute_key_regex: str,
        required_role: AdminRole,
        target_scope: TargetScope = TargetScope.self,
        attribute_value_regex: Optional[str] = None,
    ) -> AttributePrivilegeRule:
        """
        Create a new attribute privilege rule.
        """
        db_obj = AttributePrivilegeRule(
            description=description,
            action=action,
            attribute_key_regex=attribute_key_regex,
            attribute_value_regex=attribute_value_regex,
            target_scope=target_scope,
            required_role=required_role,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    @staticmethod
    async def delete(
        db: AsyncSession,
        rule_id: int,
    ) -> None:
        """
        Delete a rule by ID.
        """
        db_obj = await db.get(AttributePrivilegeRule, rule_id)
        if not db_obj:
            return
        await db.delete(db_obj)
        await db.commit()


crud_attribute_privilege_rule = CRUDAtttributePrivilegeRule()
