"""
Auth & Admin routes
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from pydantic import BaseModel

from api.auth.database import Database
from api.auth.utils import hash_password, verify_password, create_access_token, create_refresh_token, decode_refresh_token, generate_invite_code
from api.auth.schemas import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    UserInfo,
    UserDailyUsage,
    AdminUserUpdate,
    AdminSetVipRequest,
    AdminBalanceAdjustRequest,
    UserListResponse,
)
from api.auth.dependencies import (
    require_user,
    require_admin,
    check_daily_limit,
    get_current_user,
    get_sys_config,
    handle_invite_reward,
)
from api.auth.schemas import SysConfigResponse, SysConfigUpdateRequest

router = APIRouter(prefix="/auth", tags=["Authentication"])


# Column list for user queries (include vip_expires_at, phone, zs_balance, invite_code)
_USER_COLUMNS = "id, username, email, phone, role, daily_limit, vip_expires_at, zs_balance, invite_code, status, created_at"


def _row_to_userinfo(row: dict) -> UserInfo:
    """Convert a DB row dict to UserInfo."""
    return UserInfo(
        id=row["id"],
        username=row["username"],
        email=row.get("email"),
        phone=row.get("phone"),
        role=row["role"],
        daily_limit=row["daily_limit"],
        vip_expires_at=row.get("vip_expires_at"),
        zs_balance=row.get("zs_balance", 0),
        invite_code=row.get("invite_code"),
        status=row.get("status", 1),
        created_at=row["created_at"],
    )


@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterRequest):
    """Register a new user (default role: normal)"""
    # Check if username already exists
    existing = await Database.fetchone(
        "SELECT id FROM users WHERE username = %s", (body.username,)
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="用户名已存在",
        )

    # Check if email already exists
    if body.email:
        existing_email = await Database.fetchone(
            "SELECT id FROM users WHERE email = %s", (body.email,)
        )
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="邮箱已被使用",
            )

    # Create user
    password_hash = hash_password(body.password)
    user_invite_code = generate_invite_code()
    register_bonus = int(await get_sys_config("register_bonus", "600"))

    user_id = await Database.execute(
        "INSERT INTO users (username, password_hash, email, role, daily_limit, zs_balance, invite_code) "
        "VALUES (%s, %s, %s, 'normal', -1, %s, %s)",
        (body.username, password_hash, body.email, register_bonus, user_invite_code),
    )

    # Process invite reward
    if body.invite_code:
        await handle_invite_reward(body.invite_code, user_id)

    # Generate tokens
    access_token = create_access_token(user_id, "normal")
    refresh_token = create_refresh_token(user_id, "normal")

    # Fetch created user to get created_at & vip_expires_at
    row = await Database.fetchone(
        f"SELECT {_USER_COLUMNS} FROM users WHERE id = %s",
        (user_id,),
    )
    user_info = _row_to_userinfo(row) if row else UserInfo(
        id=user_id,
        username=body.username,
        email=body.email,
        role="normal",
        daily_limit=1,
        zs_balance=register_bonus,
        created_at=datetime.now(),
    )

    logger.info(f"New user registered: {body.username} (id={user_id}) zs_balance={register_bonus}")
    return TokenResponse(access_token=access_token, refresh_token=refresh_token, user=user_info)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    """Login with username and password"""
    row = await Database.fetchone(
        f"SELECT {_USER_COLUMNS}, password_hash, status FROM users WHERE username = %s",
        (body.username,),
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    if row["status"] == 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用，请联系管理员",
        )

    if not verify_password(body.password, row["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    access_token = create_access_token(row["id"], row["role"])
    refresh_token = create_refresh_token(row["id"], row["role"])
    user_info = _row_to_userinfo(row)

    logger.info(f"User logged in: {body.username}")
    return TokenResponse(access_token=access_token, refresh_token=refresh_token, user=user_info)


class LoginByPhoneRequest(BaseModel):
    """Login by phone request"""
    phone: str
    password: str


@router.post("/login-by-phone", response_model=TokenResponse)
async def login_by_phone(body: LoginByPhoneRequest):
    """Login with phone number and password"""
    row = await Database.fetchone(
        f"SELECT {_USER_COLUMNS}, password_hash, status FROM users WHERE phone = %s",
        (body.phone,),
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="手机号或密码错误",
        )

    if row["status"] == 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用，请联系管理员",
        )

    if not verify_password(body.password, row["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="手机号或密码错误",
        )

    access_token = create_access_token(row["id"], row["role"])
    refresh_token = create_refresh_token(row["id"], row["role"])
    user_info = _row_to_userinfo(row)

    logger.info(f"User logged in by phone: {body.phone} (user={row['username']})")
    return TokenResponse(access_token=access_token, refresh_token=refresh_token, user=user_info)


@router.get("/me", response_model=UserInfo)
async def get_me(user: UserInfo = Depends(require_user)):
    """Get current user info"""
    # Refresh from DB to get latest data
    row = await Database.fetchone(
        f"SELECT {_USER_COLUMNS} FROM users WHERE id = %s",
        (user.id,),
    )
    if row:
        return _row_to_userinfo(row)
    return user


class RefreshTokenRequest(BaseModel):
    refresh_token: str


@router.post("/refresh-token", response_model=TokenResponse)
async def refresh_token(body: RefreshTokenRequest):
    """Refresh access token using refresh token"""
    payload = decode_refresh_token(body.refresh_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌，请重新登录",
        )
    
    user_id = int(payload["sub"])
    role = payload["role"]
    
    # Check if user still exists and is active
    row = await Database.fetchone(
        f"SELECT {_USER_COLUMNS}, status FROM users WHERE id = %s",
        (user_id,),
    )
    
    if not row or row["status"] == 0:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已被禁用，请重新登录",
        )
    
    # Generate new tokens
    new_access_token = create_access_token(user_id, role)
    new_refresh_token = create_refresh_token(user_id, role)
    user_info = _row_to_userinfo(row)
    
    return TokenResponse(access_token=new_access_token, refresh_token=new_refresh_token, user=user_info)


@router.get("/usage", response_model=UserDailyUsage)
async def get_usage(user: UserInfo = Depends(require_user)):
    """Get current user's daily usage"""
    from datetime import date

    today = date.today()

    # SVIP/admin: unlimited
    if user.daily_limit == -1:
        return UserDailyUsage(used_today=0, remaining=-1, is_unlimited=True)

    usage = await Database.fetchone(
        "SELECT used_count FROM daily_usage WHERE user_id = %s AND date = %s",
        (user.id, today),
    )
    used_today = usage["used_count"] if usage else 0
    remaining = max(0, user.daily_limit - used_today)

    return UserDailyUsage(
        used_today=used_today,
        remaining=remaining,
        is_unlimited=False,
    )


# ====== Admin Routes ======


@router.get("/admin/users", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query("", description="Search by username or phone"),
    admin: UserInfo = Depends(require_admin),
):
    """List all users (admin only). Supports search by username or phone."""
    offset = (page - 1) * page_size

    if search:
        search_param = f"%{search}%"
        total_row = await Database.fetchone(
            "SELECT COUNT(*) as count FROM users WHERE username LIKE %s OR phone LIKE %s",
            (search_param, search_param),
        )
        total = total_row["count"] if total_row else 0

        rows = await Database.fetchall(
            f"SELECT {_USER_COLUMNS} FROM users WHERE username LIKE %s OR phone LIKE %s ORDER BY created_at DESC LIMIT %s OFFSET %s",
            (search_param, search_param, page_size, offset),
        )
    else:
        total_row = await Database.fetchone("SELECT COUNT(*) as count FROM users")
        total = total_row["count"] if total_row else 0

        rows = await Database.fetchall(
            f"SELECT {_USER_COLUMNS} FROM users ORDER BY created_at DESC LIMIT %s OFFSET %s",
            (page_size, offset),
        )

    users = [_row_to_userinfo(row) for row in rows]
    total_pages = max(1, (total + page_size - 1) // page_size)

    return UserListResponse(
        users=users,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.put("/admin/users/{user_id}", response_model=UserInfo)
async def update_user(
    user_id: int,
    body: AdminUserUpdate,
    admin: UserInfo = Depends(require_admin),
):
    """Update user role/status/limit (admin only)"""
    row = await Database.fetchone(
        f"SELECT {_USER_COLUMNS} FROM users WHERE id = %s",
        (user_id,),
    )
    if not row:
        raise HTTPException(status_code=404, detail="用户不存在")

    # Build update fields
    updates = []
    params = []
    if body.role is not None:
        updates.append("role = %s")
        params.append(body.role)
        if body.role == 'vip':
            updates.append("daily_limit = %s")
            params.append(10)
        elif body.role == 'svip':
            updates.append("daily_limit = %s")
            params.append(-1)
        elif body.daily_limit is not None:
            updates.append("daily_limit = %s")
            params.append(body.daily_limit)
    elif body.daily_limit is not None:
        updates.append("daily_limit = %s")
        params.append(body.daily_limit)
    if body.status is not None:
        updates.append("status = %s")
        params.append(body.status)
    if body.vip_expires_at is not None:
        updates.append("vip_expires_at = %s")
        params.append(body.vip_expires_at)

    if updates:
        params.append(user_id)
        await Database.execute(
            f"UPDATE users SET {', '.join(updates)} WHERE id = %s",
            params,
        )
        logger.info(f"Admin updated user {user_id}: {body.model_dump(exclude_none=True)}")

    row = await Database.fetchone(
        f"SELECT {_USER_COLUMNS} FROM users WHERE id = %s",
        (user_id,),
    )
    return _row_to_userinfo(row)


@router.post("/admin/set-vip", response_model=UserInfo)
async def set_vip(
    body: AdminSetVipRequest,
    admin: UserInfo = Depends(require_admin),
):
    """Set a user as VIP with expiry date (admin only)."""
    if body.phone:
        row = await Database.fetchone(
            f"SELECT {_USER_COLUMNS} FROM users WHERE phone = %s",
            (body.phone,),
        )
    else:
        row = await Database.fetchone(
            f"SELECT {_USER_COLUMNS} FROM users WHERE username = %s",
            (body.username,),
        )
    if not row:
        raise HTTPException(status_code=404, detail="用户不存在")

    user_id = row["id"]

    await Database.execute(
        "UPDATE users SET role = 'vip', vip_expires_at = %s, daily_limit = 10 WHERE id = %s",
        (body.vip_expires_at, user_id),
    )
    logger.info(f"Admin set VIP for user {row['username']} (id={user_id}) until {body.vip_expires_at}")

    row = await Database.fetchone(
        f"SELECT {_USER_COLUMNS} FROM users WHERE id = %s",
        (user_id,),
    )
    return _row_to_userinfo(row)


class AdminSetSvipRequest(BaseModel):
    """Admin set SVIP request"""
    username: str = ""
    phone: str = ""
    svip_expires_at: datetime


@router.post("/admin/set-svip", response_model=UserInfo)
async def set_svip(
    body: AdminSetSvipRequest,
    admin: UserInfo = Depends(require_admin),
):
    """Set a user as SVIP with expiry date (admin only)."""
    if body.phone:
        row = await Database.fetchone(
            f"SELECT {_USER_COLUMNS} FROM users WHERE phone = %s",
            (body.phone,),
        )
    else:
        row = await Database.fetchone(
            f"SELECT {_USER_COLUMNS} FROM users WHERE username = %s",
            (body.username,),
        )
    if not row:
        raise HTTPException(status_code=404, detail="用户不存在")

    user_id = row["id"]

    await Database.execute(
        "UPDATE users SET role = 'svip', vip_expires_at = %s, daily_limit = -1 WHERE id = %s",
        (body.svip_expires_at, user_id),
    )
    logger.info(f"Admin set SVIP for user {row['username']} (id={user_id}) until {body.svip_expires_at}")

    row = await Database.fetchone(
        f"SELECT {_USER_COLUMNS} FROM users WHERE id = %s",
        (user_id,),
    )
    return _row_to_userinfo(row)


@router.post("/admin/remove-vip/{user_id}", response_model=UserInfo)
async def remove_vip(
    user_id: int,
    admin: UserInfo = Depends(require_admin),
):
    """Remove VIP/SVIP status from a user, reset to normal (admin only)"""
    row = await Database.fetchone(
        f"SELECT {_USER_COLUMNS} FROM users WHERE id = %s",
        (user_id,),
    )
    if not row:
        raise HTTPException(status_code=404, detail="用户不存在")

    old_role = row["role"]

    await Database.execute(
        "UPDATE users SET role = 'normal', vip_expires_at = NULL, daily_limit = 1 WHERE id = %s",
        (user_id,),
    )
    logger.info(f"Admin removed {old_role.upper()} from user {row['username']} (id={user_id}), reset to normal")

    row = await Database.fetchone(
        f"SELECT {_USER_COLUMNS} FROM users WHERE id = %s",
        (user_id,),
    )
    return _row_to_userinfo(row)


@router.post("/admin/adjust-balance", response_model=UserInfo)
async def adjust_user_balance(
    body: AdminBalanceAdjustRequest,
    admin: UserInfo = Depends(require_admin),
):
    """管理员增减用户ZS余额（正数=增加，负数=减少），记录变更日志"""
    if body.change_amount == 0:
        raise HTTPException(status_code=400, detail="变动数量不能为0")

    # 获取目标用户
    row = await Database.fetchone(
        f"SELECT {_USER_COLUMNS} FROM users WHERE id = %s",
        (body.user_id,),
    )
    if not row:
        raise HTTPException(status_code=404, detail="用户不存在")

    balance_before = row.get("zs_balance", 0)
    balance_after = balance_before + body.change_amount
    if balance_after < 0:
        raise HTTPException(status_code=400, detail=f"余额不足，当前余额 {balance_before}，减少 {abs(body.change_amount)} 后余额为负数")

    # 更新余额
    await Database.execute(
        "UPDATE users SET zs_balance = %s WHERE id = %s",
        (balance_after, body.user_id),
    )

    # 记录变更日志
    await Database.execute(
        "INSERT INTO balance_change_log (user_id, admin_id, change_amount, balance_before, balance_after, reason) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (body.user_id, admin.id, body.change_amount, balance_before, balance_after, body.reason),
    )

    logger.info(
        f"Admin {admin.username}(id={admin.id}) adjusted balance for user {row['username']}(id={body.user_id}): "
        f"{balance_before} -> {balance_after} (change={body.change_amount}), reason: {body.reason}"
    )

    # 返回更新后的用户信息
    row = await Database.fetchone(
        f"SELECT {_USER_COLUMNS} FROM users WHERE id = %s",
        (body.user_id,),
    )
    return _row_to_userinfo(row)


# ====== 邀请信息接口 ======


@router.get("/invite-info")
async def get_invite_info(user: UserInfo = Depends(require_user)):
    """
    获取我的邀请信息
    """
    invite_bonus = int(await get_sys_config("invite_bonus", "200"))

    # 如果用户没有邀请码，自动生成并保存
    if not user.invite_code:
        user.invite_code = generate_invite_code()
        await Database.execute(
            "UPDATE users SET invite_code = %s WHERE id = %s",
            (user.invite_code, user.id),
        )

    # Count total invites
    count_row = await Database.fetchone(
        "SELECT COUNT(*) as cnt FROM invite_log WHERE inviter_id = %s",
        (user.id,),
    )
    total_invites = count_row["cnt"] if count_row else 0

    # Sum total reward
    reward_row = await Database.fetchone(
        "SELECT COALESCE(SUM(reward_zs), 0) as total FROM invite_log WHERE inviter_id = %s",
        (user.id,),
    )
    total_reward_zs = reward_row["total"] if reward_row else 0

    # Get invitee list
    invitees = await Database.fetchall(
        """SELECT u.username, il.created_at
           FROM invite_log il
           JOIN users u ON u.id = il.invitee_id
           WHERE il.inviter_id = %s
           ORDER BY il.created_at DESC
           LIMIT 50""",
        (user.id,),
    )

    invitee_list = [
        {"username": row["username"], "created_at": row["created_at"].isoformat() if hasattr(row["created_at"], 'isoformat') else str(row["created_at"])}
        for row in invitees
    ]

    return {
        "invite_code": user.invite_code or "",
        "invite_link": f"/register?invite={user.invite_code or ''}",
        "invite_bonus": invite_bonus,
        "total_invites": total_invites,
        "total_reward_zs": total_reward_zs,
        "invitees": invitee_list,
    }


# ====== 管理员系统配置接口 ======


@router.get("/admin/config", response_model=SysConfigResponse)
async def get_admin_config(admin: UserInfo = Depends(require_admin)):
    """获取系统配置（管理员）"""
    zs_per_second = await get_sys_config("zs_per_second", "5")
    exchange_rate = await get_sys_config("exchange_rate", "100")
    register_bonus = await get_sys_config("register_bonus", "600")
    min_recharge = await get_sys_config("min_recharge", "10")
    invite_bonus = await get_sys_config("invite_bonus", "200")
    vip_price = await get_sys_config("vip_price", "29")
    svip_price = await get_sys_config("svip_price", "89")
    vip_bonus_zs = await get_sys_config("vip_bonus_zs", "3900")
    svip_bonus_zs = await get_sys_config("svip_bonus_zs", "10000")
    vip_discount = await get_sys_config("vip_discount", "90")
    svip_discount = await get_sys_config("svip_discount", "80")
    vip_queue_priority = await get_sys_config("vip_queue_priority", "1")
    svip_queue_priority = await get_sys_config("svip_queue_priority", "2")

    return SysConfigResponse(
        zs_per_second=zs_per_second,
        exchange_rate=exchange_rate,
        register_bonus=register_bonus,
        min_recharge=min_recharge,
        invite_bonus=invite_bonus,
        vip_price=vip_price,
        svip_price=svip_price,
        vip_bonus_zs=vip_bonus_zs,
        svip_bonus_zs=svip_bonus_zs,
        vip_discount=vip_discount,
        svip_discount=svip_discount,
        vip_queue_priority=vip_queue_priority,
        svip_queue_priority=svip_queue_priority,
    )


@router.put("/admin/config/{config_key}")
async def update_admin_config(
    config_key: str,
    body: SysConfigUpdateRequest,
    admin: UserInfo = Depends(require_admin),
):
    """修改系统配置（管理员）
    可修改：zs_per_second, exchange_rate, register_bonus, invite_bonus, min_recharge,
            vip_price, svip_price, vip_bonus_zs, svip_bonus_zs, vip_discount, svip_discount
    """
    valid_keys = ["zs_per_second", "exchange_rate", "register_bonus", "invite_bonus", "min_recharge",
                  "vip_price", "svip_price", "vip_bonus_zs", "svip_bonus_zs", "vip_discount", "svip_discount",
                  "vip_queue_priority", "svip_queue_priority"]
    if config_key not in valid_keys:
        raise HTTPException(status_code=400, detail=f"无效的配置键，允许的值: {valid_keys}")

    await Database.execute(
        "UPDATE sys_config SET config_value = %s WHERE config_key = %s",
        (body.config_value, config_key),
    )
    logger.info(f"Admin updated config {config_key} = {body.config_value}")

    return {"success": True, "config_key": config_key, "config_value": body.config_value}
