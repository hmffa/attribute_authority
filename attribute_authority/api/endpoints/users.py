from typing import List, Dict, Any
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import require_admin_claims, get_db_dependency, get_current_user_claims
from ...crud.user import crud_user
from ...crud.attribute import crud_attribute
from ...services.attribute_service import attribute_service
from ...core.logging_config import logger

router = APIRouter()



@router.get("/admin/users", response_model=List[Dict[str, Any]])
async def list_users(
    request: Request,
    claims: Dict[str, Any] = Depends(require_admin_claims),
    db: AsyncSession = Depends(get_db_dependency()),
):
    """
    Attribute Authority List Users Endpoint.
    Return list of all users
    """
    current_url = request.url.path
    if not claims:
        login_url = f"/api/v1/auth/login?next={current_url}"
        return RedirectResponse(url=login_url)
    
    logger.info(f"Processing list_users request by admin sub: {claims.get('sub')}")
    users = await crud_user.get_all(db)
    result = []
    for user in users:
        attributes = await crud_attribute.get_by_user_id(db, user.id)
        attr_dict = {}
        for attr in attributes:
            if attr.key not in attr_dict:
                attr_dict[attr.key] = []
            attr_dict[attr.key].append(attr.value)
        result.append({
            "sub": user.sub,
            "iss": user.iss,
            "attributes": attr_dict
        })
    return result



