"""
Auth dependencies for FastAPI
"""

from typing import Optional
from datetime import datetime
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from loguru import logger

from api.auth.utils import decode_access_token
from api.auth.database import Database
from api.auth.schemas import UserInfo, UserDailyUsage

# HTTP Bearer token scheme
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[UserInfo]:
    """
    Get current user from JWT token.
    Returns None if not authenticated (optional auth).
    """
    if credentials is None:
        return None

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        return None

    user_id = int(payload.get("sub", 0))
    if not user_id:
        return None

    row = await Database.fetchone(
        "SELECT id, username, email, role, daily_limit, vip_expires_at, created_at FROM users WHERE id = %s AND status = 1",
        (user_id,),
    )
    if not row:
        return None

    user = UserInfo(**row)

    # Auto-downgrade VIP if expired
    if user.role == 'vip' and user.vip_expires_at is not None:
        now = datetime.now()
        # vip_expires_at might be a string from DB, ensure it's datetime
        expires_at = user.vip_expires_at
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        if expires_at < now:
            # VIP expired, downgrade to normal
            await Database.execute(
                "UPDATE users SET role = 'normal', daily_limit = 3, vip_expires_at = NULL WHERE id = %s",
                (user_id,),
            )
            user.role = 'normal'
            user.daily_limit = 3
            user.vip_expires_at = None
            logger.info(f"User {user.username} (id={user_id}) VIP expired, auto-downgraded to normal")

    return user


async def require_user(
    user: Optional[UserInfo] = Depends(get_current_user),
) -> UserInfo:
    """
    Require authenticated user.
    Raises 401 if not authenticated.
    """
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def require_admin(
    user: UserInfo = Depends(require_user),
) -> UserInfo:
    """
    Require admin role.
    Raises 403 if not admin.
    """
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    return user


async def check_daily_limit(
    user: UserInfo = Depends(require_user),
) -> tuple[UserInfo, UserDailyUsage]:
    """
    Check if user has exceeded daily generation limit.
    VIP users (daily_limit = -1) have unlimited access.
    Raises 429 if limit exceeded.
    """
    from datetime import date

    today = date.today()

    # VIP: unlimited
    if user.daily_limit == -1:
        return user, UserDailyUsage(used_today=0, remaining=-1, is_unlimited=True)

    # Get today's usage count
    usage = await Database.fetchone(
        "SELECT count FROM daily_usage WHERE user_id = %s AND date = %s",
        (user.id, today),
    )
    used_today = usage["count"] if usage else 0
    remaining = max(0, user.daily_limit - used_today)

    if remaining <= 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"今日生成次数已用完（上限 {user.daily_limit} 次），请明天再试或升级为 VIP",
        )

    return user, UserDailyUsage(
        used_today=used_today,
        remaining=remaining,
        is_unlimited=False,
    )


async def increment_daily_usage(user_id: int):
    """Increment daily usage counter for user"""
    from datetime import date

    today = date.today()
    await Database.execute(
        """INSERT INTO daily_usage (user_id, date, count)
           VALUES (%s, %s, 1)
           ON DUPLICATE KEY UPDATE count = count + 1""",
        (user_id, today),
    )