# Copyright (C) 2025 AIDC-AI
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
API Configuration
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel
from dotenv import load_dotenv

# Load .env file from project root (must precede any config reads)
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    load_dotenv(str(_env_path))


class APIConfig(BaseModel):
    """API configuration"""

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False

    # CORS settings
    cors_enabled: bool = True
    cors_origins: list[str] = ["*"]

    # Task settings
    task_cleanup_interval: int = 3600  # Clean completed tasks every hour
    task_retention_time: int = 2592000  # Keep task results for 30 days

    # File upload settings
    max_upload_size: int = 100 * 1024 * 1024  # 100MB

    # API settings
    api_prefix: str = "/api"
    docs_url: Optional[str] = "/docs"
    redoc_url: Optional[str] = "/redoc"
    openapi_url: Optional[str] = "/openapi.json"

    # MySQL database settings (overridable via environment variables)
    database: dict = {
        "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", "123456"),
        "database": os.getenv("MYSQL_DATABASE", "pixelle_video"),
    }

    # JWT settings (secret key overridable via environment variable)
    jwt: dict = {
        "secret_key": os.getenv("JWT_SECRET_KEY", "pixelle-video-jwt-secret-key-change-in-production"),
        "algorithm": "HS256",
        "expire_minutes": 1440,  # 24 hours
    }

    # Aliyun SMS settings (overridable via environment variables)
    aliyun_sms: dict = {
        "access_key_id": os.getenv("ALIYUN_SMS_ACCESS_KEY_ID", ""),
        "access_key_secret": os.getenv("ALIYUN_SMS_ACCESS_KEY_SECRET", ""),
        "sign_name": os.getenv("ALIYUN_SMS_SIGN_NAME", ""),
        "template_code": os.getenv("ALIYUN_SMS_TEMPLATE_CODE", ""),
    }

    # WeChat payment settings (overridable via environment variables)
    wechat_payment: dict = {
        "mchid": os.getenv("WECHAT_MCHID", ""),
        "api_key": os.getenv("WECHAT_API_KEY", ""),
        "appid": os.getenv("WECHAT_APPID", ""),
        "notify_url": os.getenv("WECHAT_NOTIFY_URL", ""),
    }

    # Storage limits per role (in bytes)
    storage_limits: dict = {
        "normal": 200 * 1024 * 1024,  # 200MB
        "vip": 1 * 1024 * 1024 * 1024,  # 1GB
        "svip": 2 * 1024 * 1024 * 1024,  # 2GB
        "admin": -1,  # unlimited
    }


# Global config instance
api_config = APIConfig()
