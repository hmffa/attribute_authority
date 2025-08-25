from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timedelta, timezone

import secrets
from ..models.invitation import Invitation
from ..schemas.invitation import InvitationCreate

class CRUDInvitation:
    @staticmethod
    async def create(db: AsyncSession, obj_in: InvitationCreate, creator_user_id: int) -> Invitation:
        """Create a new invitation"""
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=obj_in.expires_in_minutes)
        
        # Generate a unique hash
        invitation_hash = secrets.token_urlsafe(32)
        
        db_obj = Invitation(
            hash=invitation_hash,
            created_by_user_id=creator_user_id,
            invited_user_sub=obj_in.invited_user_sub,
            invited_user_iss=obj_in.invited_user_iss,
            group_key=obj_in.group_key,
            group_value=obj_in.group_value,
            max_uses=obj_in.max_uses,
            current_uses=0,
            expires_at=expires_at.isoformat(),
            created_at=now.isoformat(),
            status="active"
        )
        
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    @staticmethod
    async def get_by_hash(db: AsyncSession, invitation_hash: str) -> Optional[Invitation]:
        """Get invitation by hash"""
        query = select(Invitation).where(Invitation.hash == invitation_hash)
        result = await db.execute(query)
        return result.scalars().first()
    
    @staticmethod
    async def list_by_creator(db: AsyncSession, creator_user_id: int) -> List[Invitation]:
        """List all invitations created by a user"""
        query = select(Invitation).where(Invitation.created_by_user_id == creator_user_id)
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def use_invitation(db: AsyncSession, invitation: Invitation) -> Invitation:
        """Mark invitation as used or increment use count"""
        invitation.current_uses += 1
        
        # If max uses reached, mark as used
        if invitation.current_uses >= invitation.max_uses:
            invitation.status = "used"
            
        await db.commit()
        await db.refresh(invitation)
        return invitation
        
    @staticmethod
    async def check_invitation_valid(invitation: Optional[Invitation]) -> bool:
        """Check if an invitation is valid"""
        if not invitation:
            return False
            
        if invitation.status != "active":
            return False
            
        # Check expiration
        now = datetime.now(timezone.utc)
        expires_at = datetime.fromisoformat(invitation.expires_at)
        if now > expires_at:
            return False
            
        # Check usage limits
        if invitation.current_uses >= invitation.max_uses:
            return False
            
        return True

crud_invitation = CRUDInvitation()