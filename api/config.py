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
from typing import Optional
from pydantic import BaseModel


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
    task_retention_time: int = 86400   # Keep task results for 24 hours

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

    # Storage limits per role (in bytes)
    storage_limits: dict = {
        "normal": 200 * 1024 * 1024,  # 500MB
        "vip": 1 * 1024 * 1024 * 1024,  # 2GB
        "admin": -1,  # unlimited
    }


# Global config instance
api_config = APIConfig()
