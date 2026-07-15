"""User-related Pydantic schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    """Schema for creating a new user."""

    username: str
    password: str
    role: str = "viewer"
    organization_id: Optional[int] = None
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None


class UserResponse(BaseModel):
    """Public user data returned by the API (never includes password_hash)."""

    user_id: int
    organization_id: Optional[int] = None
    username: str
    role: Optional[str]
    full_name: Optional[str]
    email: Optional[str]
    active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserInDB(UserResponse):
    """Internal schema that includes the password hash (never returned to client)."""

    password_hash: str
