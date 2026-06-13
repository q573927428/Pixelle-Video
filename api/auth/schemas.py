"""
Pydantic schemas for auth endpoints
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    """User registration request"""
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    password: str = Field(..., min_length=6, max_length=128, description="Password")
    email: Optional[str] = Field(None, max_length=100, description="Email")


class LoginRequest(BaseModel):
    """User login request"""
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")


class TokenResponse(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"
    user: "UserInfo"


class UserInfo(BaseModel):
    """User info response"""
    id: int
    username: str
    email: Optional[str] = None
    role: str
    daily_limit: int
    created_at: datetime

    class Config:
        from_attributes = True


class UserDailyUsage(BaseModel):
    """User daily usage info"""
    used_today: int
    remaining: int
    is_unlimited: bool


class AdminUserUpdate(BaseModel):
    """Admin user update request"""
    role: Optional[str] = Field(None, pattern="^(vip|normal|admin)$")
    status: Optional[int] = Field(None, ge=0, le=1)
    daily_limit: Optional[int] = Field(None, ge=-1)


class UserListResponse(BaseModel):
    """User list response"""
    users: List[UserInfo]
    total: int
    page: int
    page_size: int
    total_pages: int
