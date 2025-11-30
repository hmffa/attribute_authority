from __future__ import annotations
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_db_dependency, require_admin_claims
from ...crud.admin_role import crud_admin_role
from ...crud.attribute_privilege_rule import crud_attribute_privilege_rule
from ...crud.user import crud_user
from ...schemas.privilege import (
    AdminRoleCreate,
    AdminRoleRead,
    AdminRoleAssignmentBase,
    AdminRoleAssignmentResponse,
    AttributePrivilegeRuleCreate,
    AttributePrivilegeRuleUpdate,
    AttributePrivilegeRuleRead,
    AttributePrivilegeRuleList,
)
from ...models.attribute_privilege_rule import PrivilegeAction, TargetScope
from ...core.logging_config import logger

router = APIRouter(prefix="/admin", tags=["admin-privileges"])


# ---------------------------------------------------------------------------
# Admin roles endpoints
# ---------------------------------------------------------------------------

@router.get("/roles", response_model=List[AdminRoleRead])
async def list_admin_roles(
    claims: Dict[str, Any] = Depends(require_admin_claims),
    db: AsyncSession = Depends(get_db_dependency),
):
    """
    List all internal AA admin roles.
    """
    logger.info(f"User {claims.get('sub')} listing admin roles")
    roles = await crud_admin_role.get_all(db)
    return roles


@router.post("/roles", response_model=AdminRoleRead, status_code=status.HTTP_201_CREATED)
async def create_admin_role(
    role_in: AdminRoleCreate,
    claims: Dict[str, Any] = Depends(require_admin_claims),
    db: AsyncSession = Depends(get_db_dependency),
):
    """
    Create a new internal AA admin role.
    Example roles:
      - GLOBAL_ATTR_ADMIN
      - ENTITLEMENT_ADMIN_VO1
      - SELF_SERVICE
    """
    logger.info(f"User {claims.get('sub')} creating admin role {role_in.name}")

    existing = await crud_admin_role.get_by_name(db, role_in.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Admin role '{role_in.name}' already exists",
        )

    role = await crud_admin_role.create(
        db,
        name=role_in.name,
        description=role_in.description,
    )
    return role


@router.post(
    "/roles/assign",
    response_model=AdminRoleAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assign_admin_role_to_user(
    body: AdminRoleAssignmentBase,
    claims: Dict[str, Any] = Depends(require_admin_claims),
    db: AsyncSession = Depends(get_db_dependency),
):
    """
    Assign an internal AA admin role to a user.

    Body:
      {
        "user_id": 123,
        "role_name": "GLOBAL_ATTR_ADMIN"
      }
    """
    logger.info(
        f"User {claims.get('sub')} assigning role {body.role_name} to user {body.user_id}"
    )

    user = await crud_user.get(db, id=body.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {body.user_id} not found",
        )

    role = await crud_admin_role.get_by_name(db, body.role_name)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Admin role '{body.role_name}' not found",
        )

    await crud_admin_role.assign_to_user(db, user=user, role=role)
    return AdminRoleAssignmentResponse(user_id=user.id, role_name=role.name)


@router.post(
    "/roles/revoke",
    response_model=AdminRoleAssignmentResponse,
)
async def revoke_admin_role_from_user(
    body: AdminRoleAssignmentBase,
    claims: Dict[str, Any] = Depends(require_admin_claims),
    db: AsyncSession = Depends(get_db_dependency),
):
    """
    Revoke an internal AA admin role from a user.
    """
    logger.info(
        f"User {claims.get('sub')} revoking role {body.role_name} from user {body.user_id}"
    )

    user = await crud_user.get(db, id=body.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {body.user_id} not found",
        )

    role = await crud_admin_role.get_by_name(db, body.role_name)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Admin role '{body.role_name}' not found",
        )

    await crud_admin_role.revoke_from_user(db, user=user, role=role)
    return AdminRoleAssignmentResponse(user_id=user.id, role_name=role.name)


# ---------------------------------------------------------------------------
# Attribute privilege rules endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/attribute-rules",
    response_model=AttributePrivilegeRuleList,
)
async def list_attribute_privilege_rules(
    claims: Dict[str, Any] = Depends(require_admin_claims),
    db: AsyncSession = Depends(get_db_dependency),
):
    """
    List all attribute privilege rules.

    These rules define:
      - which admin role is required
      - which CRUD action
      - which attribute key regex
      - optional value regex
      - target scope (self / any / ...)
    """
    logger.info(f"User {claims.get('sub')} listing attribute privilege rules")
    rules = await crud_attribute_privilege_rule.get_all(db)
    items: List[AttributePrivilegeRuleRead] = []
    for r in rules:
        items.append(
            AttributePrivilegeRuleRead(
                id=r.id,
                description=r.description,
                action=r.action,
                attribute_key_regex=r.attribute_key_regex,
                attribute_value_regex=r.attribute_value_regex,
                target_scope=r.target_scope,
                required_role_name=r.required_role.name,
            )
        )
    return AttributePrivilegeRuleList(items=items)


@router.post(
    "/attribute-rules",
    response_model=AttributePrivilegeRuleRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_attribute_privilege_rule(
    rule_in: AttributePrivilegeRuleCreate,
    claims: Dict[str, Any] = Depends(require_admin_claims),
    db: AsyncSession = Depends(get_db_dependency),
):
    """
    Create a new attribute privilege rule.

    Example:
      {
        "description": "Global admin can delete any attribute",
        "action": "delete",
        "attribute_key_regex": "^.*$",
        "attribute_value_regex": null,
        "target_scope": "any",
        "required_role_name": "GLOBAL_ATTR_ADMIN"
      }
    """
    logger.info(f"User {claims.get('sub')} creating attribute privilege rule")

    role = await crud_admin_role.get_by_name(db, rule_in.required_role_name)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Admin role '{rule_in.required_role_name}' not found",
        )

    rule = await crud_attribute_privilege_rule.create(
        db,
        description=rule_in.description,
        action=rule_in.action,
        attribute_key_regex=rule_in.attribute_key_regex,
        attribute_value_regex=rule_in.attribute_value_regex,
        target_scope=rule_in.target_scope,
        required_role=role,
    )

    return AttributePrivilegeRuleRead(
        id=rule.id,
        description=rule.description,
        action=rule.action,
        attribute_key_regex=rule.attribute_key_regex,
        attribute_value_regex=rule.attribute_value_regex,
        target_scope=rule.target_scope,
        required_role_name=role.name,
    )


@router.get(
    "/attribute-rules/{rule_id}",
    response_model=AttributePrivilegeRuleRead,
)
async def get_attribute_privilege_rule(
    rule_id: int,
    claims: Dict[str, Any] = Depends(require_admin_claims),
    db: AsyncSession = Depends(get_db_dependency),
):
    """
    Get one attribute privilege rule by ID.
    """
    logger.info(f"User {claims.get('sub')} fetching rule {rule_id}")

    rule = await crud_attribute_privilege_rule.get_by_id(db, rule_id)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule {rule_id} not found",
        )

    return AttributePrivilegeRuleRead(
        id=rule.id,
        description=rule.description,
        action=rule.action,
        attribute_key_regex=rule.attribute_key_regex,
        attribute_value_regex=rule.attribute_value_regex,
        target_scope=rule.target_scope,
        required_role_name=rule.required_role.name,
    )


@router.patch(
    "/attribute-rules/{rule_id}",
    response_model=AttributePrivilegeRuleRead,
)
async def update_attribute_privilege_rule(
    rule_id: int,
    rule_update: AttributePrivilegeRuleUpdate,
    claims: Dict[str, Any] = Depends(require_admin_claims),
    db: AsyncSession = Depends(get_db_dependency),
):
    """
    Partially update an existing attribute privilege rule.

    You can change description, action, key/value regex, target scope,
    and/or required role.
    """
    logger.info(f"User {claims.get('sub')} updating rule {rule_id}")

    rule = await crud_attribute_privilege_rule.get_by_id(db, rule_id)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule {rule_id} not found",
        )

    # Update fields if provided
    if rule_update.description is not None:
        rule.description = rule_update.description
    if rule_update.action is not None:
        rule.action = rule_update.action
    if rule_update.attribute_key_regex is not None:
        rule.attribute_key_regex = rule_update.attribute_key_regex
    if rule_update.attribute_value_regex is not None:
        rule.attribute_value_regex = rule_update.attribute_value_regex
    if rule_update.target_scope is not None:
        rule.target_scope = rule_update.target_scope
    if rule_update.required_role_name is not None:
        new_role = await crud_admin_role.get_by_name(db, rule_update.required_role_name)
        if not new_role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Admin role '{rule_update.required_role_name}' not found",
            )
        rule.required_role = new_role

    db.add(rule)
    await db.commit()
    await db.refresh(rule)

    return AttributePrivilegeRuleRead(
        id=rule.id,
        description=rule.description,
        action=rule.action,
        attribute_key_regex=rule.attribute_key_regex,
        attribute_value_regex=rule.attribute_value_regex,
        target_scope=rule.target_scope,
        required_role_name=rule.required_role.name,
    )


@router.delete(
    "/attribute-rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_attribute_privilege_rule(
    rule_id: int,
    claims: Dict[str, Any] = Depends(require_admin_claims),
    db: AsyncSession = Depends(get_db_dependency),
):
    """
    Delete an attribute privilege rule.
    """
    logger.info(f"User {claims.get('sub')} deleting rule {rule_id}")

    rule = await crud_attribute_privilege_rule.get_by_id(db, rule_id)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule {rule_id} not found",
        )

    await crud_attribute_privilege_rule.delete(db, rule_id=rule_id)
    return
