from fastapi import APIRouter, Depends, Request, HTTPException, status, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_current_user_claims, get_db_dependency, optional_user_claims
from ...services.invitation_service import invitation_service
from ...crud.invitation import crud_invitation
from ...schemas.invitation import InvitationCreate, InvitationResponse, InvitationList, InvitationDetails
from ...core.logging_config import logger

router = APIRouter()

@router.post("/invitations", response_model=InvitationResponse)
async def create_invitation(
    invitation: InvitationCreate,
    claims: Dict[str, Any] = Depends(get_current_user_claims),
    db: AsyncSession = Depends(get_db_dependency())
):
    logger.info(f"User {claims.get('sub')} creating invitation")
    return await invitation_service.create_invitation(db, invitation, claims)

@router.get("/invitations", response_model=InvitationList)
async def list_invitations(
    claims: Dict[str, Any] = Depends(get_current_user_claims),
    db: AsyncSession = Depends(get_db_dependency())
):
    """List all invitations created by current user"""
    sub = claims.get("sub")
    iss = claims.get("iss")
    from ...crud.user import crud_user
    
    user = await crud_user.get_by_sub_and_iss(db, sub, iss)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    invitations = await crud_invitation.list_by_creator(db, user.id)
    return InvitationList(invitations=invitations)

@router.get("/invitations/{invitation_hash}/accept", response_class=HTMLResponse)
async def show_invitation_page(
    invitation_hash: str,
    request: Request,
    claims: Dict[str, Any] = Depends(optional_user_claims),
    db: AsyncSession = Depends(get_db_dependency())
):
    """Show invitation acceptance page (HTML)"""
    invitation = await crud_invitation.get_by_hash(db, invitation_hash)
    if not invitation:
        return HTMLResponse(content="<html><body><h1>Invalid invitation</h1></body></html>")
    
    # Check if invitation is valid
    is_valid = await crud_invitation.check_invitation_valid(invitation)
    if not is_valid:
        return HTMLResponse(content="<html><body><h1>This invitation has expired or already been used</h1></body></html>")
    
    # If user is not logged in, redirect to login page
    if not claims:
        login_url = f"/api/v1/auth/login?next=/api/v1/invitations/{invitation_hash}/accept"
        return RedirectResponse(url=login_url)
    
    # Show acceptance page
    return HTMLResponse(content=f"""
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
    """)

# @router.post("/invitations/{invitation_hash}/confirm")
# async def confirm_invitation(
#     invitation_hash: str,
#     action: str = Form(...),  # "accept" or "reject"
#     claims: Dict[str, Any] = Depends(get_current_user_claims),
#     db: AsyncSession = Depends(get_db_dependency())
# ):
#     """Process invitation acceptance or rejection"""
#     if action == "accept":
#         result = await invitation_service.accept_invitation(db, invitation_hash, claims)
#         return HTMLResponse(content=f"""
#         <html><body>
#             <h1>Invitation Accepted</h1>
#             <p>{result["message"]}</p>
#             <a href="/">Return to homepage</a>
#         </body></html>
#         """)
#     else:
#         return HTMLResponse(content="""
#         <html><body>
#             <h1>Invitation Rejected</h1>
#             <p>You have declined this invitation.</p>
#             <a href="/">Return to homepage</a>
#         </body></html>
#         """)