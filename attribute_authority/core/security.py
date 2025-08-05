from typing import Dict, Any
from flaat.fastapi import Flaat
from flaat import access_tokens
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

    # Extract info from access token
    token_info = access_tokens.get_access_token_info(access_token, verify=False) # TODO Access token verification disabled for now

    # Get user infos from access token
    # user_infos = flaat.get_user_infos_from_access_token(access_token)
    if not token_info:
        logger.warning("Invalid token or token expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token or token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user subject identifier
    sub = token_info.body.get("sub")
    if not sub:
        logger.warning("Token does not contain subject identifier")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token does not contain subject identifier",
        )

    return token_info.body  # Return the user info dictionary
