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


async def get_sys_config(key: str, default=None):
    """读取系统配置"""
    row = await Database.fetchone(
        "SELECT config_value FROM sys_config WHERE config_key = %s", (key,)
    )
    return row["config_value"] if row else default


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
        "SELECT id, username, email, phone, role, daily_limit, vip_expires_at, "
        "zs_balance, invite_code, created_at FROM users WHERE id = %s AND status = 1",
        (user_id,),
    )
    if not row:
        return None

    user = UserInfo(**row)

    # Auto-downgrade VIP if expired
    if user.role == 'vip' and user.vip_expires_at is not None:
        now = datetime.now()
        expires_at = user.vip_expires_at
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        if expires_at < now:
            await Database.execute(
                "UPDATE users SET role = 'normal', daily_limit = -1, vip_expires_at = NULL WHERE id = %s",
                (user_id,),
            )
            user.role = 'normal'
            user.daily_limit = -1
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
) -> UserInfo:
    """
    按量计费模式：ZS币就是限制，不限制每天次数。
    所有用户 daily_limit = -1（无限制），直接通过。
    """
    return user


async def increment_daily_usage(user_id: int):
    """按量计费模式：不限制次数，这个方法留空（保持接口兼容）"""
    pass


async def decrement_daily_usage(user_id: int):
    """按量计费模式：不限制次数，这个方法留空（保持接口兼容）"""
    pass


# ====== ZS币 扣费核心逻辑 ======


async def freeze_balance(user_id: int, estimated_seconds: int) -> tuple[bool, int, str]:
    """
    预冻结余额。
    返回 (成功?, 冻结金额, 消息)
    """
    zs_per_sec = int(await get_sys_config("zs_per_second", "5"))
    frozen = estimated_seconds * zs_per_sec  # 整数，无需 round
    
    affected = await Database.execute(
        "UPDATE users SET zs_balance = zs_balance - %s WHERE id = %s AND zs_balance >= %s",
        (frozen, user_id, frozen)
    )
    if affected > 0:
        return True, frozen, ""
    else:
        row = await Database.fetchone(
            "SELECT zs_balance FROM users WHERE id = %s", (user_id,)
        )
        balance = row["zs_balance"] if row else 0
        return False, 0, f"ZS币不足（当前 {balance}），需要 {frozen}，请充值"


async def settle_generation(task_id: str, user_id: int, frozen_zs: int,
                            actual_seconds: int, success: bool) -> dict:
    """
    结算生成任务：
    - 成功：按实际时长扣费，退还差额
    - 失败：全额退款
    
    Returns:
        {
            "deducted_zs": int,  # 实际扣除的ZS币
            "frozen_zs": int,    # 预冻结的ZS币
            "success": bool      # 是否成功
        }
    """
    if not success:
        await Database.execute(
            "UPDATE users SET zs_balance = zs_balance + %s WHERE id = %s",
            (frozen_zs, user_id)
        )
        await Database.execute(
            "UPDATE generation_log SET status = 'refunded', updated_at = NOW() "
            "WHERE task_id = %s", (task_id,)
        )
        return {"deducted_zs": 0, "frozen_zs": frozen_zs, "success": False}
    
    zs_per_sec = int(await get_sys_config("zs_per_second", "5"))
    actual_cost = actual_seconds * zs_per_sec
    refund = frozen_zs - actual_cost
    
    if refund > 0:
        await Database.execute(
            "UPDATE users SET zs_balance = zs_balance + %s WHERE id = %s",
            (refund, user_id)
        )
    elif refund < 0:
        affected = await Database.execute(
            "UPDATE users SET zs_balance = zs_balance + %s WHERE id = %s AND zs_balance >= %s",
            (refund, user_id, abs(refund))
        )
        if affected == 0:
            await Database.execute(
                "UPDATE generation_log SET status = 'abnormal', actual_seconds=%s, "
                "deducted_zs=%s, updated_at=NOW() WHERE task_id=%s",
                (actual_seconds, actual_cost, task_id)
            )
            return {"deducted_zs": 0, "frozen_zs": frozen_zs, "success": False}
    
    await Database.execute(
        "UPDATE generation_log SET actual_seconds=%s, deducted_zs=%s, "
        "status='deducted', updated_at=NOW() WHERE task_id=%s",
        (actual_seconds, actual_cost, task_id)
    )
    
    return {"deducted_zs": actual_cost, "frozen_zs": frozen_zs, "success": True}


async def handle_invite_reward(invite_code: str, new_user_id: int):
    """
    处理邀请注册奖励：
    1. 根据 invite_code 找到邀请人
    2. 给邀请人发放 ZS币 奖励
    3. 记录邀请日志
    """
    if not invite_code:
        return
    
    # 查找邀请人
    inviter = await Database.fetchone(
        "SELECT id, username FROM users WHERE invite_code = %s", (invite_code,)
    )
    if not inviter:
        return  # 邀请码无效，忽略
    
    inviter_id = inviter["id"]
    
    # 防止自邀
    if inviter_id == new_user_id:
        return
    
    # 读取奖励金额
    reward = int(await get_sys_config("invite_bonus", "200"))
    
    # 给邀请人发放奖励
    await Database.execute(
        "UPDATE users SET zs_balance = zs_balance + %s WHERE id = %s",
        (reward, inviter_id)
    )
    
    # 更新新用户的 invited_by
    await Database.execute(
        "UPDATE users SET invited_by = %s WHERE id = %s",
        (inviter_id, new_user_id)
    )
    
    # 记录邀请日志
    await Database.execute(
        "INSERT INTO invite_log (inviter_id, invitee_id, reward_zs) VALUES (%s, %s, %s)",
        (inviter_id, new_user_id, reward)
    )
    logger.info(f"Invite reward: inviter={inviter_id} got {reward} ZS for inviting user={new_user_id}")