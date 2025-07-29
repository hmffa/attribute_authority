from fastapi import Request

from ..db.session import get_async_db
from ..core.security import validate_token

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
