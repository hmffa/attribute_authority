"""Server-rendered UI routes."""

from datetime import datetime
import json
from math import ceil
from typing import Any, Dict, Optional
from urllib.parse import quote, urlencode

from authlib.integrations.starlette_client import OAuth, OAuthError
from flaat import access_tokens
from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from ..api.dependencies import optional_user_claims
from ..core.config import settings
from ..core.logging_config import logger
from ..db.session import get_async_db
from ..models.privilege import PrivilegeAction
from ..models.user import User
from ..schemas.attribute import AttributeCreate, AttributeUpdate
from ..schemas.invitation import InvitationCreate
from ..schemas.privilege import PrivilegeCreate, PrivilegeDelegate, PrivilegeUpdate
from ..schemas.user import UserUpdate
from ..services import attribute_definition as attributes
from ..services import authorization
from ..services import invitation as invitation_service
from ..services import privilege as privileges
from ..services import user as users
from ..services import user_attribute_value as user_attributes
from .templating import templates

router = APIRouter(include_in_schema=False)

oauth = OAuth()
providers: list[str] = []

for provider_name, provider in settings.OIDC_PROVIDERS.items():
    provider_url = provider["url"]
    client_id = provider["client_id"]
    client_secret = provider["client_secret"]

    if client_id and client_secret:
        oauth.register(
            name=provider_name,
            server_metadata_url=f"{provider_url}/.well-known/openid-configuration",
            client_id=client_id,
            client_secret=client_secret,
            client_kwargs={"scope": "openid email profile"},
        )
        providers.append(provider_name)


def _sanitize_next_url(next_url: Optional[str]) -> str:
    if not next_url:
        return "/"
    if not next_url.startswith("/") or next_url.startswith("//"):
        return "/"
    return next_url


def _display_claims(claims: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not claims:
        return None
    return {
        "sub": claims.get("sub"),
        "iss": claims.get("iss"),
        "name": claims.get("name") or claims.get("preferred_username"),
        "email": claims.get("email"),
    }


def _provider_links(next_url: str) -> list[dict[str, str]]:
    safe_next = quote(next_url, safe="")
    return [
        {
            "name": provider_name,
            "href": f"/auth/authorize/{provider_name}?next={safe_next}",
        }
        for provider_name in providers
    ]


def _page_context(
    request: Request,
    claims: Optional[Dict[str, Any]] = None,
    *,
    active_nav: str = "",
    page_message: Optional[str] = None,
    page_error: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    context = {
        "request": request,
        "claims": _display_claims(claims),
        "active_nav": active_nav,
        "page_message": page_message,
        "page_error": page_error,
    }
    context.update(kwargs)
    return context


def _notice_redirect(
    path: str,
    *,
    message: Optional[str] = None,
    error: Optional[str] = None,
) -> RedirectResponse:
    params: dict[str, str] = {}
    if message:
        params["message"] = message
    if error:
        params["error"] = error
    url = f"{path}?{urlencode(params)}" if params else path
    return RedirectResponse(url=url, status_code=303)


def _login_redirect(request: Request) -> RedirectResponse:
    next_url = request.url.path
    if request.url.query:
        next_url = f"{next_url}?{request.url.query}"
    return RedirectResponse(
        url=f"/login?next={quote(_sanitize_next_url(next_url), safe='')}",
        status_code=302,
    )


def _detail_text(exc: HTTPException) -> str:
    if isinstance(exc.detail, str):
        return exc.detail
    try:
        return json.dumps(exc.detail)
    except TypeError:
        return str(exc.detail)


def _optional_int(raw_value: Optional[str]) -> Optional[int]:
    if raw_value is None:
        return None
    value = raw_value.strip()
    if not value:
        return None
    return int(value)


def _optional_text(raw_value: Optional[str]) -> Optional[str]:
    if raw_value is None:
        return None
    value = raw_value.strip()
    return value or None


def _parse_target_restriction(raw_value: Optional[str]) -> Optional[list[dict[str, Any]]]:
    value = _optional_text(raw_value)
    if value is None:
        return None
    parsed = json.loads(value)
    if not isinstance(parsed, list):
        raise ValueError("Target restriction must be a JSON array.")
    if not all(isinstance(item, dict) for item in parsed):
        raise ValueError("Target restriction must contain JSON objects only.")
    return parsed


async def _resolve_actor(
    db: AsyncSession,
    claims: Optional[Dict[str, Any]],
) -> Optional[User]:
    if not claims:
        return None
    sub = claims.get("sub")
    iss = claims.get("iss")
    if not sub or not iss:
        return None
    user = await users.get_by_sub_and_iss(db, sub, iss)
    if user:
        return user
    return await users.get_or_create(db, sub=sub, iss=iss)


async def _require_actor(
    request: Request,
    db: AsyncSession,
    claims: Optional[Dict[str, Any]],
) -> tuple[Optional[User], Optional[RedirectResponse]]:
    actor = await _resolve_actor(db, claims)
    if not actor:
        return None, _login_redirect(request)
    return actor, None


async def _require_privilege_page(
    request: Request,
    db: AsyncSession,
    claims: Optional[Dict[str, Any]],
    action: PrivilegeAction,
    *,
    active_nav: str,
    target_user: Optional[User] = None,
    attribute_id: Optional[int] = None,
) -> tuple[Optional[User], Optional[RedirectResponse], Optional[Any]]:
    actor, redirect = await _require_actor(request, db, claims)
    if redirect:
        return None, redirect, None
    assert actor is not None

    is_allowed = await authorization.has_privilege(
        db,
        actor=actor,
        action=action,
        target_user=target_user,
        attribute_id=attribute_id,
    )
    if is_allowed:
        return actor, None, None

    error_page = templates.TemplateResponse(
        "error.html",
        _page_context(
            request,
            claims,
            active_nav=active_nav,
            message=f"You do not have permission to perform {action.value}.",
        ),
        status_code=403,
    )
    return actor, None, error_page


async def _visible_attributes_for_target(
    db: AsyncSession,
    actor: User,
    target_user: User,
) -> dict[str, list[dict[str, Any]]]:
    if actor.id == target_user.id:
        return await user_attributes.get_user_attributes_by_user_id(db, target_user.id)

    visible: dict[str, list[dict[str, Any]]] = {}
    for attr_value in target_user.attribute_values:
        is_allowed = await authorization.has_privilege(
            db,
            actor=actor,
            action=PrivilegeAction.READ_VALUE,
            target_user=target_user,
            attribute_id=attr_value.attribute_id,
            value=attr_value.value,
        )
        if not is_allowed:
            continue

        attr_name = attr_value.attribute_definition.name
        visible.setdefault(attr_name, []).append(
            {"id": attr_value.id, "value": attr_value.value}
        )
    return visible


def _invitation_url(request: Request, invitation_hash: str) -> str:
    return f"{request.url.scheme}://{request.url.netloc}/invitations/{invitation_hash}"


@router.get("/")
async def dashboard(
    request: Request,
    claims: Optional[Dict[str, Any]] = Depends(optional_user_claims),
    db: AsyncSession = Depends(get_async_db),
):
    actor = await _resolve_actor(db, claims)
    cards = [
        {
            "title": "My Attributes",
            "description": "Review your issued attributes and entitlements.",
            "href": "/me/attributes",
            "icon": "bi bi-person-badge",
        },
        {
            "title": "Users",
            "description": "Browse the user directory and inspect attribute visibility.",
            "href": "/admin/users",
            "icon": "bi bi-people",
        },
        {
            "title": "Definitions",
            "description": "Manage attribute definitions with Bootstrap-based admin forms.",
            "href": "/admin/attributes",
            "icon": "bi bi-diagram-3",
        },
        {
            "title": "Privileges",
            "description": "Grant, delegate, and review authorization scopes.",
            "href": "/admin/privileges",
            "icon": "bi bi-shield-lock",
        },
        {
            "title": "Invitations",
            "description": "Create invite links and manage their lifecycle.",
            "href": "/invitations/manage",
            "icon": "bi bi-envelope-paper",
        },
        {
            "title": "API Docs",
            "description": "Inspect the generated OpenAPI document and interactive docs.",
            "href": "/docs",
            "icon": "bi bi-file-earmark-code",
        },
    ]

    stats = None
    if actor:
        my_attributes = await user_attributes.get_user_attributes(db, actor.sub, actor.iss)
        my_invitations = await invitation_service.list_by_creator(db, actor.id)
        stats = {
            "attribute_count": sum(len(values) for values in my_attributes.values()),
            "group_count": len(my_attributes),
            "invitation_count": len(my_invitations),
        }

    return templates.TemplateResponse(
        "dashboard.html",
        _page_context(
            request,
            claims,
            active_nav="dashboard",
            cards=cards,
            stats=stats,
            provider_links=_provider_links("/me/attributes"),
        ),
    )


@router.get("/privacy")
async def privacy_page(
    request: Request,
    claims: Optional[Dict[str, Any]] = Depends(optional_user_claims),
):
    return templates.TemplateResponse(
        "privacy.html",
        _page_context(request, claims, active_nav="privacy"),
    )


@router.get("/login")
async def login_page(
    request: Request,
    next: Optional[str] = Query(None),
    claims: Optional[Dict[str, Any]] = Depends(optional_user_claims),
):
    redirect_target = _sanitize_next_url(next)
    if claims:
        return RedirectResponse(url=redirect_target, status_code=302)

    return templates.TemplateResponse(
        "login.html",
        _page_context(
            request,
            claims,
            active_nav="login",
            provider_links=_provider_links(redirect_target),
            next_url=redirect_target,
        ),
    )


@router.get("/auth/authorize/{provider}")
async def authorize(
    request: Request,
    provider: str,
    next: Optional[str] = Query("/"),
):
    redirect_uri = f"{settings.PUBLIC_BASE_URL}/auth/callback/{provider}"
    request.session["next_url"] = _sanitize_next_url(next)

    client = oauth.create_client(provider)
    if not client:
        return templates.TemplateResponse(
            "error.html",
            _page_context(
                request,
                active_nav="login",
                message=f"Provider '{provider}' is not configured.",
            ),
            status_code=400,
        )

    return await client.authorize_redirect(request, redirect_uri)


@router.get("/auth/callback/{provider}")
async def oidc_callback(
    request: Request,
    provider: str,
    db: AsyncSession = Depends(get_async_db),
):
    try:
        client = oauth.create_client(provider)
        if not client:
            return templates.TemplateResponse(
                "error.html",
                _page_context(
                    request,
                    active_nav="login",
                    message=f"Provider '{provider}' is not configured.",
                ),
                status_code=400,
            )

        token_response = await client.authorize_access_token(request)
        id_token = token_response.get("id_token")
        if not id_token:
            logger.error("Missing ID token")
            return templates.TemplateResponse(
                "error.html",
                _page_context(
                    request,
                    active_nav="login",
                    message="Authentication failed because the provider did not return an ID token.",
                ),
                status_code=400,
            )

        claims = access_tokens.get_access_token_info(id_token, verify=False).body
        sub = claims.get("sub")
        iss = claims.get("iss")
        if not sub or not iss:
            logger.error("Missing required claims in token")
            return templates.TemplateResponse(
                "error.html",
                _page_context(
                    request,
                    active_nav="login",
                    message="Authentication failed because the provider response was incomplete.",
                ),
                status_code=400,
            )

        user = await users.get_or_create(db, sub=sub, iss=iss)
        profile_update = UserUpdate(
            name=claims.get("name") or claims.get("preferred_username"),
            email=claims.get("email"),
        )
        if profile_update.name or profile_update.email:
            user = await users.update(db, user, profile_update)

        request.session["id_token"] = id_token
        redirect_url = _sanitize_next_url(request.session.get("next_url", "/"))
        return RedirectResponse(url=redirect_url, status_code=302)
    except OAuthError as exc:
        logger.error("OAuth error: %s", exc.error)
        return templates.TemplateResponse(
            "error.html",
            _page_context(
                request,
                active_nav="login",
                message=exc.description or "Authentication failed.",
            ),
            status_code=400,
        )
    except Exception as exc:  # pragma: no cover - defensive path
        logger.error("Error during OIDC callback: %s", exc, exc_info=True)
        return templates.TemplateResponse(
            "error.html",
            _page_context(
                request,
                active_nav="login",
                message="Could not complete login. Please try again.",
            ),
            status_code=400,
        )


@router.get("/logout")
async def logout(
    request: Request,
    claims: Optional[Dict[str, Any]] = Depends(optional_user_claims),
):
    request.session.clear()
    return templates.TemplateResponse(
        "logout_success.html",
        _page_context(request, claims, active_nav="logout"),
    )


@router.get("/me/attributes")
async def my_attributes_page(
    request: Request,
    message: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    claims: Optional[Dict[str, Any]] = Depends(optional_user_claims),
    db: AsyncSession = Depends(get_async_db),
):
    actor, redirect = await _require_actor(request, db, claims)
    if redirect:
        return redirect
    assert actor is not None

    my_attributes = await user_attributes.get_user_attributes(db, actor.sub, actor.iss)
    return templates.TemplateResponse(
        "user_attributes.html",
        _page_context(
            request,
            claims,
            active_nav="attributes-self",
            page_message=message,
            page_error=error,
            attributes=my_attributes,
        ),
    )


@router.get("/admin/users")
async def admin_users_page(
    request: Request,
    page: int = Query(1, ge=1),
    message: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    claims: Optional[Dict[str, Any]] = Depends(optional_user_claims),
    db: AsyncSession = Depends(get_async_db),
):
    actor, redirect = await _require_actor(request, db, claims)
    if redirect:
        return redirect

    per_page = 10
    result = await users.list_users_paginated(db, page=page, per_page=per_page)
    total_users = result["total"]
    page_count = max(1, ceil(total_users / per_page))
    return templates.TemplateResponse(
        "users.html",
        _page_context(
            request,
            claims,
            active_nav="users",
            page_message=message,
            page_error=error,
            users=result["items"],
            pagination={
                "page": page,
                "per_page": per_page,
                "total": total_users,
                "page_count": page_count,
                "has_prev": page > 1,
                "has_next": page < page_count,
            },
        ),
    )


@router.get("/admin/users/{user_id}/attributes")
async def admin_user_attributes_page(
    user_id: int,
    request: Request,
    claims: Optional[Dict[str, Any]] = Depends(optional_user_claims),
    db: AsyncSession = Depends(get_async_db),
):
    actor, redirect = await _require_actor(request, db, claims)
    if redirect:
        return redirect
    assert actor is not None

    target_user = await users.get_by_id(db, user_id)
    if not target_user:
        return templates.TemplateResponse(
            "error.html",
            _page_context(
                request,
                claims,
                active_nav="users",
                message="The requested user could not be found.",
            ),
            status_code=404,
        )

    visible_attributes = await _visible_attributes_for_target(db, actor, target_user)
    return templates.TemplateResponse(
        "admin_user_attributes.html",
        _page_context(
            request,
            claims,
            active_nav="users",
            target_user=target_user,
            attributes=visible_attributes,
        ),
    )


@router.get("/admin/attributes")
async def admin_attributes_page(
    request: Request,
    message: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    claims: Optional[Dict[str, Any]] = Depends(optional_user_claims),
    db: AsyncSession = Depends(get_async_db),
):
    _, redirect, error_page = await _require_privilege_page(
        request,
        db,
        claims,
        PrivilegeAction.READ_ATTR,
        active_nav="attribute-definitions",
    )
    if redirect:
        return redirect
    if error_page:
        return error_page

    attribute_list = await attributes.get_all(db)
    return templates.TemplateResponse(
        "admin_attributes.html",
        _page_context(
            request,
            claims,
            active_nav="attribute-definitions",
            page_message=message,
            page_error=error,
            attribute_definitions=attribute_list,
        ),
    )


@router.post("/admin/attributes")
async def create_attribute_page_action(
    request: Request,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    value_restriction: Optional[str] = Form(None),
    is_multivalue: bool = Form(False),
    enabled: bool = Form(False),
    claims: Optional[Dict[str, Any]] = Depends(optional_user_claims),
    db: AsyncSession = Depends(get_async_db),
):
    _, redirect, error_page = await _require_privilege_page(
        request,
        db,
        claims,
        PrivilegeAction.CREATE_ATTR,
        active_nav="attribute-definitions",
    )
    if redirect:
        return redirect
    if error_page:
        return error_page

    try:
        await attributes.create(
            db,
            AttributeCreate(
                name=name.strip(),
                description=_optional_text(description),
                value_restriction=_optional_text(value_restriction),
                is_multivalue=is_multivalue,
                enabled=enabled,
            ),
        )
    except HTTPException as exc:
        return _notice_redirect(
            "/admin/attributes",
            error=_detail_text(exc),
        )

    return _notice_redirect(
        "/admin/attributes",
        message=f"Attribute '{name.strip()}' created.",
    )


@router.get("/admin/attributes/{attribute_id}/edit")
async def edit_attribute_page(
    attribute_id: int,
    request: Request,
    message: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    claims: Optional[Dict[str, Any]] = Depends(optional_user_claims),
    db: AsyncSession = Depends(get_async_db),
):
    _, redirect, error_page = await _require_privilege_page(
        request,
        db,
        claims,
        PrivilegeAction.READ_ATTR,
        active_nav="attribute-definitions",
    )
    if redirect:
        return redirect
    if error_page:
        return error_page

    attribute = await attributes.get_by_id(db, attribute_id)
    if not attribute:
        return templates.TemplateResponse(
            "error.html",
            _page_context(
                request,
                claims,
                active_nav="attribute-definitions",
                message="The requested attribute definition could not be found.",
            ),
            status_code=404,
        )

    return templates.TemplateResponse(
        "admin_attribute_edit.html",
        _page_context(
            request,
            claims,
            active_nav="attribute-definitions",
            page_message=message,
            page_error=error,
            attribute_definition=attribute,
        ),
    )


@router.post("/admin/attributes/{attribute_id}/edit")
async def edit_attribute_page_action(
    attribute_id: int,
    request: Request,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    value_restriction: Optional[str] = Form(None),
    is_multivalue: bool = Form(False),
    enabled: bool = Form(False),
    claims: Optional[Dict[str, Any]] = Depends(optional_user_claims),
    db: AsyncSession = Depends(get_async_db),
):
    _, redirect, error_page = await _require_privilege_page(
        request,
        db,
        claims,
        PrivilegeAction.UPDATE_ATTR,
        active_nav="attribute-definitions",
    )
    if redirect:
        return redirect
    if error_page:
        return error_page

    try:
        await attributes.update(
            db,
            attribute_id=attribute_id,
            attr_in=AttributeUpdate(
                name=name.strip(),
                description=_optional_text(description),
                value_restriction=_optional_text(value_restriction),
                is_multivalue=is_multivalue,
                enabled=enabled,
            ),
        )
    except HTTPException as exc:
        return _notice_redirect(
            f"/admin/attributes/{attribute_id}/edit",
            error=_detail_text(exc),
        )

    return _notice_redirect(
        f"/admin/attributes/{attribute_id}/edit",
        message="Attribute definition updated.",
    )


@router.post("/admin/attributes/{attribute_id}/delete")
async def delete_attribute_page_action(
    attribute_id: int,
    request: Request,
    claims: Optional[Dict[str, Any]] = Depends(optional_user_claims),
    db: AsyncSession = Depends(get_async_db),
):
    _, redirect, error_page = await _require_privilege_page(
        request,
        db,
        claims,
        PrivilegeAction.DELETE_ATTR,
        active_nav="attribute-definitions",
    )
    if redirect:
        return redirect
    if error_page:
        return error_page

    try:
        await attributes.delete(db, attribute_id)
    except HTTPException as exc:
        return _notice_redirect("/admin/attributes", error=_detail_text(exc))
    return _notice_redirect("/admin/attributes", message="Attribute definition deleted.")


@router.get("/admin/privileges")
async def admin_privileges_page(
    request: Request,
    message: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    claims: Optional[Dict[str, Any]] = Depends(optional_user_claims),
    db: AsyncSession = Depends(get_async_db),
):
    _, redirect, error_page = await _require_privilege_page(
        request,
        db,
        claims,
        PrivilegeAction.ASSIGN_PRIVILEGE,
        active_nav="privileges",
    )
    if redirect:
        return redirect
    if error_page:
        return error_page

    all_privileges = await privileges.get_all(db)
    all_users = await users.get_all(db)
    attribute_list = await attributes.get_all(db)
    return templates.TemplateResponse(
        "admin_privileges.html",
        _page_context(
            request,
            claims,
            active_nav="privileges",
            page_message=message,
            page_error=error,
            privilege_entries=all_privileges,
            user_options=all_users,
            attribute_options=attribute_list,
            actions=list(PrivilegeAction),
        ),
    )


@router.post("/admin/privileges/grant")
async def grant_privilege_page_action(
    request: Request,
    grantee_user_id: int = Form(...),
    action: PrivilegeAction = Form(...),
    attribute_id: Optional[str] = Form(None),
    value_restriction: Optional[str] = Form(None),
    target_restriction: Optional[str] = Form(None),
    is_delegable: bool = Form(False),
    claims: Optional[Dict[str, Any]] = Depends(optional_user_claims),
    db: AsyncSession = Depends(get_async_db),
):
    _, redirect, error_page = await _require_privilege_page(
        request,
        db,
        claims,
        PrivilegeAction.ASSIGN_PRIVILEGE,
        active_nav="privileges",
    )
    if redirect:
        return redirect
    if error_page:
        return error_page

    try:
        target_scope = _parse_target_restriction(target_restriction)
        await privileges.assign_privilege_by_id(
            db,
            grantee_user_id=grantee_user_id,
            action=action,
            attribute_id=_optional_int(attribute_id),
            value_restriction=_optional_text(value_restriction),
            target_restriction=target_scope,
            is_delegable=is_delegable,
        )
    except ValueError as exc:
        return _notice_redirect("/admin/privileges", error=str(exc))
    except HTTPException as exc:
        return _notice_redirect("/admin/privileges", error=_detail_text(exc))

    return _notice_redirect("/admin/privileges", message="Privilege granted.")


@router.post("/admin/privileges/delegate")
async def delegate_privilege_page_action(
    request: Request,
    grantee_user_id: int = Form(...),
    action: PrivilegeAction = Form(...),
    attribute_id: Optional[str] = Form(None),
    value_restriction: Optional[str] = Form(None),
    target_restriction: Optional[str] = Form(None),
    is_delegable: bool = Form(False),
    claims: Optional[Dict[str, Any]] = Depends(optional_user_claims),
    db: AsyncSession = Depends(get_async_db),
):
    actor, redirect = await _require_actor(request, db, claims)
    if redirect:
        return redirect
    assert actor is not None

    try:
        target_scope = _parse_target_restriction(target_restriction)
        await privileges.delegate_privilege(
            db,
            delegator=actor,
            delegation_request=PrivilegeDelegate(
                grantee_user_id=grantee_user_id,
                action=action,
                attribute_id=_optional_int(attribute_id),
                value_restriction=_optional_text(value_restriction),
                target_restriction=target_scope,
                is_delegable=is_delegable,
            ),
        )
    except ValueError as exc:
        return _notice_redirect("/admin/privileges", error=str(exc))
    except HTTPException as exc:
        return _notice_redirect("/admin/privileges", error=_detail_text(exc))

    return _notice_redirect("/admin/privileges", message="Privilege delegated.")


@router.get("/admin/privileges/{privilege_id}/edit")
async def edit_privilege_page(
    privilege_id: int,
    request: Request,
    message: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    claims: Optional[Dict[str, Any]] = Depends(optional_user_claims),
    db: AsyncSession = Depends(get_async_db),
):
    _, redirect, error_page = await _require_privilege_page(
        request,
        db,
        claims,
        PrivilegeAction.ASSIGN_PRIVILEGE,
        active_nav="privileges",
    )
    if redirect:
        return redirect
    if error_page:
        return error_page

    privilege = await privileges.get_by_id(db, privilege_id)
    if not privilege:
        return templates.TemplateResponse(
            "error.html",
            _page_context(
                request,
                claims,
                active_nav="privileges",
                message="The requested privilege could not be found.",
            ),
            status_code=404,
        )

    return templates.TemplateResponse(
        "admin_privilege_edit.html",
        _page_context(
            request,
            claims,
            active_nav="privileges",
            page_message=message,
            page_error=error,
            privilege_entry=privilege,
            user_options=await users.get_all(db),
            attribute_options=await attributes.get_all(db),
            actions=list(PrivilegeAction),
        ),
    )


@router.post("/admin/privileges/{privilege_id}/edit")
async def edit_privilege_page_action(
    privilege_id: int,
    request: Request,
    action: PrivilegeAction = Form(...),
    attribute_id: Optional[str] = Form(None),
    value_restriction: Optional[str] = Form(None),
    target_restriction: Optional[str] = Form(None),
    is_delegable: bool = Form(False),
    claims: Optional[Dict[str, Any]] = Depends(optional_user_claims),
    db: AsyncSession = Depends(get_async_db),
):
    _, redirect, error_page = await _require_privilege_page(
        request,
        db,
        claims,
        PrivilegeAction.ASSIGN_PRIVILEGE,
        active_nav="privileges",
    )
    if redirect:
        return redirect
    if error_page:
        return error_page

    try:
        target_scope = _parse_target_restriction(target_restriction)
        await privileges.update_privilege(
            db,
            privilege_id=privilege_id,
            privilege_in=PrivilegeUpdate(
                action=action,
                attribute_id=_optional_int(attribute_id),
                value_restriction=_optional_text(value_restriction),
                target_restriction=target_scope,
                is_delegable=is_delegable,
            ),
        )
    except ValueError as exc:
        return _notice_redirect(f"/admin/privileges/{privilege_id}/edit", error=str(exc))
    except HTTPException as exc:
        return _notice_redirect(
            f"/admin/privileges/{privilege_id}/edit",
            error=_detail_text(exc),
        )

    return _notice_redirect(
        f"/admin/privileges/{privilege_id}/edit",
        message="Privilege updated.",
    )


@router.post("/admin/privileges/{privilege_id}/delete")
async def delete_privilege_page_action(
    privilege_id: int,
    request: Request,
    claims: Optional[Dict[str, Any]] = Depends(optional_user_claims),
    db: AsyncSession = Depends(get_async_db),
):
    _, redirect, error_page = await _require_privilege_page(
        request,
        db,
        claims,
        PrivilegeAction.ASSIGN_PRIVILEGE,
        active_nav="privileges",
    )
    if redirect:
        return redirect
    if error_page:
        return error_page

    try:
        await privileges.delete(db, privilege_id)
    except HTTPException as exc:
        return _notice_redirect("/admin/privileges", error=_detail_text(exc))
    return _notice_redirect("/admin/privileges", message="Privilege deleted.")


@router.get("/invitations/manage")
async def invitations_manage_page(
    request: Request,
    message: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    claims: Optional[Dict[str, Any]] = Depends(optional_user_claims),
    db: AsyncSession = Depends(get_async_db),
):
    actor, redirect = await _require_actor(request, db, claims)
    if redirect:
        return redirect
    assert actor is not None

    invitation_rows = []
    for invitation in await invitation_service.list_by_creator(db, actor.id):
        invitation_rows.append(
            {
                "record": invitation,
                "invitation_url": _invitation_url(request, invitation.hash),
                "remaining_uses": max(invitation.max_uses - invitation.current_uses, 0),
                "is_valid": invitation_service.check_invitation_valid(invitation),
            }
        )

    attribute_options = [attr for attr in await attributes.get_all(db) if attr.enabled]
    return templates.TemplateResponse(
        "manage_invitations.html",
        _page_context(
            request,
            claims,
            active_nav="invitations",
            page_message=message,
            page_error=error,
            invitation_rows=invitation_rows,
            attribute_options=attribute_options,
        ),
    )


@router.post("/invitations/manage")
async def create_invitation_page_action(
    request: Request,
    group_key: str = Form(...),
    group_value: str = Form(...),
    max_uses: int = Form(1),
    expires_in_seconds: int = Form(86400),
    invited_user_sub: Optional[str] = Form(None),
    invited_user_iss: Optional[str] = Form(None),
    claims: Optional[Dict[str, Any]] = Depends(optional_user_claims),
    db: AsyncSession = Depends(get_async_db),
):
    actor, redirect = await _require_actor(request, db, claims)
    if redirect:
        return redirect
    assert actor is not None

    try:
        await invitation_service.create_invitation(
            db,
            InvitationCreate(
                group_key=group_key.strip(),
                group_value=group_value.strip(),
                invited_user_sub=_optional_text(invited_user_sub),
                invited_user_iss=_optional_text(invited_user_iss),
                max_uses=max_uses,
                expires_in_seconds=expires_in_seconds,
            ),
            claims,
        )
    except ValidationError as exc:
        return _notice_redirect("/invitations/manage", error=str(exc))
    except HTTPException as exc:
        return _notice_redirect("/invitations/manage", error=_detail_text(exc))

    return _notice_redirect("/invitations/manage", message="Invitation created.")


@router.post("/invitations/{invitation_hash}/revoke")
async def revoke_invitation_page_action(
    invitation_hash: str,
    request: Request,
    claims: Optional[Dict[str, Any]] = Depends(optional_user_claims),
    db: AsyncSession = Depends(get_async_db),
):
    actor, redirect = await _require_actor(request, db, claims)
    if redirect:
        return redirect
    assert actor is not None

    try:
        await invitation_service.revoke_invitation(db, invitation_hash, actor.id)
    except HTTPException as exc:
        return _notice_redirect("/invitations/manage", error=_detail_text(exc))
    return _notice_redirect("/invitations/manage", message="Invitation revoked.")


@router.get("/invitations/{invitation_hash}")
async def invitation_page(
    invitation_hash: str,
    request: Request,
    claims: Optional[Dict[str, Any]] = Depends(optional_user_claims),
    db: AsyncSession = Depends(get_async_db),
):
    invitation = await invitation_service.get_by_hash(db, invitation_hash)
    if not invitation:
        return templates.TemplateResponse(
            "error.html",
            _page_context(
                request,
                claims,
                active_nav="invitations",
                message="This invitation does not exist.",
            ),
            status_code=404,
        )

    if not invitation_service.check_invitation_valid(invitation):
        return templates.TemplateResponse(
            "error.html",
            _page_context(
                request,
                claims,
                active_nav="invitations",
                message="This invitation has expired or is no longer active.",
            ),
            status_code=410,
        )

    if not claims:
        return _login_redirect(request)

    return templates.TemplateResponse(
        "invitation.html",
        _page_context(
            request,
            claims,
            active_nav="invitations",
            invitation=invitation,
            invitation_url=_invitation_url(request, invitation_hash),
            expiry_at=datetime.fromisoformat(invitation.expires_at),
            remaining_uses=max(invitation.max_uses - invitation.current_uses, 0),
        ),
    )


@router.get("/invitations/{invitation_hash}/accept")
async def invitation_accept_page(
    invitation_hash: str,
    request: Request,
    claims: Optional[Dict[str, Any]] = Depends(optional_user_claims),
    db: AsyncSession = Depends(get_async_db),
):
    invitation = await invitation_service.get_by_hash(db, invitation_hash)
    if not invitation:
        return templates.TemplateResponse(
            "error.html",
            _page_context(
                request,
                claims,
                active_nav="invitations",
                message="This invitation does not exist.",
            ),
            status_code=404,
        )

    if not invitation_service.check_invitation_valid(invitation):
        return templates.TemplateResponse(
            "error.html",
            _page_context(
                request,
                claims,
                active_nav="invitations",
                message="This invitation has expired or is no longer active.",
            ),
            status_code=410,
        )

    if not claims:
        return _login_redirect(request)

    return templates.TemplateResponse(
        "invitation_accept.html",
        _page_context(
            request,
            claims,
            active_nav="invitations",
            invitation=invitation,
            invitation_hash=invitation_hash,
        ),
    )


@router.post("/invitations/{invitation_hash}/confirm")
async def confirm_invitation_page_action(
    invitation_hash: str,
    request: Request,
    action: str = Form(...),
    claims: Optional[Dict[str, Any]] = Depends(optional_user_claims),
    db: AsyncSession = Depends(get_async_db),
):
    actor, redirect = await _require_actor(request, db, claims)
    if redirect:
        return redirect
    assert actor is not None

    if action == "accept":
        try:
            result = await invitation_service.accept_invitation(db, invitation_hash, claims or {})
        except HTTPException as exc:
            return templates.TemplateResponse(
                "error.html",
                _page_context(
                    request,
                    claims,
                    active_nav="invitations",
                    message=_detail_text(exc),
                ),
                status_code=exc.status_code,
            )

        title = "Invitation Accepted"
        if result["status"] == "info":
            title = "Already a Member"
        return templates.TemplateResponse(
            "result.html",
            _page_context(
                request,
                claims,
                active_nav="invitations",
                title=title,
                message=result["message"],
                success=True,
            ),
        )

    return templates.TemplateResponse(
        "result.html",
        _page_context(
            request,
            claims,
            active_nav="invitations",
            title="Invitation Rejected",
            message="You have declined this invitation.",
            success=False,
        ),
    )