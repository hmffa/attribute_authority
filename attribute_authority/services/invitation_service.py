from typing import Dict, Any, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import os
from sqlalchemy.exc import IntegrityError

from ..crud.invitation import crud_invitation
from ..crud.user import crud_user
from ..schemas.user import UserCreate
from ..crud.user_attribute_value import crud_attribute
from ..schemas.invitation import InvitationCreate, InvitationResponse
from ..core.config import settings
from .email_service import send_invitation_email

class InvitationService:
    @staticmethod
    async def create_invitation(db: AsyncSession, obj_in: InvitationCreate, claims: Dict[str, Any]) -> InvitationResponse:
        """Create a new invitation and return details"""
        sub = claims.get("sub")
        iss = claims.get("iss")
        
        # Get user ID from claims
        user = await crud_user.get_by_sub_and_iss(db, sub, iss)
        if not user:
            user = await crud_user.create(db, UserCreate(sub=sub, iss=iss))
        
        # Create invitation
        invitation = await crud_invitation.create(db, obj_in, user.id)
        
        # Generate invitation URL
        # approve_url = f"{settings.PUBLIC_BASE_URL}/api/v1/invitations/{invitation.hash}/accept"
        # reject_url = f"{settings.PUBLIC_BASE_URL}/api/v1/invitations/{invitation.hash}/reject"
        invitation_url = f"{settings.PUBLIC_BASE_URL}/api/v1/invitations/{invitation.hash}"


        # NOTE Sending email notification feature is currently disabled

        # context = {
        #     "user_name": getattr(user, "name", "Sample User"),  # TODO add extra user information such as name, email, etc
        #     "admin_name": "Admin",  # TODO Replace with actual admin name when there is a separate table for that
        #     "group_name": invitation.group_value,
        #     "approve_url": approve_url,
        #     "reject_url": reject_url
        # }
        # template = render_template("user_invitation.html", context)

        # await send_invitation_email(
        #     to= getattr(user, "email", "hmffam@gmail.com"), # TODO replace this when user table is updated
        #     subject="Group Membership Request",
        #     body=template
        # )

        return InvitationResponse(
            hash=invitation.hash,
            invitation_url=invitation_url,
            expires_at_utc=invitation.expires_at,
            max_uses=invitation.max_uses
        )
    
    @staticmethod
    async def accept_invitation(db: AsyncSession, invitation_hash: str, claims: Dict[str, Any]) -> Dict[str, Any]:
        """Process invitation acceptance"""
        invitation = await crud_invitation.get_by_hash(db, invitation_hash)
        
        # Check if invitation is valid
        if not await crud_invitation.check_invitation_valid(invitation):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired invitation"
            )
        
        # Check if the invitation is specific to a user
        if invitation.invited_user_sub and invitation.invited_user_iss:
            sub = claims.get("sub")
            iss = claims.get("iss")
            
            if sub != invitation.invited_user_sub or iss != invitation.invited_user_iss:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="This invitation is for another user"
                )
        
        # Get current user
        sub = claims.get("sub")
        iss = claims.get("iss")
        user = await crud_user.get_by_sub_and_iss(db, sub, iss)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        

        group_key = invitation.group_key
        group_value = invitation.group_value
        try:
            # Add the attribute/group to the user
            await crud_attribute.create(
                db, 
                user_id=user.id,
                key=invitation.group_key,
                value=invitation.group_value
            )
        except IntegrityError:
            await db.rollback()
            return {
                "status": "info",
                "message": f"You are already a member of {group_value}",
                "group_key": group_key,
                "group_value": group_value
            }
        
        # Mark invitation as used
        await crud_invitation.use_invitation(db, invitation)

        # send email to the user
        # await send_email(
        #     to=user.email,
        #     subject="Invitation Accepted",
        #     body=f"You have been added to {invitation.group_value}"
        # )

        return {
            "status": "success",
            "message": f"You have been added to {invitation.group_value}",
            "group_key": invitation.group_key,
            "group_value": invitation.group_value
        }

invitation_service = InvitationService()