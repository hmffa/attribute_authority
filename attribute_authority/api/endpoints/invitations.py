"""Invitation endpoints."""
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_current_user_claims, optional_user_claims
from ...db.session import get_async_db
from ...schemas.invitation import InvitationCreate, InvitationList, InvitationResponse
from ...services import invitation as invitations
from ...services import user as users
from ...web.templating import templates

router = APIRouter()


@router.post("/invitations", response_model=InvitationResponse)
async def create_invitation(
    invitation: InvitationCreate,
    claims: Dict[str, Any] = Depends(get_current_user_claims),
    db: AsyncSession = Depends(get_async_db),
):
    """Create a new invitation."""
    return await invitations.create_invitation(db, invitation, claims)


@router.get("/invitations", response_model=InvitationList)
async def list_invitations(
    claims: Dict[str, Any] = Depends(get_current_user_claims),
    db: AsyncSession = Depends(get_async_db),
):
    """List all invitations created by current user."""
    sub = claims.get("sub")
    iss = claims.get("iss")

    user = await users.get_by_sub_and_iss(db, sub, iss)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    invitation_list = await invitations.list_by_creator(db, user.id)
    return InvitationList(invitations=invitation_list)


@router.get("/invitations/{invitation_hash}/accept", response_class=HTMLResponse)
async def show_invitation_accept_page(
    invitation_hash: str,
    request: Request,
    claims: Dict[str, Any] = Depends(optional_user_claims),
    db: AsyncSession = Depends(get_async_db),
):
    """Show invitation acceptance page (HTML)."""
    invitation = await invitations.get_by_hash(db, invitation_hash)
    if not invitation:
        return HTMLResponse(content="<html><body><h1>Invalid invitation</h1></body></html>")

    if not invitations.check_invitation_valid(invitation):
        return HTMLResponse(
            content="<html><body><h1>This invitation has expired or already been used</h1></body></html>"
        )

    if not claims:
        login_url = f"/api/v1/auth/login?next=/api/v1/invitations/{invitation_hash}/accept"
        return RedirectResponse(url=login_url)

    return HTMLResponse(
        content=f"""
    <html>
    <body>
        <h1>Invitation to join {invitation.group_value}</h1>
        <p>You've been invited to join this group. Would you like to accept?</p>
        <form action="/api/v1/invitations/{invitation_hash}/confirm" method="post">
            <button type="submit" name="action" value="accept">Accept</button>
            <button type="submit" name="action" value="reject">Reject</button>
        </form>
    </body>
    </html>
    """
    )


@router.post("/invitations/{invitation_hash}/confirm")
async def confirm_invitation(
    invitation_hash: str,
    request: Request,
    action: str = Form(...),
    claims: Dict[str, Any] = Depends(optional_user_claims),
    db: AsyncSession = Depends(get_async_db),
):
    """Process invitation acceptance or rejection."""
    if not claims:
        return RedirectResponse(
            url=f"/api/v1/invitations/{invitation_hash}", status_code=302
        )

    if action == "accept":
        result = await invitations.accept_invitation(db, invitation_hash, claims)
        if result["status"] == "info":
            title = "Already a Member"
        else:
            title = "Invitation Accepted"
        return templates.TemplateResponse(
            "result.html",
            {
                "request": request,
                "title": title,
                "message": result["message"],
                "success": True,
            },
        )
    else:
        return templates.TemplateResponse(
            "result.html",
            {
                "request": request,
                "title": "Invitation Rejected",
                "message": "You have declined this invitation.",
                "success": False,
            },
        )


@router.get("/invitations/{invitation_hash}", response_class=HTMLResponse)
async def show_invitation_page(
    invitation_hash: str,
    request: Request,
    claims: Dict[str, Any] = Depends(optional_user_claims),
    db: AsyncSession = Depends(get_async_db),
):
    """Show invitation page with QR code and details."""
    invitation = await invitations.get_by_hash(db, invitation_hash)
    if not invitation:
        return templates.TemplateResponse(
            "error.html", {"request": request, "message": "Invalid invitation"}
        )

    if not invitations.check_invitation_valid(invitation):
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "message": "This invitation has expired or already been used",
            },
        )

    if not claims:
        login_url = f"/api/v1/auth/login?next=/api/v1/invitations/{invitation_hash}"
        return RedirectResponse(url=login_url)

    expires_at = datetime.fromisoformat(invitation.expires_at)
    remaining_uses = invitation.max_uses - invitation.current_uses
    invitation_url = (
        f"{request.url.scheme}://{request.url.netloc}/api/v1/invitations/{invitation_hash}"
    )

    return templates.TemplateResponse(
        "invitation.html",
        {
            "request": request,
            "invitation": invitation,
            "invitation_url": invitation_url,
            "expiry_at": expires_at,
            "remaining_uses": remaining_uses,
        },
    )
