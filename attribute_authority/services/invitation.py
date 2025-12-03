from typing import Dict, Any, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import os

from ..crud.invitation import crud_invitation
from ..crud.user import crud_user
from ..crud.attribute_definition import crud_attribute_definition
from ..schemas.user import UserCreate
from ..schemas.invitation import InvitationCreate, InvitationResponse
from ..services.user_attribute_value import user_attribute_value_service
from ..core.config import settings
# from .email import send_invitation_email # Uncomment when email is ready

class InvitationService:
    @staticmethod
    async def create_invitation(
        db: AsyncSession, 
        obj_in: InvitationCreate, 
        claims: Dict[str, Any]
    ) -> InvitationResponse:
        """Create a new invitation and return details"""
        
        # 1. Validation: Ensure the attribute actually exists!
        # We don't want to invite users to a non-existent attribute.
        attr_def = await crud_attribute_definition.get_by_name(db, obj_in.group_key)
        if not attr_def:
            raise HTTPException(
                status_code=400, 
                detail=f"Attribute definition '{obj_in.group_key}' not found."
            )

        # 2. Get/Create Creator User
        sub = claims.get("sub")
        iss = claims.get("iss")
        user = await crud_user.get_by_sub_and_iss(db, sub, iss)
        if not user:
            user = await crud_user.create(db, UserCreate(sub=sub, iss=iss))
        
        # 3. Create Invitation
        invitation = await crud_invitation.create(db, obj_in, user.id)
        
        invitation_url = f"{settings.PUBLIC_BASE_URL}/api/v1/invitations/{invitation.hash}"

        # TODO: Trigger Email Service here
        
        return InvitationResponse(
            hash=invitation.hash,
            invitation_url=invitation_url,
            expires_at_utc=invitation.expires_at,
            max_uses=invitation.max_uses
        )
    
    @staticmethod
    async def accept_invitation(
        db: AsyncSession, 
        invitation_hash: str, 
        claims: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process invitation acceptance"""
        invitation = await crud_invitation.get_by_hash(db, invitation_hash)
        
        # 1. Check validity
        if not await crud_invitation.check_invitation_valid(invitation):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired invitation"
            )
        
        # 2. Check Targeted Invite (optional security)
        if invitation.invited_user_sub and invitation.invited_user_iss:
            sub = claims.get("sub")
            iss = claims.get("iss")
            if sub != invitation.invited_user_sub or iss != invitation.invited_user_iss:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="This invitation is for another user"
                )
        
        # 3. Resolve User
        sub = claims.get("sub")
        iss = claims.get("iss")
        user = await crud_user.get_by_sub_and_iss(db, sub, iss)
        if not user:
            user = await crud_user.create(db, UserCreate(sub=sub, iss=iss))
        
        # 4. Apply Attribute using the SERVICE (Not CRUD)
        # This handles the lookup: group_key (String) -> attribute_id (Int)
        # It also checks Regex rules and Multi-value constraints.
        try:
            await user_attribute_value_service.add_value(
                db, 
                target_user_id=user.id,
                attribute_name=invitation.group_key,
                value=invitation.group_value,
                source="invitation"
            )
        except HTTPException as e:
            # Handle duplicates gracefully (e.g., user clicked link twice)
            if e.status_code == 400 and "already has a value" in e.detail:
                 return {
                    "status": "info",
                    "message": f"You are already a member of {invitation.group_value}",
                    "group_key": invitation.group_key,
                    "group_value": invitation.group_value
                }
            raise e
        
        # 5. Consume Invite
        await crud_invitation.use_invitation(db, invitation)

        return {
            "status": "success",
            "message": f"You have been added to {invitation.group_value}",
            "group_key": invitation.group_key,
            "group_value": invitation.group_value
        }

invitation_service = InvitationService()