"""Organization and membership schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class OrganizationBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    slug: str = Field(..., min_length=2, max_length=120)
    organization_type: Optional[str] = Field(default=None, max_length=80)
    country: Optional[str] = Field(default=None, max_length=80)
    time_zone: Optional[str] = Field(default=None, max_length=80)
    primary_species: Optional[str] = Field(default=None, max_length=80)


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationResponse(OrganizationBase):
    organization_id: int
    active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrganizationMembershipResponse(BaseModel):
    membership_id: int
    organization_id: int
    user_id: int
    role: str
    status: str
    is_primary: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class OrganizationInvitationCreate(BaseModel):
    email: EmailStr
    role: str
    expires_at: datetime
    notes: Optional[str] = None


class OrganizationInvitationResponse(BaseModel):
    invitation_id: int
    organization_id: int
    email: EmailStr
    role: str
    invited_by_user_id: int
    token: str
    status: str
    expires_at: datetime
    accepted_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class OrganizationRegistrationRequest(BaseModel):
    organization: OrganizationCreate
    admin_username: str = Field(..., min_length=3, max_length=100)
    admin_password: str = Field(..., min_length=8, max_length=128)
    admin_full_name: Optional[str] = Field(default=None, max_length=200)
    admin_email: Optional[EmailStr] = None


class OrganizationRegistrationResponse(BaseModel):
    organization: OrganizationResponse
    user_id: int
    username: str
    role: str
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

