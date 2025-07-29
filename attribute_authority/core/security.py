from typing import Dict, Any
from flaat.fastapi import Flaat
from fastapi import Request, HTTPException, status
from .config import settings
from .logging_config import logger

flaat = Flaat()
trusted_ops = settings.TRUSTED_OP_LIST.split(",")
flaat.set_trusted_OP_list(trusted_ops)
# flaat.set_cache_lifetime(settings.TOKEN_CACHE_LIFETIME) # FIXME: Set cache lifetime for token validation

async def validate_token(request: Request) -> Dict[str, Any]:
    """
    Validates access token and returns claims.
    """
    # Extract token from Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        logger.warning("No valid access token provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No valid access token provided",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = auth_header[len("Bearer "):]

    # Get user infos from access token
    user_infos = flaat.get_user_infos_from_access_token(access_token)
    if not user_infos:
        logger.warning("Invalid token or token expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token or token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user subject identifier
    sub = user_infos.subject
    if not sub:
        logger.warning("Token does not contain subject identifier")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token does not contain subject identifier",
        )
    
    return user_infos.user_info  # Return the user info dictionary
