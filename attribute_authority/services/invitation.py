"""Invitation service - combines data access and business logic."""
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..models.invitation import Invitation
from ..schemas.invitation import InvitationCreate, InvitationResponse
from ..core.config import settings
from . import user as users
from . import attribute_definition as attributes
from . import user_attribute_value as user_attributes


# --- Data Access ---

async def get_by_hash(db: AsyncSession, invitation_hash: str) -> Optional[Invitation]:
    """Get invitation by hash."""
    result = await db.execute(
        select(Invitation).where(Invitation.hash == invitation_hash)
    )
    return result.scalars().first()


async def list_by_creator(db: AsyncSession, creator_user_id: int) -> List[Invitation]:
    """List all invitations created by a user."""
    result = await db.execute(
        select(Invitation).where(Invitation.created_by_user_id == creator_user_id)
    )
    return result.scalars().all()


async def create_invitation_record(
    db: AsyncSession, invitation_in: InvitationCreate, creator_user_id: int
) -> Invitation:
    """Create a new invitation record."""
    now = datetime.now(timezone.utc)
    invitation_hash = secrets.token_urlsafe(32)

    invitation = Invitation(
        hash=invitation_hash,
        created_by_user_id=creator_user_id,
        invited_user_sub=invitation_in.invited_user_sub,
        invited_user_iss=invitation_in.invited_user_iss,
        group_key=invitation_in.group_key,
        group_value=invitation_in.group_value,
        max_uses=invitation_in.max_uses,
        current_uses=0,
        expires_at=invitation_in.expires_at,
        created_at=now.isoformat(),
        status="active",
    )

    db.add(invitation)
    await db.commit()
    await db.refresh(invitation)
    return invitation


async def use_invitation_record(
    db: AsyncSession, invitation: Invitation
) -> Invitation:
    """Mark invitation as used or increment use count."""
    invitation.current_uses += 1

    if invitation.current_uses >= invitation.max_uses:
        invitation.status = "used"

    await db.commit()
    await db.refresh(invitation)
    return invitation


def check_invitation_valid(invitation: Optional[Invitation]) -> bool:
    """Check if an invitation is valid."""
    if not invitation:
        return False

    if invitation.status != "active":
        return False

    now = datetime.now(timezone.utc)
    expires_at = datetime.fromisoformat(invitation.expires_at)
    if now > expires_at:
        return False

    if invitation.current_uses >= invitation.max_uses:
        return False

    return True


# --- Business Logic ---

async def create_invitation(
    db: AsyncSession, invitation_in: InvitationCreate, claims: Dict[str, Any]
) -> InvitationResponse:
    """Create a new invitation and return details."""
    # Validate attribute exists
    attr_def = await attributes.get_by_name(db, invitation_in.group_key)
    if not attr_def:
        raise HTTPException(
            status_code=400,
            detail=f"Attribute definition '{invitation_in.group_key}' not found.",
        )

    # Get/Create Creator User
    sub = claims.get("sub")
    iss = claims.get("iss")
    user = await users.get_or_create(db, sub, iss)

    # Create Invitation
    invitation = await create_invitation_record(db, invitation_in, user.id)

    invitation_url = f"{settings.PUBLIC_BASE_URL}/api/v1/invitations/{invitation.hash}"

    return InvitationResponse(
        hash=invitation.hash,
        invitation_url=invitation_url,
        expires_at_utc=invitation.expires_at,
        max_uses=invitation.max_uses,
    )


async def accept_invitation(
    db: AsyncSession, invitation_hash: str, claims: Dict[str, Any]
) -> Dict[str, Any]:
    """Process invitation acceptance."""
    invitation = await get_by_hash(db, invitation_hash)

    if not check_invitation_valid(invitation):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired invitation",
        )

    # Check Targeted Invite
    if invitation.invited_user_sub and invitation.invited_user_iss:
        sub = claims.get("sub")
        iss = claims.get("iss")
        if sub != invitation.invited_user_sub or iss != invitation.invited_user_iss:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This invitation is for another user",
            )

    # Resolve User
    sub = claims.get("sub")
    iss = claims.get("iss")
    user = await users.get_or_create(db, sub, iss)

    # Apply Attribute (bypassing normal auth since invitation is the authorization)
    try:
        attribute = await attributes.get_or_404(db, invitation.group_key)
        await user_attributes.create_value(
            db,
            user_id=user.id,
            attribute_id=attribute.id,
            value=invitation.group_value,
        )
    except HTTPException as e:
        if e.status_code == 400 and "already has a value" in e.detail:
            return {
                "status": "info",
                "message": f"You are already a member of {invitation.group_value}",
                "group_key": invitation.group_key,
                "group_value": invitation.group_value,
            }
        raise e

    # Consume Invite
    await use_invitation_record(db, invitation)

    return {
        "status": "success",
        "message": f"You have been added to {invitation.group_value}",
        "group_key": invitation.group_key,
        "group_value": invitation.group_value,
    }