"""Invitation endpoints."""
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_current_user_claims
from ...db.session import get_async_db
from ...schemas.invitation import InvitationCreate, InvitationList, InvitationResponse
from ...services import invitation as invitations
from ...services import user as users

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


@router.delete("/invitations/{invitation_hash}")
async def revoke_invitation(
    invitation_hash: str,
    claims: Dict[str, Any] = Depends(get_current_user_claims),
    db: AsyncSession = Depends(get_async_db),
):
    """Revoke an invitation created by the current user."""
    sub = claims.get("sub")
    iss = claims.get("iss")
    user = await users.get_by_sub_and_iss(db, sub, iss)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    invitation = await invitations.revoke_invitation(
        db,
        invitation_hash=invitation_hash,
        actor_user_id=user.id,
    )
    return {
        "status": "success",
        "message": f"Invitation '{invitation.hash}' revoked",
    }
