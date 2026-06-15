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
    refresh_token: str
    token_type: str = "bearer"
    user: "UserInfo"


class UserInfo(BaseModel):
    """User info response"""
    id: int
    username: str
    email: Optional[str] = None
    phone: Optional[str] = None
    role: str
    daily_limit: int
    vip_expires_at: Optional[datetime] = None
    status: int = 1
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
    vip_expires_at: Optional[datetime] = None


class AdminSetVipRequest(BaseModel):
    """Admin set VIP request"""
    username: str = ""
    phone: str = ""
    vip_expires_at: datetime


class SendSmsCodeRequest(BaseModel):
    """Send SMS verification code request"""
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$", description="手机号")


class SendSmsCodeResponse(BaseModel):
    """Send SMS code response"""
    message: str = "验证码已发送"
    expire_seconds: int = 300


class RegisterByPhoneRequest(BaseModel):
    """Register by phone request"""
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$", description="手机号")
    code: str = Field(..., min_length=6, max_length=6, description="短信验证码")
    password: str = Field(..., min_length=6, max_length=128, description="密码")


class BindPhoneRequest(BaseModel):
    """Bind phone to existing account request"""
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$", description="手机号")
    code: str = Field(..., min_length=6, max_length=6, description="短信验证码")


class UserListResponse(BaseModel):
    """User list response"""
    users: List[UserInfo]
    total: int
    page: int
    page_size: int
    total_pages: int
