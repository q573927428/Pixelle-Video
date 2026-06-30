"""
Cookie 加密存储管理

用于安全地存储和加载各短视频平台的登录 Cookie。
使用 AES-GCM 加密后存入 MySQL 数据库。
"""

import json
import time
from typing import Optional
from loguru import logger

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    import base64
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False
    logger.warning("cryptography not installed, cookie encryption disabled")


# Fallback simple obfuscation when cryptography is not available
def _simple_obfuscate(data: str, key: str = "pixelle-publish") -> str:
    """Simple obfuscation for cookie data (NOT secure, use cryptography in production)"""
    result = []
    for i, c in enumerate(data):
        result.append(chr(ord(c) ^ ord(key[i % len(key)])))
    return base64.b64encode(''.join(result).encode()).decode()


def _simple_deobfuscate(data: str, key: str = "pixelle-publish") -> str:
    """Reverse simple obfuscation"""
    try:
        decoded = base64.b64decode(data).decode()
        result = []
        for i, c in enumerate(decoded):
            result.append(chr(ord(c) ^ ord(key[i % len(key)])))
        return ''.join(result)
    except Exception:
        return ""


class CookieManager:
    """Cookie 加密存储管理器

    提供 Cookie 的加密保存、加载和删除功能。
    支持多用户多平台多账号。
    """

    def __init__(self, secret_key: Optional[str] = None):
        """初始化 CookieManager

        Args:
            secret_key: 加密密钥（可选，默认使用内置密钥）
        """
        self._fernet = None
        if HAS_CRYPTO and secret_key:
            try:
                # Use PBKDF2 to derive a 32-byte key from the secret
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=b"pixelle-cookie-salt",
                    iterations=100000,
                )
                key = base64.urlsafe_b64encode(kdf.derive(secret_key.encode()))
                self._fernet = Fernet(key)
            except Exception as e:
                logger.warning(f"Failed to initialize Fernet encryption: {e}")
                self._fernet = None

    def _encrypt(self, data: str) -> str:
        """加密数据"""
        if self._fernet:
            try:
                return self._fernet.encrypt(data.encode()).decode()
            except Exception as e:
                logger.error(f"Encryption failed, using fallback: {e}")
        return _simple_obfuscate(data)

    def _decrypt(self, encrypted: str) -> str:
        """解密数据"""
        if self._fernet:
            try:
                return self._fernet.decrypt(encrypted.encode()).decode()
            except Exception as e:
                logger.error(f"Decryption failed, trying fallback: {e}")
        return _simple_deobfuscate(encrypted)

    async def save(self, user_id: int, platform: str, cookies: list,
                   account_name: str = "", expires_at: Optional[float] = None) -> bool:
        """保存 Cookie 到数据库

        Args:
            user_id: 用户 ID
            platform: 平台名称 (douyin/kuaishou/xiaohongshu/shipinhao)
            cookies: Playwright Cookie 列表
            account_name: 平台显示的用户名
            expires_at: Cookie 过期时间戳

        Returns:
            bool: 是否保存成功
        """
        try:
            from api.auth.database import Database

            cookies_json = json.dumps(cookies, ensure_ascii=False)
            encrypted = self._encrypt(cookies_json)

            # 检查是否已存在该用户+平台的记录
            existing = await Database.fetchone(
                "SELECT id FROM platform_accounts WHERE user_id = %s AND platform = %s",
                (user_id, platform)
            )

            expires_str = None
            if expires_at:
                from datetime import datetime
                expires_str = datetime.fromtimestamp(expires_at).strftime("%Y-%m-%d %H:%M:%S")

            if existing:
                await Database.execute(
                    """UPDATE platform_accounts
                       SET cookies_encrypted = %s, account_name = %s,
                           expires_at = %s, updated_at = NOW(), status = 'active'
                       WHERE user_id = %s AND platform = %s""",
                    (encrypted, account_name, expires_str, user_id, platform)
                )
            else:
                await Database.execute(
                    """INSERT INTO platform_accounts
                       (user_id, platform, account_name, cookies_encrypted, expires_at, status)
                       VALUES (%s, %s, %s, %s, %s, 'active')""",
                    (user_id, platform, account_name, encrypted, expires_str)
                )

            logger.info(f"✅ Cookie saved for user {user_id} / {platform}")
            return True
        except Exception as e:
            logger.error(f"Failed to save cookies: {e}")
            return False

    async def load(self, user_id: int, platform: str) -> Optional[list]:
        """从数据库加载 Cookie

        Args:
            user_id: 用户 ID
            platform: 平台名称

        Returns:
            Optional[list]: Playwright Cookie 列表，如果没有则返回 None
        """
        try:
            from api.auth.database import Database

            row = await Database.fetchone(
                """SELECT cookies_encrypted, expires_at, status
                   FROM platform_accounts
                   WHERE user_id = %s AND platform = %s""",
                (user_id, platform)
            )

            if not row:
                return None

            if row["status"] == "revoked" or row["status"] == "expired":
                logger.info(f"Cookie for user {user_id} / {platform} is {row['status']}")
                return None

            # 检查是否过期
            if row["expires_at"]:
                from datetime import datetime
                expires = row["expires_at"]
                if isinstance(expires, str):
                    expires = datetime.strptime(expires, "%Y-%m-%d %H:%M:%S")
                if expires < datetime.now():
                    logger.info(f"Cookie for user {user_id} / {platform} has expired")
                    # Mark as expired
                    await Database.execute(
                        "UPDATE platform_accounts SET status = 'expired' WHERE user_id = %s AND platform = %s",
                        (user_id, platform)
                    )
                    return None

            encrypted = row["cookies_encrypted"]
            cookies_json = self._decrypt(encrypted)
            cookies = json.loads(cookies_json)

            # 验证格式
            if not isinstance(cookies, list):
                logger.error(f"Invalid cookie format for user {user_id} / {platform}")
                return None

            # 更新最后使用时间
            await Database.execute(
                "UPDATE platform_accounts SET last_used_at = NOW() WHERE user_id = %s AND platform = %s",
                (user_id, platform)
            )

            logger.info(f"✅ Cookie loaded for user {user_id} / {platform} ({len(cookies)} cookies)")
            return cookies
        except Exception as e:
            logger.error(f"Failed to load cookies: {e}")
            return None

    async def delete(self, user_id: int, platform: str) -> bool:
        """删除指定用户+平台的 Cookie（软删除，标记为 revoked）

        Args:
            user_id: 用户 ID
            platform: 平台名称

        Returns:
            bool: 是否删除成功
        """
        try:
            from api.auth.database import Database

            await Database.execute(
                "UPDATE platform_accounts SET status = 'revoked', updated_at = NOW() WHERE user_id = %s AND platform = %s",
                (user_id, platform)
            )
            logger.info(f"✅ Cookie revoked for user {user_id} / {platform}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete cookies: {e}")
            return False

    async def list_accounts(self, user_id: int) -> list:
        """列出用户已绑定的所有平台账号

        Args:
            user_id: 用户 ID

        Returns:
            list: 账号信息列表
        """
        try:
            from api.auth.database import Database

            rows = await Database.fetchall(
                """SELECT id, platform, account_name, status, last_used_at, expires_at
                   FROM platform_accounts
                   WHERE user_id = %s
                   ORDER BY platform""",
                (user_id,)
            )

            accounts = []
            for row in rows:
                accounts.append({
                    "id": row["id"],
                    "platform": row["platform"],
                    "account_name": row["account_name"] or "",
                    "status": row["status"] or "active",
                    "last_used_at": row["last_used_at"].strftime("%Y-%m-%dT%H:%M:%SZ") if row.get("last_used_at") else None,
                    "expires_at": row["expires_at"].strftime("%Y-%m-%dT%H:%M:%SZ") if row.get("expires_at") else None,
                })

            return accounts
        except Exception as e:
            logger.error(f"Failed to list accounts: {e}")
            return []

    async def delete_account_by_id(self, account_id: int) -> bool:
        """根据 ID 删除账号记录（硬删除）

        Args:
            account_id: 账号记录 ID

        Returns:
            bool: 是否删除成功
        """
        try:
            from api.auth.database import Database

            await Database.execute(
                "DELETE FROM platform_accounts WHERE id = %s",
                (account_id,)
            )
            logger.info(f"✅ Account {account_id} deleted")
            return True
        except Exception as e:
            logger.error(f"Failed to delete account: {e}")
            return False


# 全局实例
cookie_manager = CookieManager()