"""
Pixelle-Video Publisher Module

Browser automation engine for publishing videos to Chinese short-video platforms
(Douyin, Kuaishou, Xiaohongshu, Shipinhao / WeChat Channels).

This module uses Playwright to simulate human operations for:
- Logging into platforms via QR code scanning
- Uploading videos
- Filling in titles, descriptions, and hashtags
- Setting covers
- Clicking publish button
"""

from pixelle_video.services.publisher.stealth import (
    create_stealth_context,
    STEALTH_SCRIPT,
)
from pixelle_video.services.publisher.cookie_manager import CookieManager
from pixelle_video.services.publisher.browser_pool import BrowserPool
from pixelle_video.services.publisher.session_manager import (
    SessionManager,
    PublishSession,
)
from pixelle_video.services.publisher.publisher_base import BasePublisher

__all__ = [
    "create_stealth_context",
    "STEALTH_SCRIPT",
    "CookieManager",
    "BrowserPool",
    "SessionManager",
    "PublishSession",
    "BasePublisher",
]