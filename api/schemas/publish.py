"""
Publishing API schemas

Schema definitions for the video publishing endpoints.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


# ============================================================================
# Start Publish
# ============================================================================

class PublishStartRequest(BaseModel):
    """发布启动请求"""
    platform: str = Field(..., description="目标平台：douyin/kuaishou/xiaohongshu/shipinhao")
    video_path: str = Field(..., description="视频文件路径")
    title: str = Field("", description="视频标题")
    text: str = Field("", description="文案内容")
    topics: List[str] = Field(default_factory=list, description="话题标签列表")
    portrait_cover: str = Field("", description="竖屏封面 (base64)")
    landscape_cover: str = Field("", description="横屏封面 (base64)")

    class Config:
        json_schema_extra = {
            "example": {
                "platform": "douyin",
                "video_path": "output/20260701/xxx.mp4",
                "title": "精彩视频",
                "text": "这是一个用AI生成的视频...",
                "topics": ["#AI技术", "#数字人"],
                "portrait_cover": "data:image/png;base64,...",
                "landscape_cover": "data:image/png;base64,...",
            }
        }


class PublishStartResponse(BaseModel):
    """发布启动响应"""
    success: bool = True
    session_id: str = Field(..., description="发布会话 ID")
    status: str = Field("pending", description="会话状态")
    message: str = Field("发布会话已创建", description="状态消息")


# ============================================================================
# Publish Status
# ============================================================================

class PublishStatusResponse(BaseModel):
    """发布状态查询响应"""
    success: bool = True
    session_id: str = Field(..., description="发布会话 ID")
    status: str = Field(..., description="会话状态")
    current_step: str = Field("", description="当前步骤")
    progress: float = Field(0.0, description="进度百分比 (0-100)")
    message: str = Field("", description="状态消息")
    platform_url: str = Field("", description="发布成功后的平台链接")
    error: str = Field("", description="错误信息")


# ============================================================================
# Cookie Management
# ============================================================================

class CookieSaveRequest(BaseModel):
    """Cookie 保存请求"""
    platform: str = Field(..., description="平台名称")
    cookies: List[dict] = Field(..., description="Playwright Cookie 列表")
    account_name: str = Field("", description="平台显示的用户名")
    expires_at: Optional[str] = Field(None, description="过期时间 (ISO 8601)")

    class Config:
        json_schema_extra = {
            "example": {
                "platform": "douyin",
                "cookies": [
                    {
                        "name": "sessionid",
                        "value": "xxx",
                        "domain": ".douyin.com",
                        "path": "/",
                    }
                ],
                "account_name": "张三",
                "expires_at": "2026-08-01T00:00:00Z",
            }
        }


class CookieSaveResponse(BaseModel):
    """Cookie 保存响应"""
    success: bool = True
    message: str = Field("Cookie 保存成功", description="状态消息")


# ============================================================================
# Account Management
# ============================================================================

class AccountInfo(BaseModel):
    """账号信息"""
    id: int = Field(..., description="记录 ID")
    platform: str = Field(..., description="平台名称")
    account_name: str = Field("", description="平台用户名")
    status: str = Field("active", description="状态：active/expired/revoked")
    last_used_at: Optional[str] = Field(None, description="最后使用时间")
    expires_at: Optional[str] = Field(None, description="Cookie 过期时间")


class AccountListResponse(BaseModel):
    """账号列表响应"""
    success: bool = True
    accounts: List[AccountInfo] = Field(default_factory=list, description="账号列表")


# ============================================================================
# Cancel Publish
# ============================================================================

class PublishCancelResponse(BaseModel):
    """取消发布响应"""
    success: bool = True
    message: str = Field("发布已取消", description="状态消息")