from fastapi import APIRouter, Depends, HTTPException, Request, status
from typing import Dict, Any, List
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from tomlkit import key, value

from ..dependencies import get_current_user_claims, get_db_dependency, optional_user_claims
from ...schemas.attribute import AttributeMutation, AttributeCreate
from ...crud.user_attribute_value import crud_attribute
from ...crud.user import crud_user
from ...services.user_attribute_value import attribute_service
from ...core.logging_config import logger
from ...web.templating import templates
from ...schemas.user import UserCreate


router = APIRouter()


@router.get("/user/myattributes", response_model=Dict[str, Any])
async def myattributes(
    request: Request,
    claims: Dict[str, Any] = Depends(optional_user_claims),
    db: AsyncSession = Depends(get_db_dependency()),
):
    """
    Attribute Authority My Attributes Endpoint.
    Returns all attributes of the current user.
    """
    current_url = request.url.path
    if not claims:
        login_url = f"/api/v1/auth/login?next={current_url}"
        return RedirectResponse(url=login_url)

    logger.info(f"Processing myattributes request for sub: {claims.get('sub')}")

    # Fetch user attributes using your existing service # TODO refactor the service method name
    attributes = await attribute_service.get_attributes_with_user_id(db, claims)

    # TODO Use pydantic model for rendering template
    display_claims = {
        "sub": claims.get("sub"),
        "iss": claims.get("iss"),
        "name": claims.get("name") or claims.get("preferred_username"),
        "email": claims.get("email"),
    }

    return templates.TemplateResponse(
        "user_attributes.html",
        {
            "request": request,
            "claims": display_claims,
            "attributes": attributes,
        },
    )

@router.delete("/user/myattributes/{attr_id}", response_model=Dict[str, Any])
async def delete_user_attribute(
    attr_id: int,
    request: Request,
    claims: Dict[str, Any] = Depends(optional_user_claims),
    db: AsyncSession = Depends(get_db_dependency()),
):
    """
    Attribute Authority Delete User Attribute Endpoint.
    Deletes a specific user attribute based on the provided access token.
    """
    # TODO Handle Delete all values for a given key in tryServerDelete
    logger.info(f"Processing delete_user_attribute request for sub: {claims.get('sub')} and attribute id: {attr_id}")
    await crud_attribute.delete(db, attr_id=attr_id)
    return {"status": "success", "message": "Attribute deleted successfully."}


@router.put("/admin/attributes/{key}", response_model=Dict[str, List[str]])
async def set_attributes(
    key: str,
    body: AttributeMutation,
    claims: Dict[str, Any] = Depends(get_current_user_claims),
    db: AsyncSession = Depends(get_db_dependency()),
):
    sub = claims.get("sub")
    iss = claims.get("iss")
    if not sub or not iss:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing sub or iss in token")

    user = await crud_user.get_by_sub_and_iss(db, sub=sub, iss=iss)
    if not user:
        user = await crud_user.create(db, UserCreate(sub=sub, iss=iss))

    current = {ua.value for ua in await crud_attribute.get_by_user_id_and_key(db, user.id, key)}
    desired = set(body.values)

    for v in desired - current:
        await crud_attribute.create(db, user.id, key, v)
    for v in current - desired:
        await crud_attribute.delete(db, user.id, key, v)

    updated = await crud_attribute.get_by_user_id_and_key(db, user.id, key)
    return {key: [ua.value for ua in updated]}

@router.post("/admin/attributes/{key}", response_model=Dict[str, List[str]])
async def add_attributes(
    key: str,
    body: AttributeMutation,
    # claims: Dict[str, Any] = Depends(require_admin_claims),
    claims: Dict[str, Any] = Depends(get_current_user_claims),
    db: AsyncSession = Depends(get_db_dependency()),
):
    sub = claims.get("sub")
    iss = claims.get("iss")
    if not sub or not iss:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing sub or iss in token")

    user = await crud_user.get_by_sub_and_iss(db, sub=sub, iss=iss)
    if not user:
        user = await crud_user.create(db, UserCreate(sub=sub, iss=iss))

    await db.refresh(user)

    existing_attributes = await crud_attribute.get_by_user_id_and_key(db, user.id, key)
    existing_values = {ua.value for ua in existing_attributes}

    for v in body.values:
        if v not in existing_values:
            user_attribute_create_obj = AttributeCreate(user_id=user.id, key=key, value=v)
            await crud_attribute.create(db, obj_in=user_attribute_create_obj)

    updated = await crud_attribute.get_by_user_id_and_key(db, user.id, key)
    return {key: [ua.value for ua in updated]}

@router.delete("/admin/attributes/{key}", response_model=Dict[str, List[str]])
async def remove_attributes(
    key: str,
    body: AttributeMutation,
    claims: Dict[str, Any] = Depends(get_current_user_claims),
    db: AsyncSession = Depends(get_db_dependency()),
):
    sub = claims.get("sub")
    iss = claims.get("iss")
    if not sub or not iss:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing sub or iss in token")

    user = await crud_user.get_by_sub_and_iss(db, sub=sub, iss=iss)
    if not user:
        return {key: []}

    for v in body.values:
        try:
            await crud_attribute.delete(db, user.id, key, v)
        except:
            continue

    updated = await crud_attribute.get_by_user_id_and_key(db, user.id, key)
    return {key: [ua.value for ua in updated]}

@router.get("/userattributes", response_model=Dict[str, Any])
async def userattributes(
    request: Request,
    claims: Dict[str, Any] = Depends(get_current_user_claims),
    db: AsyncSession = Depends(get_db_dependency()),
):
    """
    Attribute Authority User Attributes Endpoint.
    Returns user attributes based on the provided access token.
    """
    logger.info(f"Processing userattributes request for sub: {claims.get('sub')}")
    return await attribute_service.get_attributes_with_user_id(db, claims)

@router.get("/userattributes/{key}", response_model=Dict[str, Any])
async def userattribute(
    key: str,
    request: Request,
    claims: Dict[str, Any] = Depends(get_current_user_claims),
    db: AsyncSession = Depends(get_db_dependency()),
):
    """
    Attribute Authority User Attribute Endpoint.
    Returns a specific user attribute based on the provided access token.
    """
    logger.info(f"Processing userattribute request for sub: {claims.get('sub')} and key: {key}")
    return await attribute_service.get_attribute(db, claims, key)