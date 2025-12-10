from collections import defaultdict
from typing import Any, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession

from ..crud.user import crud_user
from ..models.user import User
from ..models.privilege import PrivilegeAction
from ..services.authorization import authorization_service
from ..schemas.user import UserWithAttributes

class UserService:
    @staticmethod
    async def list_users(db: AsyncSession, page: int, per_page: int) -> Dict[str, Any]:
        """
        Calculates offset and fetches paginated data.
        """
        offset = (page - 1) * per_page
        users = await crud_user.list(db, offset=offset, limit=per_page)
        total = await crud_user.count(db)
        
        return {
            "items": users,
            "total": total,
            "page": page,
            "per_page": per_page
        }
    
    @staticmethod
    async def get_all_users_with_visible_attributes(
        db: AsyncSession, 
        actor: User
    ) -> List[UserWithAttributes]:
        """
        Fetches all users and filters them based on the actor's READ privileges.
        If the actor cannot see any attributes for a user (due to lack of privilege 
        or target_restrictions), that user is excluded from the list.
        """
        # 1. Fetch all users
        users = await crud_user.get_all(db)
        results = []

        for target_user in users:
            visible_attributes = defaultdict(list)

            # 2. Iterate and Filter
            for user_attr in target_user.attribute_values:
                is_allowed = await authorization_service.has_privilege(
                    db,
                    actor=actor,
                    action=PrivilegeAction.READ_VALUE,
                    target_user=target_user,
                    attribute_id=user_attr.attribute_id,
                    value=user_attr.value
                )

                if is_allowed:
                    attr_name = user_attr.attribute_definition.name
                    visible_attributes[attr_name].append(user_attr.value)

            if visible_attributes:
                user_out = UserWithAttributes(
                    id=target_user.id,
                    sub=target_user.sub,
                    iss=target_user.iss,
                    name=target_user.name,
                    email=target_user.email,
                    created_at=target_user.created_at,
                    attributes=visible_attributes
                )
                results.append(user_out)

        return results

user_service = UserService()