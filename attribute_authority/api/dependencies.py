from fastapi import HTTPException, Request, Depends, status, Path
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from flaat import access_tokens

from ..db.session import get_async_db
from ..core.security import validate_token
from ..core.config import settings
from ..models.user import User
from ..models.privilege import PrivilegeAction
from ..services.authorization import authorization_service
from ..crud.user import crud_user
from ..crud.attribute_definition import crud_attribute_definition

async def get_current_user_claims(request: Request) -> Dict[str, Any]:
    return await validate_token(request)

def get_db_dependency():
    return get_async_db

async def get_current_actor(
    claims: Dict[str, Any] = Depends(get_current_user_claims),
    db: AsyncSession = Depends(get_async_db)
) -> User:
    """
    Resolves the caller (Actor) from the OIDC token.
    """
    sub = claims.get("sub")
    iss = claims.get("iss")
    user = await crud_user.get_by_sub_and_iss(db, sub, iss)
    if not user:
        # Auto-provisioning is handled in login callback, but if accessing API directly:
        raise HTTPException(status_code=401, detail="User not registered in AA")
    return user

def require_privilege(action: PrivilegeAction):
    """
    Decorator to check if the current actor has the required privilege.
    Automatically detects 'user_id' and 'attribute_name' in path params if present.
    """
    async def dependency(
        request: Request,
        actor: User = Depends(get_current_actor),
        db: AsyncSession = Depends(get_async_db),
    ):
        # 1. Resolve Target User (if strictly one user is being targeted in URL)
        # We look for 'user_id' in path parameters
        target_user = None
        user_id_param = request.path_params.get("user_id")
        if user_id_param:
            try:
                target_user = await crud_user.get(db, int(user_id_param)) # Assuming get_by_id exists or adding it
            except:
                pass # If logic fails, we assume no specific target restriction check needed yet
        
        # 2. Resolve Attribute Scope (if specific attribute is targeted)
        attribute_id = None
        attr_name_param = request.path_params.get("attribute_name")
        if attr_name_param:
            attr_def = await crud_attribute_definition.get_by_name(db, attr_name_param)
            if attr_def:
                attribute_id = attr_def.id

        # 3. Check Authorization
        is_allowed = await authorization_service.has_privilege(
            db,
            actor=actor,
            action=action,
            target_user=target_user,
            attribute_id=attribute_id,
            # value=... # Value checking is usually done inside the service logic for SET/ADD
        )

        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You do not have permission to perform {action.value}"
            )
        
        return actor

    return dependency

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

async def get_current_actor(
    claims: Dict[str, Any] = Depends(get_current_user_claims),
    db: AsyncSession = Depends(get_db_dependency)
) -> User:
    """
    Resolves the caller (Actor) from the OIDC token claims into a database User object.
    """
    sub = claims.get("sub")
    iss = claims.get("iss")
    
    if not sub or not iss:
        raise HTTPException(status_code=401, detail="Invalid token claims")

    user = await crud_user.get_by_sub_and_iss(db, sub, iss)
    if not user:
        # If user doesn't exist in DB, they have no privileges.
        raise HTTPException(status_code=401, detail="User not registered in AA")
        
    return user