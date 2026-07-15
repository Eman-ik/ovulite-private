"""Organization and invitation endpoints."""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_organization, get_current_user, require_role
from app.database import get_db
from app.models.organization import Organization, OrganizationInvitation, OrganizationMembership
from app.models.user import User
from app.schemas.organization import (
    OrganizationInvitationCreate,
    OrganizationInvitationResponse,
    OrganizationMembershipResponse,
    OrganizationResponse,
)

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get("/me", response_model=OrganizationResponse)
def get_my_organization(
    organization: Organization = Depends(get_current_organization),
) -> Organization:
    return organization


@router.post(
    "/{organization_id}/invitations",
    response_model=OrganizationInvitationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("admin", "organization_admin"))],
)
def create_invitation(
    organization_id: int,
    payload: OrganizationInvitationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrganizationInvitation:
    if current_user.organization_id != organization_id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot manage invitations for another organization",
        )

    organization = db.query(Organization).filter(Organization.organization_id == organization_id).first()
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    invitation = OrganizationInvitation(
        organization_id=organization_id,
        email=payload.email,
        role=payload.role,
        invited_by_user_id=current_user.user_id,
        token=uuid4().hex,
        status="pending",
        expires_at=payload.expires_at,
        notes=payload.notes,
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    return invitation


@router.get(
    "/{organization_id}/invitations",
    response_model=list[OrganizationInvitationResponse],
    dependencies=[Depends(require_role("admin", "organization_admin"))],
)
def list_invitations(
    organization_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[OrganizationInvitation]:
    if current_user.organization_id != organization_id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot view invitations for another organization",
        )

    return (
        db.query(OrganizationInvitation)
        .filter(OrganizationInvitation.organization_id == organization_id)
        .order_by(OrganizationInvitation.created_at.desc())
        .all()
    )


@router.get(
    "/{organization_id}/members",
    response_model=list[OrganizationMembershipResponse],
    dependencies=[Depends(require_role("admin", "organization_admin"))],
)
def list_members(
    organization_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[OrganizationMembership]:
    if current_user.organization_id != organization_id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot view members for another organization",
        )

    return (
        db.query(OrganizationMembership)
        .filter(OrganizationMembership.organization_id == organization_id)
        .order_by(OrganizationMembership.created_at.asc())
        .all()
    )
