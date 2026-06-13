"""
Auth & Admin routes
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger

from api.auth.database import Database
from api.auth.utils import hash_password, verify_password, create_access_token
from api.auth.schemas import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    UserInfo,
    UserDailyUsage,
    AdminUserUpdate,
    UserListResponse,
)
from api.auth.dependencies import (
    require_user,
    require_admin,
    check_daily_limit,
    get_current_user,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


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
    user_id = await Database.execute(
        "INSERT INTO users (username, password_hash, email, role, daily_limit) VALUES (%s, %s, %s, 'normal', 3)",
        (body.username, password_hash, body.email),
    )

    # Generate token
    token = create_access_token(user_id, "normal")

    # Fetch created user to get created_at
    row = await Database.fetchone(
        "SELECT id, username, email, role, daily_limit, created_at FROM users WHERE id = %s",
        (user_id,),
    )
    user_info = UserInfo(**row) if row else UserInfo(
        id=user_id,
        username=body.username,
        email=body.email,
        role="normal",
        daily_limit=3,
        created_at=datetime.now(),
    )

    logger.info(f"New user registered: {body.username} (id={user_id})")
    return TokenResponse(access_token=token, user=user_info)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    """Login with username and password"""
    row = await Database.fetchone(
        "SELECT id, username, email, role, daily_limit, created_at, password_hash, status FROM users WHERE username = %s",
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

    token = create_access_token(row["id"], row["role"])
    user_info = UserInfo(
        id=row["id"],
        username=row["username"],
        email=row["email"],
        role=row["role"],
        daily_limit=row["daily_limit"],
        created_at=row["created_at"],
    )

    logger.info(f"User logged in: {body.username}")
    return TokenResponse(access_token=token, user=user_info)


@router.get("/me", response_model=UserInfo)
async def get_me(user: UserInfo = Depends(require_user)):
    """Get current user info"""
    return user


@router.get("/usage", response_model=UserDailyUsage)
async def get_usage(user: UserInfo = Depends(require_user)):
    """Get current user's daily usage"""
    from datetime import date

    today = date.today()

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
    admin: UserInfo = Depends(require_admin),
):
    """List all users (admin only)"""
    offset = (page - 1) * page_size

    total_row = await Database.fetchone("SELECT COUNT(*) as count FROM users")
    total = total_row["count"] if total_row else 0

    rows = await Database.fetchall(
        "SELECT id, username, email, role, daily_limit, created_at FROM users ORDER BY created_at DESC LIMIT %s OFFSET %s",
        (page_size, offset),
    )

    users = [UserInfo(**row) for row in rows]
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
    # Check user exists
    row = await Database.fetchone(
        "SELECT id, username, email, role, daily_limit, created_at FROM users WHERE id = %s",
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
    if body.status is not None:
        updates.append("status = %s")
        params.append(body.status)
    if body.daily_limit is not None:
        updates.append("daily_limit = %s")
        params.append(body.daily_limit)

    if updates:
        params.append(user_id)
        await Database.execute(
            f"UPDATE users SET {', '.join(updates)} WHERE id = %s",
            params,
        )
        logger.info(f"Admin updated user {user_id}: {body.model_dump(exclude_none=True)}")

    # Return updated user
    row = await Database.fetchone(
        "SELECT id, username, email, role, daily_limit, created_at FROM users WHERE id = %s",
        (user_id,),
    )
    return UserInfo(**row)
