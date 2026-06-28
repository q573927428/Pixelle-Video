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
    invite_code: Optional[str] = Field(None, max_length=16, description="邀请码（可选）")


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
    zs_balance: int = 0
    invite_code: Optional[str] = None
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
    role: Optional[str] = Field(None, pattern="^(vip|svip|normal|admin)$")
    status: Optional[int] = Field(None, ge=0, le=1)
    daily_limit: Optional[int] = Field(None, ge=-1)
    vip_expires_at: Optional[datetime] = None


class AdminBalanceAdjustRequest(BaseModel):
    """Admin adjust user ZS balance request（只能增减，不能直接设置）"""
    user_id: int = Field(..., description="目标用户ID")
    change_amount: int = Field(..., description="变动数量（正数=增加，负数=减少）")
    reason: str = Field("", max_length=500, description="变动原因")


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
    invite_code: Optional[str] = Field(None, max_length=16, description="邀请码（可选）")


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


# ====== ZS币 & 充值相关 ======

class RechargeCreateRequest(BaseModel):
    """充值请求"""
    amount_rmb: float = Field(..., ge=1, description="充值金额（元人民币）")


class RechargeCreateResponse(BaseModel):
    """充值响应"""
    order_no: str
    amount_rmb: float
    amount_zs: int
    code_url: Optional[str] = None
    status: str = "pending"


class BalanceResponse(BaseModel):
    """余额响应"""
    zs_balance: int
    zs_per_second: int
    exchange_rate: int


class RechargeRecord(BaseModel):
    """充值记录"""
    order_no: str
    amount_rmb: float
    amount_zs: int
    status: str
    paid_at: Optional[datetime] = None
    created_at: datetime


class RechargeRecordsResponse(BaseModel):
    """充值记录列表响应"""
    records: list[RechargeRecord]
    total: int
    page: int
    page_size: int
    total_pages: int


class InviteInfoResponse(BaseModel):
    """邀请信息响应"""
    invite_code: str
    invite_link: str
    invite_bonus: int
    total_invites: int
    total_reward_zs: int
    invitees: list[dict]


class SysConfigResponse(BaseModel):
    """系统配置响应"""
    zs_per_second: str
    exchange_rate: str
    register_bonus: str
    min_recharge: str
    invite_bonus: str
    # VIP/SVIP 套餐配置
    vip_price: str = "29"
    svip_price: str = "89"
    vip_bonus_zs: str = "3900"
    svip_bonus_zs: str = "10000"
    vip_discount: str = "90"
    svip_discount: str = "80"
    vip_queue_priority: str = "1"
    svip_queue_priority: str = "2"


class SysConfigUpdateRequest(BaseModel):
    """系统配置更新请求"""
    config_value: str = Field(..., description="配置值")