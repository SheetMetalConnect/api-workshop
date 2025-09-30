from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List
from uuid import UUID


class ProfileBase(BaseModel):
    """Base schema for Profile

    Note: Profiles are managed by Supabase Auth.
    This API primarily reads profile data for authorization checks.
    Email validation is handled by Supabase during user signup.
    """

    # EmailStr validates email format - rejects "not-an-email", accepts "user@domain.com"
    # Optional means it can be None (null in database)
    email: Optional[str] = None

    full_name: Optional[str] = None
    role: Optional[str] = "operator"
    workplace_access: Optional[List[str]] = None


class ProfileCreate(ProfileBase):
    """Schema for creating a new Profile

    Usually called via Supabase trigger after user signup,
    not directly via API.
    """

    id: UUID  # Must match Supabase auth.users.id


class ProfileUpdate(BaseModel):
    """Schema for updating an existing Profile

    Used to update role and workplace_access for operators.
    """

    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    workplace_access: Optional[List[str]] = None


class Profile(ProfileBase):
    """Schema for reading Profile (includes all fields)"""

    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
