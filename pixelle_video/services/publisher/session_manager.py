"""
发布会话管理

管理视频发布会话的生命周期，支持：
- 会话创建/查询/更新
- WebSocket 实时事件广播
- 过期会话自动清理
"""

import asyncio
import uuid
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from loguru import logger


@dataclass
class PublishSession:
    """发布会话数据模型"""
    session_id: str
    user_id: int
    platform: str
    status: str = "pending"  # pending | running | need_login | success | failed
    progress: float = 0.0  # 0-100
    current_step: str = "launching"  # launching | uploading | filling | cover | publishing | complete | need_login
    message: str = ""
    platform_url: str = ""  # 发布成功后的平台链接
    error: str = ""
    retry_count: int = 0
    created_at: float = 0.0
    # WebSocket 连接列表，用于广播事件
    ws_connections: list = field(default_factory=list)
    # 缓存的二维码图片数据，WS 连接时自动推送给前端
    pending_qrcode: Optional[str] = None  # base64 data URL

    def to_dict(self) -> dict:
        """转换为字典（用于 JSON 序列化）"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "platform": self.platform,
            "status": self.status,
            "progress": self.progress,
            "current_step": self.current_step,
            "message": self.message,
            "platform_url": self.platform_url,
            "error": self.error,
            "retry_count": self.retry_count,
            "created_at": self.created_at,
        }


class SessionManager:
    """发布会话管理器（内存 + 可选持久化）"""

    def __init__(self, cleanup_interval: int = 300, session_ttl: int = 3600):
        """初始化 SessionManager

        Args:
            cleanup_interval: 过期清理间隔（秒）
            session_ttl: 会话过期时间（秒），超过此时间自动清理
        """
        self._sessions: Dict[str, PublishSession] = {}
        self._lock = asyncio.Lock()
        self._cleanup_interval = cleanup_interval
        self._session_ttl = session_ttl
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

    def start(self):
        """启动后台清理任务"""
        if self._running:
            return
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("✅ SessionManager started")

    async def stop(self):
        """停止后台清理任务"""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
        logger.info("✅ SessionManager stopped")

    async def create(self, user_id: int, platform: str) -> str:
        """创建新的发布会话

        Args:
            user_id: 用户 ID
            platform: 平台名称

        Returns:
            str: 会话 ID
        """
        session_id = str(uuid.uuid4())
        session = PublishSession(
            session_id=session_id,
            user_id=user_id,
            platform=platform,
            created_at=time.time(),
        )

        async with self._lock:
            self._sessions[session_id] = session

        logger.info(f"📋 Created session {session_id} for user {user_id} / {platform}")
        return session_id

    async def get(self, session_id: str) -> Optional[PublishSession]:
        """获取会话

        Args:
            session_id: 会话 ID

        Returns:
            Optional[PublishSession]: 会话对象
        """
        async with self._lock:
            return self._sessions.get(session_id)

    async def update_status(self, session_id: str, **kwargs):
        """更新会话状态

        Args:
            session_id: 会话 ID
            **kwargs: 要更新的字段
        """
        async with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                logger.warning(f"Session {session_id} not found, cannot update")
                return

            for key, value in kwargs.items():
                if hasattr(session, key):
                    setattr(session, key, value)

            logger.debug(f"Session {session_id} updated: {kwargs}")

    async def register_ws(self, session_id: str, websocket) -> bool:
        """为会话注册 WebSocket 连接

        Args:
            session_id: 会话 ID
            websocket: WebSocket 连接对象

        Returns:
            bool: 是否注册成功
        """
        async with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                logger.warning(f"Session {session_id} not found, cannot register WS")
                return False

            if websocket not in session.ws_connections:
                session.ws_connections.append(websocket)
                logger.info(f"🔌 WebSocket registered for session {session_id} "
                            f"(total: {len(session.ws_connections)})")
            return True

    async def unregister_ws(self, session_id: str, websocket):
        """注销 WebSocket 连接"""
        async with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return

            if websocket in session.ws_connections:
                session.ws_connections.remove(websocket)
                logger.info(f"🔌 WebSocket unregistered for session {session_id} "
                            f"(remaining: {len(session.ws_connections)})")

    async def broadcast(self, session_id: str, event: dict):
        """向会话的所有 WebSocket 连接广播事件

        如果发送失败（连接已断开），自动移除该连接。

        Args:
            session_id: 会话 ID
            event: 事件字典（JSON 格式）
        """
        async with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return

            # 发送给所有 WS 连接
            disconnected = []
            for ws in session.ws_connections:
                try:
                    await ws.send_json(event)
                except Exception as e:
                    logger.warning(f"WebSocket send failed: {e}")
                    disconnected.append(ws)

            # 移除断开的连接
            for ws in disconnected:
                session.ws_connections.remove(ws)

            if disconnected:
                logger.info(f"Removed {len(disconnected)} disconnected WebSocket(s) "
                            f"from session {session_id}")

    async def remove(self, session_id: str):
        """移除会话

        Args:
            session_id: 会话 ID
        """
        async with self._lock:
            session = self._sessions.pop(session_id, None)
            if session:
                logger.info(f"🗑️ Removed session {session_id}")

    async def _cleanup_loop(self):
        """后台清理任务：移除过期会话"""
        while self._running:
            try:
                await asyncio.sleep(self._cleanup_interval)
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Session cleanup error: {e}")

    async def _cleanup_expired(self):
        """清理过期的会话"""
        now = time.time()
        expired_ids = []

        async with self._lock:
            for session_id, session in self._sessions.items():
                if now - session.created_at > self._session_ttl:
                    expired_ids.append(session_id)

            for session_id in expired_ids:
                self._sessions.pop(session_id, None)

        if expired_ids:
            logger.info(f"🧹 Cleaned up {len(expired_ids)} expired sessions")

    @property
    def active_count(self) -> int:
        """当前活跃会话数"""
        return len(self._sessions)

    def get_active_sessions(self, user_id: Optional[int] = None) -> list:
        """获取活跃会话列表

        Args:
            user_id: 可选，按用户筛选

        Returns:
            list: 会话字典列表
        """
        sessions = []
        for session in self._sessions.values():
            if user_id and session.user_id != user_id:
                continue
            sessions.append(session.to_dict())
        # 按创建时间降序排列
        sessions.sort(key=lambda s: s["created_at"], reverse=True)
        return sessions


# 全局会话管理器实例
session_manager = SessionManager()