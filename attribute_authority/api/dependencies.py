"""FastAPI dependencies for authentication and authorization."""
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, Request, status
from flaat import access_tokens
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.security import validate_token
from ..db.session import get_async_db
from ..models.privilege import PrivilegeAction
from ..models.user import User
from ..services import authorization
from ..services import user as users
from ..services import attribute_definition as attributes


def _claim_text(claims: Optional[Dict[str, Any]], *keys: str) -> Optional[str]:
    if not claims:
        return None
    for key in keys:
        value = claims.get(key)
        if isinstance(value, str):
            value = value.strip()
            if value:
                return value
    return None


async def _merge_user_profile_claims(
    db: AsyncSession,
    claims: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    if not claims:
        return None

    has_name = _claim_text(claims, "name", "preferred_username") is not None
    has_email = _claim_text(claims, "email") is not None
    if has_name and has_email:
        return claims

    sub = claims.get("sub")
    iss = claims.get("iss")
    if not sub or not iss:
        return claims

    user = await users.get_by_sub_and_iss(db, sub, iss)
    if not user:
        return claims

    merged_claims = dict(claims)
    if not has_name and user.name:
        merged_claims["name"] = user.name
    if not has_email and user.email:
        merged_claims["email"] = user.email
    return merged_claims


async def get_current_user_claims(request: Request) -> Dict[str, Any]:
    """Extract and validate claims from the request token."""
    return await validate_token(request)


async def get_current_actor(
    claims: Dict[str, Any] = Depends(get_current_user_claims),
    db: AsyncSession = Depends(get_async_db),
) -> User:
    """Resolve the caller (Actor) from the OIDC token."""
    sub = claims.get("sub")
    iss = claims.get("iss")
    user = await users.get_by_sub_and_iss(db, sub, iss)
    if not user:
        raise HTTPException(status_code=401, detail="User not registered in AA")
    return user


def require_privilege(action: PrivilegeAction):
    """
    Dependency factory to check if the current actor has the required privilege.
    Automatically detects 'user_id' and 'attribute_name' in path params if present.
    """

    async def dependency(
        request: Request,
        actor: User = Depends(get_current_actor),
        db: AsyncSession = Depends(get_async_db),
    ):
        # Resolve Target User (if in URL)
        target_user = None
        user_id_param = request.path_params.get("user_id")
        if user_id_param:
            try:
                target_user = await users.get_by_id(db, int(user_id_param))
            except Exception:
                pass

        # Resolve Attribute Scope
        attribute_id = None
        attr_name_param = request.path_params.get("attribute_name")
        if attr_name_param:
            attr_def = await attributes.get_by_name(db, attr_name_param)
            if attr_def:
                attribute_id = attr_def.id

        # Check Authorization
        is_allowed = await authorization.has_privilege(
            db,
            actor=actor,
            action=action,
            target_user=target_user,
            attribute_id=attribute_id,
        )

        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You do not have permission to perform {action.value}",
            )

        return actor

    return dependency


async def optional_user_claims(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
) -> Optional[Dict[str, Any]]:
    """
    Try to validate token but don't raise exception if not present.
    Uses cookie-stored id_token first (set during login callback).
    """
    id_token = request.session.get("id_token")
    if id_token:
        token_info = access_tokens.get_access_token_info(
            id_token, verify=settings.ENVIRONMENT == "production"
        )
        body = getattr(token_info, "body", None)
        if isinstance(body, dict):
            return await _merge_user_profile_claims(db, body)
        return None
    try:
        claims = await validate_token(request)
    except HTTPException:
        return None
    return await _merge_user_profile_claims(db, claims)

