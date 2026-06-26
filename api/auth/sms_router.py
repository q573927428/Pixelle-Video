"""
SMS verification code routes
"""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from api.auth.database import Database
from api.auth.sms import SmsClient
from api.auth.schemas import (
    SendSmsCodeRequest,
    SendSmsCodeResponse,
    RegisterByPhoneRequest,
    BindPhoneRequest,
    TokenResponse,
    UserInfo,
)
from api.auth.utils import hash_password, create_access_token, create_refresh_token, generate_invite_code
from api.auth.dependencies import require_user, get_sys_config, handle_invite_reward

router = APIRouter(prefix="/auth", tags=["SMS Authentication"])

# Column list for user queries (include phone, zs_balance, invite_code)
_USER_COLUMNS = "id, username, email, phone, role, daily_limit, vip_expires_at, zs_balance, invite_code, created_at"


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
        created_at=row["created_at"],
    )


@router.post("/send-sms-code", response_model=SendSmsCodeResponse)
async def send_sms_code(body: SendSmsCodeRequest):
    """
    Send SMS verification code.
    Rate limit: 1 request per 60 seconds per phone number.
    """
    phone = body.phone

    # Check if phone is already bound to an existing account
    existing = await Database.fetchone(
        "SELECT id FROM users WHERE phone = %s", (phone,)
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该手机号已被其他账号绑定",
        )

    # Check 60-second rate limit
    last_code = await Database.fetchone(
        "SELECT created_at FROM sms_codes WHERE phone = %s ORDER BY created_at DESC LIMIT 1",
        (phone,),
    )
    if last_code:
        last_time = last_code["created_at"]
        if isinstance(last_time, str):
            last_time = datetime.fromisoformat(last_time)
        elapsed = (datetime.now() - last_time).total_seconds()
        if elapsed < 60:
            remaining = int(60 - elapsed)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"请 {remaining} 秒后再试",
            )

    # Generate code
    code = SmsClient.generate_code()

    # Send SMS
    success = await SmsClient.send_sms(phone, code)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="短信发送失败，请稍后再试",
        )

    # Store code in database (5 minutes expiry)
    expires_at = datetime.now() + timedelta(minutes=5)
    await Database.execute(
        "INSERT INTO sms_codes (phone, code, expires_at) VALUES (%s, %s, %s)",
        (phone, code, expires_at),
    )

    logger.info(f"验证码已发送到手机 {phone}")
    return SendSmsCodeResponse(message="验证码已发送", expire_seconds=300)


@router.post("/register-by-phone", response_model=TokenResponse)
async def register_by_phone(body: RegisterByPhoneRequest):
    """
    Register a new user using phone number and SMS code.
    Auto-generates username from phone number.
    Supports invite_code for invitation rewards.
    """
    phone = body.phone
    code = body.code

    # Check if phone is already bound
    existing = await Database.fetchone(
        "SELECT id FROM users WHERE phone = %s", (phone,)
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该手机号已被绑定",
        )

    # Verify SMS code
    code_record = await Database.fetchone(
        "SELECT id, code, used, expires_at FROM sms_codes "
        "WHERE phone = %s AND used = 0 ORDER BY created_at DESC LIMIT 1",
        (phone,),
    )
    if not code_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先获取验证码",
        )

    # Check expiry
    expires_at = code_record["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at < datetime.now():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码已过期，请重新获取",
        )

    # Check code match
    if code_record["code"] != code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码错误",
        )

    # Mark code as used
    await Database.execute(
        "UPDATE sms_codes SET used = 1 WHERE id = %s",
        (code_record["id"],),
    )

    # Auto-generate username
    username = f"user_{phone[-8:]}"

    # Ensure unique username
    name_exists = await Database.fetchone(
        "SELECT id FROM users WHERE username = %s", (username,)
    )
    if name_exists:
        import time
        username = f"user_{phone[-8:]}_{int(time.time()) % 10000}"

    # Create user with invite code and registration bonus
    password_hash = hash_password(body.password)
    user_invite_code = generate_invite_code()
    register_bonus = int(await get_sys_config("register_bonus", "600"))

    user_id = await Database.execute(
        "INSERT INTO users (username, password_hash, phone, role, daily_limit, zs_balance, invite_code) "
        "VALUES (%s, %s, %s, 'normal', -1, %s, %s)",
        (username, password_hash, phone, register_bonus, user_invite_code),
    )

    # Process invite reward
    if body.invite_code:
        await handle_invite_reward(body.invite_code, user_id)

    # Generate tokens
    access_token = create_access_token(user_id, "normal")
    refresh_token = create_refresh_token(user_id, "normal")

    # Fetch created user
    row = await Database.fetchone(
        f"SELECT {_USER_COLUMNS} FROM users WHERE id = %s",
        (user_id,),
    )
    user_info = _row_to_userinfo(row) if row else UserInfo(
        id=user_id,
        username=username,
        phone=phone,
        role="normal",
        daily_limit=1,
        zs_balance=register_bonus,
        created_at=datetime.now(),
    )

    logger.info(f"新用户通过手机号注册: {username} (id={user_id}, phone={phone}) zs_balance={register_bonus}")
    return TokenResponse(access_token=access_token, refresh_token=refresh_token, user=user_info)


@router.post("/bind-phone", response_model=UserInfo)
async def bind_phone(
    body: BindPhoneRequest,
    user: UserInfo = Depends(require_user),
):
    """
    Bind phone number to the current logged-in account.
    """
    phone = body.phone
    code = body.code

    # Check if already bound to current user
    if user.phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="当前账号已绑定手机号",
        )

    # Check if phone is bound to another account
    existing = await Database.fetchone(
        "SELECT id FROM users WHERE phone = %s AND id != %s",
        (phone, user.id),
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该手机号已被其他账号绑定",
        )

    # Verify SMS code
    code_record = await Database.fetchone(
        "SELECT id, code, used, expires_at FROM sms_codes "
        "WHERE phone = %s AND used = 0 ORDER BY created_at DESC LIMIT 1",
        (phone,),
    )
    if not code_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先获取验证码",
        )

    # Check expiry
    expires_at = code_record["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at < datetime.now():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码已过期，请重新获取",
        )

    # Check code match
    if code_record["code"] != code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码错误",
        )

    # Mark code as used
    await Database.execute(
        "UPDATE sms_codes SET used = 1 WHERE id = %s",
        (code_record["id"],),
    )

    # Bind phone to current user
    await Database.execute(
        "UPDATE users SET phone = %s WHERE id = %s",
        (phone, user.id),
    )

    # Fetch updated user
    row = await Database.fetchone(
        f"SELECT {_USER_COLUMNS} FROM users WHERE id = %s",
        (user.id,),
    )
    logger.info(f"用户 {user.username} (id={user.id}) 绑定了手机号 {phone}")
    return _row_to_userinfo(row)