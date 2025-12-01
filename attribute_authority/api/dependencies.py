from fastapi import HTTPException, Request, Depends, status, Form
from typing import Dict, Any
from flaat import access_tokens

from ..db.session import get_async_db
from ..core.security import validate_token
from ..core.config import settings
from ..models.user import User
from ..models.attribute_privilege_rule import PrivilegeAction
from ..services.authorization import has_attribute_privilege

async def get_current_user_claims(
    request: Request,
):
    """
    Dependency to validate token and return user claims
    """
    return await validate_token(request)

def get_db_dependency():
    """
    Return the database dependency
    """
    return get_async_db

def require_admin_claims(claims: Dict[str, Any] = Depends(get_current_user_claims)):
    if not claims.get("role") == "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return claims

async def optional_user_claims(request: Request):
    """
    Try to validate token but don't raise exception if not present.
    First, use cookie-stored id_token (set during login callback).
    """
    id_token = request.session.get("id_token")
    if id_token:
        token_info = access_tokens.get_access_token_info(id_token, verify=settings.ENVIRONMENT == "production")
        return token_info.body
    try:
        return await validate_token(request)
    except HTTPException:
        return None
    
def require_attribute_privilege(action: PrivilegeAction):
    async def dependency(
        user_id: int,
        attribute_key: str,
        value: str | None = None,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_dependency()),
    ):
        target_user = await db.get(User, user_id)
        if not target_user:
            raise HTTPException(status_code=404, detail="Target user not found")

        allowed = await has_attribute_privilege(
            db=db,
            actor=current_user,
            action=action,
            attribute_key=attribute_key,
            attribute_value=value,
            target_user=target_user,
        )
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough privilege to operate on this attribute",
            )

    return dependency