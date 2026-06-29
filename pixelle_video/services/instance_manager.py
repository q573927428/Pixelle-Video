"""
Instance Manager - AutoDL Instance Management & Auto-Scaling Service

基于 zealman API (v8.8) docs 实现 AutoDL 实例管理、镜像机 ComfyUI 控制、空闲监控与自动扩缩容。

功能：
1. AutoDL 实例管理：list/status/snapshot/power_on/power_off/release/create
2. 镜像机 ComfyUI 控制：start/stop/comfy-status/versions/switch-version/interrupt/free
3. 任务调度：空闲检测、自动开机、自动关机、自动释放
4. 空闲监控：无任务时自动 power_off，连续7天无任务自动释放
5. 优先级队列：支持 VIP/SVIP 优先排队，根据队列深度自动扩容
"""

import asyncio
import heapq
import time
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Optional
from loguru import logger
import httpx


# ========================================================================
# Exceptions
# ========================================================================

class InstanceManagerError(Exception):
    """Base exception for instance manager errors"""
    pass


class InstanceNotFoundError(InstanceManagerError):
    """Instance not found"""
    pass


class InstanceActionError(InstanceManagerError):
    """Instance action failed"""
    pass


# ========================================================================
# AutoDL Instance Manager
# ========================================================================

class AutoDLInstanceManager:
    """
    AutoDL Instance Manager
    
    封装 AutoDL API 调用，负责实例的生命周期管理：
    - 列出实例、查询状态、查询快照
    - 开机/关机/释放
    - 不缓存 Token，由调用方传入
    """
    
    def __init__(self, panel_base_url: str = ""):
        """
        Args:
            panel_base_url: 调度面板地址 (BASE_URL)，用于转发 AutoDL API 请求
        """
        self.panel_base_url = panel_base_url.rstrip("/")
        self._http_client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(120.0),
                follow_redirects=True,
            )
        return self._http_client
    
    async def close(self):
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
    
    # ---- Instance List ----
    
    async def list_instances(
        self,
        token: str,
        page_index: int = 1,
        page_size: int = 50,
    ) -> dict:
        """
        分页列出账号下的所有 AutoDL 实例
        
        POST /api/concurrent/instance/list
        
        Returns:
            {"success": true, "result_total": 3, "list": [...]}
        """
        client = await self._get_client()
        resp = await client.post(
            f"{self.panel_base_url}/api/concurrent/instance/list",
            json={
                "token": token,
                "page_index": page_index,
                "page_size": page_size,
            },
            timeout=30.0,
        )
        # 检查 HTTP 状态码，处理非 2xx 响应
        if resp.status_code >= 400:
            try:
                error_body = resp.text
            except Exception:
                error_body = "(unable to read response body)"
            raise InstanceActionError(
                f"List instances failed: HTTP {resp.status_code} - {error_body[:500]}"
            )
        try:
            data = resp.json()
        except Exception as e:
            raise InstanceActionError(
                f"List instances failed: invalid JSON response (HTTP {resp.status_code}): {e}"
            )
        if not data.get("success"):
            raise InstanceActionError(
                f"List instances failed: {data.get('message', 'unknown error')} "
                f"(HTTP {resp.status_code})"
            )
        return data
    
    # ---- Instance Status ----
    
    async def get_instance_status(self, token: str, instance_uuid: str) -> dict:
        """
        查询单个实例的开关机/计费状态
        
        GET /api/concurrent/instance/status?token=&instance_uuid=
        
        Returns:
            {"success": true, "status": "shutdown", ...}
        """
        client = await self._get_client()
        resp = await client.get(
            f"{self.panel_base_url}/api/concurrent/instance/status",
            params={"token": token, "instance_uuid": instance_uuid},
            timeout=30.0,
        )
        data = resp.json()
        if not data.get("success"):
            raise InstanceActionError(f"Get instance status failed: {data.get('message', 'unknown error')}")
        return data
    
    # ---- Instance Snapshot ----
    
    async def get_instance_snapshot(self, token: str, instance_uuid: str) -> dict:
        """
        查询实例完整快照（含 service_6008_domain）
        
        GET /api/concurrent/instance/snapshot?token=&instance_uuid=
        
        Returns:
            {"success": true, "snapshot": {"service_6008_domain": "...", ...}}
        """
        client = await self._get_client()
        resp = await client.get(
            f"{self.panel_base_url}/api/concurrent/instance/snapshot",
            params={"token": token, "instance_uuid": instance_uuid},
            timeout=30.0,
        )
        data = resp.json()
        if not data.get("success"):
            raise InstanceActionError(f"Get instance snapshot failed: {data.get('message', 'unknown error')}")
        return data
    
    # ---- Power On ----
    
    async def power_on(self, token: str, instance_uuid: str) -> dict:
        """
        开机指定实例
        
        POST /api/concurrent/instance/power_on
        
        Returns:
            {"success": true, ...}
        """
        client = await self._get_client()
        resp = await client.post(
            f"{self.panel_base_url}/api/concurrent/instance/power_on",
            json={"token": token, "instance_uuid": instance_uuid},
            timeout=60.0,
        )
        data = resp.json()
        if not data.get("success"):
            raise InstanceActionError(f"Power on failed: {data.get('message', 'unknown error')}")
        return data
    
    # ---- Power Off ----
    
    async def power_off(self, token: str, instance_uuid: str) -> dict:
        """
        关机指定实例
        
        POST /api/concurrent/instance/power_off
        
        Returns:
            {"success": true, ...}
        """
        client = await self._get_client()
        resp = await client.post(
            f"{self.panel_base_url}/api/concurrent/instance/power_off",
            json={"token": token, "instance_uuid": instance_uuid},
            timeout=60.0,
        )
        
        # 404 表示实例已不存在，视为成功
        if resp.status_code == 404:
            logger.warning(f"Instance {instance_uuid} not found (404) on power_off, treating as success")
            return {"success": True, "message": "Instance already removed"}
        
        data = resp.json()
        if not data.get("success"):
            raise InstanceActionError(f"Power off failed: {data.get('message', 'unknown error')}")
        return data
    
    # ---- Release ----
    
    async def release_instance(self, token: str, instance_uuid: str) -> dict:
        """
        释放（销毁）实例（必须先关机；释放后数据丢失）
        
        POST /api/concurrent/instance/release
        
        Returns:
            {"success": true, ...}
        """
        client = await self._get_client()
        resp = await client.post(
            f"{self.panel_base_url}/api/concurrent/instance/release",
            json={"token": token, "instance_uuid": instance_uuid},
            timeout=60.0,
        )
        data = resp.json()
        if not data.get("success"):
            raise InstanceActionError(f"Release instance failed: {data.get('message', 'unknown error')}")
        return data
    
    # ---- Create Instance ----
    
    async def create_instance(
        self,
        token: str,
        gpu_spec_uuid: str,
        req_gpu_amount: int = 1,
        instance_name: str = "并发生成-镜像机",
        expand_system_disk_by_gb: int = 0,
    ) -> dict:
        """
        基于 Zealman 公共镜像应用，开一台新的 AutoDL 实例
        
        POST /api/concurrent/instance/create
        
        Returns:
            {"success": true, "instance_uuid": "pro-xxx"}
        """
        client = await self._get_client()
        resp = await client.post(
            f"{self.panel_base_url}/api/concurrent/instance/create",
            json={
                "token": token,
                "gpu_spec_uuid": gpu_spec_uuid,
                "req_gpu_amount": req_gpu_amount,
                "expand_system_disk_by_gb": expand_system_disk_by_gb,
                "instance_name": instance_name,
            },
            timeout=60.0,
        )
        data = resp.json()
        if not data.get("success"):
            raise InstanceActionError(f"Create instance failed: {data.get('message', 'unknown error')}")
        return data


# ========================================================================
# Mirror ComfyUI Controller
# ========================================================================

class MirrorComfyUIController:
    """
    镜像机 ComfyUI 控制
    
    通过调度面板代理转发命令到各镜像机，
    控制每台镜像机上的 ComfyUI 启动/停止/状态查询/版本切换。
    """
    
    def __init__(self, panel_base_url: str = ""):
        self.panel_base_url = panel_base_url.rstrip("/")
        self._http_client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(120.0),
                follow_redirects=True,
            )
        return self._http_client
    
    async def close(self):
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
    
    async def start_comfyui(self, mirror_url: str) -> dict:
        """
        远程启动镜像机的 ComfyUI
        
        POST /api/concurrent/mirror/start
        """
        client = await self._get_client()
        resp = await client.post(
            f"{self.panel_base_url}/api/concurrent/mirror/start",
            json={"mirror_url": mirror_url},
            timeout=30.0,
        )
        return resp.json()
    
    async def stop_comfyui(self, mirror_url: str) -> dict:
        """
        停止镜像机的 ComfyUI 进程
        
        POST /api/concurrent/mirror/stop
        """
        client = await self._get_client()
        resp = await client.post(
            f"{self.panel_base_url}/api/concurrent/mirror/stop",
            json={"mirror_url": mirror_url},
            timeout=30.0,
        )
        return resp.json()
    
    async def get_comfy_status(self, mirror_url: str) -> dict:
        """
        查询镜像机 ComfyUI 运行状态
        
        GET /api/concurrent/mirror/comfy-status?mirror_url=
        
        Returns:
            {"running": true/false, "starting": true/false, "port": 6006, ...}
        """
        client = await self._get_client()
        resp = await client.get(
            f"{self.panel_base_url}/api/concurrent/mirror/comfy-status",
            params={"mirror_url": mirror_url},
            timeout=15.0,
        )
        return resp.json()
    
    async def interrupt(self, mirror_url: str) -> dict:
        """
        中断镜像机 ComfyUI 当前任务
        
        POST /api/concurrent/mirror/interrupt
        """
        client = await self._get_client()
        resp = await client.post(
            f"{self.panel_base_url}/api/concurrent/mirror/interrupt",
            json={"mirror_url": mirror_url},
            timeout=15.0,
        )
        return resp.json()
    
    async def free_memory(self, mirror_url: str) -> dict:
        """
        释放镜像机显存
        
        POST /api/concurrent/mirror/free
        """
        client = await self._get_client()
        resp = await client.post(
            f"{self.panel_base_url}/api/concurrent/mirror/free",
            json={"mirror_url": mirror_url},
            timeout=30.0,
        )
        return resp.json()
    
    async def get_versions(self, mirror_url: str) -> dict:
        """
        查询镜像机可切换的 ComfyUI 版本列表
        
        GET /api/concurrent/mirror/versions?mirror_url=
        """
        client = await self._get_client()
        resp = await client.get(
            f"{self.panel_base_url}/api/concurrent/mirror/versions",
            params={"mirror_url": mirror_url},
            timeout=15.0,
        )
        return resp.json()
    
    async def switch_version(self, mirror_url: str, version: str) -> dict:
        """
        切换镜像机的 ComfyUI 版本
        
        POST /api/concurrent/mirror/switch-version
        """
        client = await self._get_client()
        resp = await client.post(
            f"{self.panel_base_url}/api/concurrent/mirror/switch-version",
            json={"mirror_url": mirror_url, "version": version},
            timeout=120.0,
        )
        return resp.json()
    
    async def probe(self, mirror_url: str) -> dict:
        """
        探测镜像机连通性
        
        GET /api/concurrent/probe?mirror_url=
        """
        client = await self._get_client()
        resp = await client.get(
            f"{self.panel_base_url}/api/concurrent/probe",
            params={"mirror_url": mirror_url},
            timeout=15.0,
        )
        return resp.json()
    
    async def wait_for_comfy_ready(
        self,
        mirror_url: str,
        max_wait: float = 180.0,
        poll_interval: float = 5.0,
    ) -> bool:
        """
        等待镜像机的 ComfyUI 就绪
        
        Args:
            mirror_url: 镜像机地址
            max_wait: 最大等待时间（秒）
            poll_interval: 轮询间隔（秒）
        
        Returns:
            True 表示就绪，False 表示超时
        """
        start = time.time()
        while True:
            elapsed = time.time() - start
            if elapsed > max_wait:
                logger.warning(f"Wait for ComfyUI ready timeout after {max_wait}s for {mirror_url}")
                return False
            
            try:
                status = await self.get_comfy_status(mirror_url)
                if status.get("running"):
                    logger.info(f"✅ ComfyUI ready on {mirror_url} (elapsed: {elapsed:.0f}s)")
                    return True
                if status.get("starting"):
                    logger.info(f"⏳ ComfyUI still starting on {mirror_url}... ({elapsed:.0f}s)")
            except Exception as e:
                logger.warning(f"Poll comfy status failed for {mirror_url}: {e}")
            
            await asyncio.sleep(poll_interval)
    
    async def wait_for_instance_ready(
        self,
        token: str,
        instance_uuid: str,
        max_wait: float = 300.0,
        poll_interval: float = 5.0,
    ) -> Optional[str]:
        """
        等待实例开机并获取镜像机面板 URL
        
        Args:
            token: AutoDL Token
            instance_uuid: 实例 UUID
            max_wait: 最大等待时间（秒）
            poll_interval: 轮询间隔（秒）
        
        Returns:
            镜像机面板 URL (mirror_url)，如果超时返回 None
        """
        start = time.time()
        am = AutoDLInstanceManager(self.panel_base_url)
        while True:
            elapsed = time.time() - start
            if elapsed > max_wait:
                logger.warning(f"Wait for instance ready timeout after {max_wait}s for {instance_uuid}")
                return None
            
            try:
                snapshot = await am.get_instance_snapshot(token, instance_uuid)
                snap = snapshot.get("snapshot", {})
                domain = snap.get("service_6008_domain")
                if domain:
                    mirror_url = "https://" + domain
                    logger.info(f"✅ Instance {instance_uuid} ready, mirror_url={mirror_url} (elapsed: {elapsed:.0f}s)")
                    return mirror_url
                
                status_data = await am.get_instance_status(token, instance_uuid)
                status = status_data.get("status", "")
                logger.info(f"⏳ Instance {instance_uuid} status={status}... ({elapsed:.0f}s)")
            except Exception as e:
                logger.warning(f"Poll instance status failed for {instance_uuid}: {e}")
            
            await asyncio.sleep(poll_interval)


# ========================================================================
# Instance State Tracker (in-memory)
# ========================================================================

class InstanceState:
    """跟踪每个实例的状态"""
    
    def __init__(
        self,
        instance_uuid: str,
        mirror_url: str = "",
        status: str = "shutdown",
        name: str = "",
        gpu_name: str = "",
        auto_managed: bool = False,
    ):
        self.instance_uuid = instance_uuid
        self.mirror_url = mirror_url
        self.status = status  # shutdown / running / starting
        self.comfy_status = "stopped"  # stopped / starting / running
        self.name = name or instance_uuid
        self.gpu_name = gpu_name
        self.auto_managed = auto_managed
        
        # 空闲追踪
        self.last_active_time = datetime.now()  # 最近一次有任务的时间
        self.created_at = datetime.now()
        self.power_on_time: Optional[datetime] = None
        
        # 任务计数
        self.current_jobs = 0
        self.total_jobs_completed = 0
        
        # 冷却期追踪：记录上一次关机/释放尝试时间，防止无限重试
        self._last_shutdown_attempt: Optional[datetime] = None
        
    def to_dict(self) -> dict:
        return {
            "instance_uuid": self.instance_uuid,
            "mirror_url": self.mirror_url,
            "status": self.status,
            "comfy_status": self.comfy_status,
            "name": self.name,
            "gpu_name": self.gpu_name,
            "auto_managed": self.auto_managed,
            "current_jobs": self.current_jobs,
            "total_jobs_completed": self.total_jobs_completed,
            "last_active_time": self.last_active_time.isoformat() if self.last_active_time else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "power_on_time": self.power_on_time.isoformat() if self.power_on_time else None,
            "idle_seconds": (datetime.now() - self.last_active_time).total_seconds() if self.last_active_time else 0,
            "uptime_seconds": (datetime.now() - self.power_on_time).total_seconds() if self.power_on_time else 0,
            "age_days": (datetime.now() - self.created_at).total_seconds() / 86400 if self.created_at else 0,
        }


# ========================================================================
# Priority Task Queue
# ========================================================================

class QueuedTask:
    """
    优先级队列中的任务项。
    
    使用 heapq 排序，排序规则：
    1. 优先级高（priority 值大）的排在前面
    2. 同优先级按入队时间（enqueued_at）FIFO
    """
    
    def __init__(self, task_id: str, user_id: str, priority: int = 0):
        self.task_id = task_id
        self.user_id = user_id
        # priority: 0=普通用户, 1=VIP, 2=SVIP
        self.priority = priority
        self.enqueued_at = time.time()
        # 用于阻塞等待调度结果：(mirror_url, instance_uuid)
        self.future: asyncio.Future = asyncio.get_event_loop().create_future()
    
    def __lt__(self, other: "QueuedTask") -> bool:
        """heapq 用小顶堆，我们要让 priority 大的先出"""
        if self.priority != other.priority:
            return self.priority > other.priority  # 高优先级在前
        return self.enqueued_at < other.enqueued_at  # 同优先级先到先得
    
    def __repr__(self) -> str:
        return (
            f"QueuedTask(task_id={self.task_id[:8]}..., "
            f"user_id={self.user_id}, priority={self.priority}, "
            f"enqueued_at={self.enqueued_at:.1f})"
        )


class TaskPriorityQueue:
    """
    线程安全的优先级任务队列。
    
    特点：
    - 基于 heapq 实现，O(log n) 入队/出队
    - 优先级：SVIP(2) > VIP(1) > 普通(0)
    - 同优先级按入队顺序 FIFO
    - 支持取消（移除）队列中的任务
    """
    
    def __init__(self):
        self._queue: list[QueuedTask] = []
        self._lock = asyncio.Lock()
    
    async def put(self, task: QueuedTask):
        """加入队列"""
        async with self._lock:
            heapq.heappush(self._queue, task)
            logger.info(f"📥 [队列] 任务入队: {task}, 当前排队: {len(self._queue)}")
    
    async def get_next(self) -> Optional[QueuedTask]:
        """取出最高优先级的任务"""
        async with self._lock:
            if not self._queue:
                return None
            return heapq.heappop(self._queue)
    
    async def peek_next(self) -> Optional[QueuedTask]:
        """查看下一个要处理的任务（不移除）"""
        async with self._lock:
            return self._queue[0] if self._queue else None
    
    async def remove(self, task_id: str) -> bool:
        """
        从队列中移除指定任务（用于取消）
        
        Returns:
            True 如果找到了并移除，False 如果任务不在队列中
        """
        async with self._lock:
            old_len = len(self._queue)
            self._queue = [t for t in self._queue if t.task_id != task_id]
            if len(self._queue) < old_len:
                heapq.heapify(self._queue)
                # 如果任务还在等待 future，标记为取消
                logger.info(f"🗑️ [队列] 任务已移除: {task_id[:8]}...")
                return True
            return False
    
    async def qsize(self) -> int:
        """获取当前队列长度"""
        async with self._lock:
            return len(self._queue)
    
    def waiting_count(self) -> int:
        """
        快速获取等待中任务数量（不加锁，用于近似判断，线程安全）
        """
        return len(self._queue)
    
    async def get_all(self) -> list[QueuedTask]:
        """获取所有排队中的任务（用于状态查看）"""
        async with self._lock:
            return list(self._queue)


# ========================================================================
# Auto-Scaling & Idle Monitor
# ========================================================================

class AutoScalingMonitor:
    """
    自动扩缩容与空闲监控服务
    
    核心功能：
    1. 用户提交任务时，检查是否有空闲 GPU
    2. 没有空闲则自动 power_on 第二台甚至第三台镜像机
    3. 等待实例变为 running
    4. 自动启动 ComfyUI
    5. 分发任务
    6. 连续一段时间无任务（默认 10 分钟）后自动 power_off（主控机除外）
    7. 连续 7 天无任务自动释放实例（主控机除外）
    8. 优先级队列调度，VIP/SVIP 优先排队
    9. 根据等待队列深度自动扩容
    
    使用方式：
        monitor = AutoScalingMonitor(panel_base_url)
        await monitor.start()  # 开启后台监控循环
    """
    
    def __init__(
        self,
        panel_base_url: str = "",
        idle_shutdown_minutes: int = 10,
        idle_release_days: int = 7,
        check_interval_seconds: int = 60,
        max_jobs_per_instance: int = 1,
    ):
        self.panel_base_url = panel_base_url
        self.idle_shutdown_minutes = idle_shutdown_minutes
        self.idle_release_days = idle_release_days
        self.check_interval_seconds = check_interval_seconds
        # ⭐ 每台实例一次只处理 1 个任务（GPU 密集型任务不适合并行）
        self.max_jobs_per_instance = max_jobs_per_instance
        
        # 主控机实例 UUID（永远不会自动关机/释放）
        self._master_instance_uuid: Optional[str] = None
        
        # 实例状态跟踪
        self.instances: dict[str, InstanceState] = {}  # instance_uuid -> InstanceState
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._dispatch_task: Optional[asyncio.Task] = None  # 后台调度循环
        
        # 默认 AutoDL Token (从配置读取)
        self._default_token: str = ""
        
        # 组件
        self._instance_manager: Optional[AutoDLInstanceManager] = None
        self._mirror_controller: Optional[MirrorComfyUIController] = None
        
        # 日志目录
        self._log_dir = Path("output") / "instance_logs"
        self._log_dir.mkdir(parents=True, exist_ok=True)
        
        # ===== 优先级任务队列 =====
        self._task_queue = TaskPriorityQueue()
        
        # ===== 幂等开机追踪（多实例并发支持）=====
        # 记录正在开机中的实例 UUID 集合，允许多个不同实例并发开机
        self._pending_power_ons: set[str] = set()
        # 每个开机中实例对应的异步事件（dict: instance_uuid -> Event）
        self._power_on_events: dict[str, asyncio.Event] = {}
        # 每个开机中实例完成后的结果缓存（dict: instance_uuid -> (mirror_url, instance_uuid) or None）
        self._power_on_results: dict[str, Optional[tuple[str, str]]] = {}
    
    async def start(self, token: str = ""):
        """启动监控"""
        if self._running:
            return
        
        if token:
            self._default_token = token
        
        self._instance_manager = AutoDLInstanceManager(self.panel_base_url)
        self._mirror_controller = MirrorComfyUIController(self.panel_base_url)
        
        # 自动从面板 URL 中提取主控机 UUID，防止主控机被自动关机/释放
        master_uuid = self._extract_master_uuid_from_url()
        if master_uuid:
            self._master_instance_uuid = master_uuid
            logger.info(f"🎯 Auto-detected master instance from panel URL: {master_uuid}")
        
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        # ⭐ 启动后台调度循环（负责队列出队、分配实例、自动扩容）
        self._dispatch_task = asyncio.create_task(self._dispatch_loop())
        logger.info(
            f"✅ AutoScalingMonitor started "
            f"(idle_shutdown={self.idle_shutdown_minutes}min, "
            f"idle_release={self.idle_release_days}d, "
            f"max_jobs_per_instance={self.max_jobs_per_instance})"
        )
    
    async def stop(self):
        """停止监控"""
        self._running = False
        
        # 停止调度循环
        if self._dispatch_task:
            self._dispatch_task.cancel()
            try:
                await self._dispatch_task
            except asyncio.CancelledError:
                pass
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        if self._instance_manager:
            await self._instance_manager.close()
        if self._mirror_controller:
            await self._mirror_controller.close()
        
        logger.info("🛑 AutoScalingMonitor stopped")
    
    def is_running(self) -> bool:
        """监控是否正在运行"""
        return self._running

    def set_token(self, token: str):
        """设置 AutoDL Token"""
        self._default_token = token
    
    # ---- 实例注册 ----
    
    def register_instance(self, instance: InstanceState):
        """注册一个实例到监控器"""
        self.instances[instance.instance_uuid] = instance
        logger.info(f"📝 Registered instance {instance.name} ({instance.instance_uuid})")
    
    def unregister_instance(self, instance_uuid: str):
        """从监控器移除实例"""
        self.instances.pop(instance_uuid, None)
        logger.info(f"🗑️ Unregistered instance {instance_uuid}")
    
    # ====================================================================
    # ⭐ 优先级队列调度（新功能）
    # ====================================================================
    
    async def enqueue_and_wait(
        self,
        task_id: str,
        user_id: str = "",
        priority: int = 0,
        token: str = "",
    ) -> Optional[tuple[str, str]]:
        """
        将任务加入优先级队列并等待调度。
        
        这是外部调用（pipelines.py）使用的入口方法：
        1. 将任务加入优先级队列
        2. 阻塞等待被调度到一台实例
        3. 返回 (mirror_url, instance_uuid)
        
        Args:
            task_id: 任务 ID
            user_id: 用户 ID
            priority: 优先级（0=普通, 1=VIP, 2=SVIP）
            token: AutoDL Token
        
        Returns:
            (mirror_url, instance_uuid) 或 None（如果队列已关闭或任务被取消）
        """
        token = token or self._default_token
        
        # 先尝试立即分配（如果刚好有空闲实例，跳过排队）
        found = self._find_available_instance()
        if found:
            logger.info(f"⚡ [调度] 有空闲实例，直接分配: {found.name}")
            return self._reserve_and_return(found)
        
        # 创建排队任务
        queued = QueuedTask(
            task_id=task_id,
            user_id=user_id,
            priority=priority,
        )
        
        # 加入优先级队列
        await self._task_queue.put(queued)
        
        qsize = self._task_queue.waiting_count()
        logger.info(
            f"⏳ [调度] 任务 {task_id[:8]}... 加入优先级队列 "
            f"(priority={priority}, 排队位置=~{qsize})"
        )
        
        # ⭐ 唤醒调度循环立即处理（不等待下一次轮询）
        # 如果调度循环正在 sleep，提前唤醒它
        # （通过 _dispatch_loop 的下一轮检测自然触发）
        
        try:
            # 阻塞等待调度结果
            result = await asyncio.wait_for(queued.future, timeout=None)
            return result
        except asyncio.CancelledError:
            # 任务被取消，从队列中移除
            await self._task_queue.remove(task_id)
            logger.info(f"🗑️ [调度] 任务 {task_id[:8]}... 已取消，从队列移除")
            return None
    
    async def cancel_queued_task(self, task_id: str):
        """
        取消队列中的任务。
        
        当用户取消任务时调用，确保任务不会在队列中无限等待。
        """
        removed = await self._task_queue.remove(task_id)
        if removed:
            logger.info(f"🗑️ [调度] 已取消队列中的任务: {task_id[:8]}...")
    
    # ---- 任务状态更新 ----
    
    def on_task_submitted(self, instance_uuid: str):
        """任务提交到实例时调用"""
        inst = self.instances.get(instance_uuid)
        if inst:
            # current_jobs 已在 ensure_ready_instance 中预占，这里不再增加
            # 仅更新最后活跃时间
            inst.last_active_time = datetime.now()
    
    def on_task_completed(self, instance_uuid: str):
        """任务完成时调用，释放实例槽位并触发下一轮调度"""
        inst = self.instances.get(instance_uuid)
        if inst:
            inst.current_jobs = max(0, inst.current_jobs - 1)
            inst.total_jobs_completed += 1
            inst.last_active_time = datetime.now()
            logger.info(
                f"🔄 [调度] 实例 {inst.name} 任务完成, "
                f"current_jobs={inst.current_jobs}/{self.max_jobs_per_instance}"
            )
        # ⭐ 任务完成 → 触发下一轮调度（队列中等待的任务可以立即分配）
        # 不需要主动触发，_dispatch_loop 每 2 秒轮询一次
    
    # ---- 查找空闲实例 ----
    
    def get_idle_instances(self) -> list[InstanceState]:
        """获取当前空闲 (current_jobs=0) 且 running 的实例"""
        return [
            inst for inst in self.instances.values()
            if inst.current_jobs == 0
            and inst.status == "running"
            and inst.comfy_status == "running"
        ]
    
    def get_running_instances(self) -> list[InstanceState]:
        """获取所有 running 的实例"""
        return [
            inst for inst in self.instances.values()
            if inst.status == "running"
        ]
    
    def get_shutdown_instances(self) -> list[InstanceState]:
        """获取所有关机的实例"""
        return [
            inst for inst in self.instances.values()
            if inst.status == "shutdown"
        ]
    
    # ---- 自动开机 ----
    
    def _extract_master_uuid_from_url(self) -> Optional[str]:
        """从面板 base_url 中提取主控机的实例 UUID（URL 中的 pro-xxx 部分）"""
        import re
        if not self.panel_base_url:
            return None
        match = re.search(r'(pro-[a-z0-9]+)', self.panel_base_url)
        if match:
            return match.group(1)
        return None

    def set_master_instance(self, uuid: str):
        """设置主控机实例 UUID（此实例不会被自动关机/释放）"""
        self._master_instance_uuid = uuid
        logger.info(f"🎯 Master instance set: {uuid}")

    async def auto_power_on(
        self,
        token: str = "",
        max_instances: int = 5,
        skip_uuids: Optional[set[str]] = None,
    ) -> Optional[str]:
        """
        自动开机一台关机中的镜像机，支持跳过已经在开机中的实例。
        
        Args:
            token: AutoDL Token
            max_instances: 最大实例数（保留参数，兼容旧接口）
            skip_uuids: 需要跳过的实例 UUID 集合（已在开机中或已尝试过的）
        
        Returns:
            开机的实例 UUID，如果没有可用的关机实例返回 None
        """
        token = token or self._default_token
        if not token:
            logger.warning("No AutoDL token configured for auto power-on")
            return None
        
        shutdown_instances = self.get_shutdown_instances()
        if not shutdown_instances:
            # 尝试从 AutoDL 拉取最新实例列表
            try:
                result = await self._instance_manager.list_instances(token)
                for item in result.get("list", []):
                    uuid = item.get("uuid") or item.get("instance_uuid") or ""
                    if not uuid or uuid in self.instances:
                        continue
                    is_master = uuid == self._master_instance_uuid
                    self.register_instance(InstanceState(
                        instance_uuid=uuid,
                        status=item.get("status", "shutdown"),
                        name=item.get("name") or item.get("machine_alias") or uuid,
                        gpu_name=item.get("gpu_name") or item.get("gpu_spec_uuid", ""),
                        auto_managed=not is_master,
                    ))
                shutdown_instances = self.get_shutdown_instances()
            except Exception as e:
                logger.error(f"Failed to list instances for auto power-on: {e}")
                return None
        
        if not shutdown_instances:
            logger.warning("No shutdown instances available for auto power-on")
            return None
        
        # 过滤掉需要跳过的实例（已在开机中的）
        candidates = [
            inst for inst in shutdown_instances
            if skip_uuids is None or inst.instance_uuid not in skip_uuids
        ]
        if not candidates:
            logger.warning("All shutdown instances are already being powered on or excluded")
            return None
        
        # 选一台关机最久的
        target = min(candidates, key=lambda x: x.created_at)
        
        logger.info(f"🔌 Auto power-on instance {target.name} ({target.instance_uuid})")
        try:
            await self._instance_manager.power_on(token, target.instance_uuid)
            target.status = "starting"
            target.power_on_time = datetime.now()
            return target.instance_uuid
        except Exception as e:
            logger.error(f"Auto power-on failed for {target.instance_uuid}: {e}")
            return None
    
    # ---- 等待实例就绪 ----
    
    async def wait_and_setup_instance(
        self,
        instance_uuid: str,
        token: str = "",
        start_comfyui: bool = True,
        max_wait: float = 300.0,
    ) -> Optional[str]:
        """
        等待实例开机就绪，然后自动启动 ComfyUI
        
        Args:
            instance_uuid: 实例 UUID
            token: AutoDL Token
            start_comfyui: 是否自动启动 ComfyUI
            max_wait: 最大等待时间
        
        Returns:
            镜像机面板 URL，仅当实例开机 AND ComfyUI 都就绪时才返回
            任一环节失败返回 None
        """
        token = token or self._default_token
        inst = self.instances.get(instance_uuid)
        if not inst:
            logger.error(f"Instance {instance_uuid} not registered")
            return None
        
        # 1. 等待实例开机，获取镜像机 URL
        mirror_url = await self._mirror_controller.wait_for_instance_ready(
            token, instance_uuid, max_wait=max_wait
        )
        if not mirror_url:
            logger.error(f"Instance {instance_uuid} failed to become ready")
            return None
        
        inst.mirror_url = mirror_url
        inst.status = "running"
        
        # 2. 启动 ComfyUI 并等待它完全就绪
        if start_comfyui:
            logger.info(f"🚀 Starting ComfyUI on {mirror_url}")
            try:
                await self._mirror_controller.start_comfyui(mirror_url)
                inst.comfy_status = "starting"
                
                ready = await self._mirror_controller.wait_for_comfy_ready(mirror_url)
                if ready:
                    inst.comfy_status = "running"
                    logger.info(f"✅ ComfyUI ready on {mirror_url}")
                    return mirror_url
                else:
                    logger.warning(f"⚠️ ComfyUI start timeout on {mirror_url}, instance not ready")
                    inst.comfy_status = "stopped"
                    return None
            except Exception as e:
                logger.error(f"Failed to start ComfyUI on {mirror_url}: {e}")
                inst.comfy_status = "stopped"
                return None
        
        return mirror_url
    
    # ---- 自动关机 ----
    
    async def auto_power_off(self, instance_uuid: str, token: str = ""):
        """自动关机指定实例（主控机不受自动关机影响）"""
        token = token or self._default_token
        inst = self.instances.get(instance_uuid)
        if not inst:
            return
        
        # ⛔ 主控机永不自动关机
        if instance_uuid == self._master_instance_uuid:
            logger.warning(f"⛔ Skipping power-off for master instance {instance_uuid}")
            return
        
        # 冷却期检查：3分钟内不重复尝试关机同一实例
        now = datetime.now()
        if inst._last_shutdown_attempt:
            cooldown_elapsed = (now - inst._last_shutdown_attempt).total_seconds()
            if cooldown_elapsed < 180:
                logger.warning(f"⏳ Instance {instance_uuid} shutdown attempted {cooldown_elapsed:.0f}s ago, skipping (cooldown)")
                return
        
        inst._last_shutdown_attempt = now
        logger.info(f"🔌 Auto power-off instance {inst.name} ({instance_uuid})")
        
        # 先停 ComfyUI
        if inst.mirror_url and inst.comfy_status == "running":
            try:
                await self._mirror_controller.stop_comfyui(inst.mirror_url)
                inst.comfy_status = "stopped"
            except Exception as e:
                logger.warning(f"Stop ComfyUI failed for {instance_uuid}: {e}")
        
        # 关机
        try:
            await self._instance_manager.power_off(token, instance_uuid)
            inst.status = "shutdown"
            inst.mirror_url = ""
            inst.power_on_time = None
            logger.info(f"✅ Instance {instance_uuid} powered off")
        except Exception as e:
            logger.error(f"Power off failed for {instance_uuid}: {e}")
            logger.warning(f"⚠️ Marking instance {instance_uuid} as shutdown despite error to prevent retry loop")
            inst.status = "shutdown"
            inst.mirror_url = ""
            inst.power_on_time = None
    
    # ---- 自动释放 ----
    
    async def auto_release(self, instance_uuid: str, token: str = ""):
        """自动释放（销毁）实例（主控机不受自动释放影响）"""
        token = token or self._default_token
        inst = self.instances.get(instance_uuid)
        if not inst:
            return
        
        # ⛔ 主控机永不自动释放
        if instance_uuid == self._master_instance_uuid:
            logger.warning(f"⛔ Skipping auto-release for master instance {instance_uuid}")
            return
        
        # 冷却期检查：5分钟内不重复尝试释放同一实例
        now = datetime.now()
        if inst._last_shutdown_attempt:
            cooldown_elapsed = (now - inst._last_shutdown_attempt).total_seconds()
            if cooldown_elapsed < 300:
                logger.warning(f"⏳ Instance {instance_uuid} release attempted {cooldown_elapsed:.0f}s ago, skipping (cooldown)")
                return
        
        inst._last_shutdown_attempt = now
        logger.warning(f"🔥 Auto-releasing instance {inst.name} ({instance_uuid}) - idle > {self.idle_release_days}d")
        
        if inst.status == "running":
            await self.auto_power_off(instance_uuid, token)
        
        try:
            await self._instance_manager.release_instance(token, instance_uuid)
            self.unregister_instance(instance_uuid)
            logger.info(f"✅ Instance {instance_uuid} released")
        except Exception as e:
            logger.error(f"Release instance failed for {instance_uuid}: {e}")
    
    # ---- 智能扩缩容主逻辑 ----
    
    async def ensure_ready_instance(self, token: str = "") -> Optional[tuple[str, str]]:
        """
        核心方法：确保有一台就绪的镜像机可用。
        
        策略按以下顺序：
        
        阶段1 - 立即检查：找空闲/有容量实例 -> 直接返回
        阶段2 - 短时轮询(30s)：等现有满载实例释放槽位 -> 返回
        阶段3 - 等待已有开机：如果有其他实例正在开机中，等一台完成 -> 检查容量
        阶段4 - 发起新开机：没有等待中的开机，也没有容量释放 -> 关机开机
        阶段5 - 开机完成后容量仍不足 -> 继续启动下一台关机实例
        
        v2 修复：支持多台关机实例并发自动开机。
        原版 Bug：_pending_power_on 单槽设计导致后续所有任务都阻塞等待同一台实例，
        开机完成后所有任务扎堆到同一台实例上，其他关机实例永远不会被启动。
        
        Returns:
            (mirror_url, instance_uuid) 或 None
        """
        token = token or self._default_token
        
        # ===== 阶段1：立即检查是否有可用容量 =====
        found = self._find_available_instance()
        if found:
            return self._reserve_and_return(found)
        
        # ===== 阶段2：短时轮询等待现有实例释放容量（30秒内） =====
        POLL_COUNT = 6
        POLL_INTERVAL = 5
        for i in range(POLL_COUNT):
            await asyncio.sleep(POLL_INTERVAL)
            found = self._find_available_instance()
            if found:
                logger.info(f"⏳ Waited {POLL_INTERVAL * (i+1)}s, instance capacity freed up!")
                return self._reserve_and_return(found)
        
        # ===== 阶段3：如果有其他任务已在开机中，等待一台完成 =====
        if self._pending_power_ons:
            logger.info(f"⏳ Other instances already powering on ({len(self._pending_power_ons)} pending), waiting for one to complete...")
            
            wait_tasks = []
            for puuid in list(self._pending_power_ons):
                event = self._power_on_events.get(puuid)
                if event:
                    wait_tasks.append(asyncio.create_task(event.wait()))
            
            if wait_tasks:
                done_set, _ = await asyncio.wait(wait_tasks, return_when=asyncio.FIRST_COMPLETED)
                logger.info(f"⏳ At least one pending power-on completed, checking capacity... ({len(done_set)} of {len(wait_tasks)} completed)")
                
                found = self._find_available_instance()
                if found:
                    logger.info(f"✅ Power-on completed, reclaiming instance {found.name}")
                    return self._reserve_and_return(found)
            
            if self._pending_power_ons:
                logger.info(f"⏳ {len(self._pending_power_ons)} instances still powering on, but will try to start another too")
        
        # ===== 阶段4：发起新开机 =====
        logger.info("🔄 No capacity freed up, starting auto power-on for a shutdown instance...")
        
        instance_uuid = await self.auto_power_on(token, skip_uuids=self._pending_power_ons)
        if not instance_uuid:
            logger.error("❌ No shutdown instance available for auto power-on")
            return None
        
        self._pending_power_ons.add(instance_uuid)
        if instance_uuid not in self._power_on_events:
            self._power_on_events[instance_uuid] = asyncio.Event()
        self._power_on_results[instance_uuid] = None
        
        power_on_event = self._power_on_events[instance_uuid]
        power_on_event.clear()
        
        try:
            mirror_url = await self.wait_and_setup_instance(instance_uuid, token)
            if not mirror_url:
                logger.error(f"❌ Instance {instance_uuid} failed to become ready")
                self._power_on_results[instance_uuid] = None
                return None
            
            inst = self.instances.get(instance_uuid)
            if inst:
                result = self._reserve_and_return(inst)
            else:
                result = (mirror_url, instance_uuid)
            self._power_on_results[instance_uuid] = result
            logger.info(f"✅ Auto-powered and ready: {mirror_url} (instance={instance_uuid})")
            
            # ===== 阶段5：检查容量是否仍然不足 =====
            running = self.get_running_instances()
            total_pending = sum(1 for i in self.instances.values() if i.status == "starting")
            total_pending_or_running = len(running) + total_pending
            
            available_shutdown = len([
                i for i in self.get_shutdown_instances()
                if i.instance_uuid not in self._pending_power_ons
            ])
            
            if available_shutdown > 0 and total_pending_or_running < 3:
                logger.info(
                    f"🔍 Capacity check: running={len(running)} pending={total_pending} "
                    f"shutdown_available={available_shutdown}, starting next instance..."
                )
                asyncio.create_task(self._background_power_on_next(token))
            
            return result
        finally:
            if power_on_event:
                power_on_event.set()
    
    async def _background_power_on_next(self, token: str):
        """
        后台启动下一台关机实例（异步非阻塞）。
        （保留原有实现，兼容旧调用方）
        """
        try:
            result = self._find_available_instance()
            if result:
                logger.info("⏭️ Background power-on skipped: capacity already sufficient")
                return
            
            instance_uuid = await self.auto_power_on(token, skip_uuids=self._pending_power_ons)
            if not instance_uuid:
                logger.info("⏭️ Background power-on skipped: no more shutdown instances")
                return
            
            self._pending_power_ons.add(instance_uuid)
            if instance_uuid not in self._power_on_events:
                self._power_on_events[instance_uuid] = asyncio.Event()
            self._power_on_results[instance_uuid] = None
            
            logger.info(f"🔌 Background power-on: instance {instance_uuid}")
            mirror_url = await self.wait_and_setup_instance(instance_uuid, token)
            if mirror_url:
                result = (mirror_url, instance_uuid)
                self._power_on_results[instance_uuid] = result
                logger.info(f"✅ Background power-on complete: {mirror_url} (instance={instance_uuid})")
                
                available_shutdown = len([
                    i for i in self.get_shutdown_instances()
                    if i.instance_uuid not in self._pending_power_ons
                ])
                total_running_or_starting = len(self.get_running_instances()) + len([
                    i for i in self.instances.values() if i.status == "starting"
                ])
                if available_shutdown > 0 and total_running_or_starting < 3:
                    asyncio.create_task(self._background_power_on_next(token))
            else:
                logger.warning(f"❌ Background power-on failed for {instance_uuid}")
                self._power_on_results[instance_uuid] = None
            
            event = self._power_on_events.get(instance_uuid)
            if event:
                event.set()
                
        except Exception as e:
            logger.error(f"Background power-on error: {e}")

    def _reserve_and_return(self, instance: InstanceState) -> tuple[str, str]:
        """
        预占一个任务槽位并返回镜像信息。
        
        Returns:
            (mirror_url, instance_uuid)
            mirror_url 是 ComfyUI 的访问地址：
            - 镜像机（auto_managed=True）使用其独立的 service_6008_domain
            - 主控机（auto_managed=False）使用面板 base_url，因为主控机本身就是调度面板，
              所有 API 请求通过面板代理转发到主控机上的 ComfyUI
        """
        instance.current_jobs += 1
        instance.last_active_time = datetime.now()
        mirror_url = instance.mirror_url
        # 主控机没有独立的 mirror_url，使用面板地址作为 ComfyUI 入口
        if not mirror_url and self.panel_base_url:
            mirror_url = self.panel_base_url
        logger.info(
            f"🔒 Reserved slot on {instance.name} "
            f"(jobs={instance.current_jobs}/{self.max_jobs_per_instance})"
        )
        return (mirror_url, instance.instance_uuid)

    def _find_available_instance(self) -> Optional[InstanceState]:
        """
        查找当前可用的实例（同步方法，无阻塞）
        1. 优先找空闲实例（current_jobs==0 且 comfy running）
        2. 找有容量且 ComfyUI 已就绪的实例
        注意：ComfyUI 必须为 running 状态才会分配任务
        """
        # 1. 找空闲实例（current_jobs=0 且 comfy running）
        idle = self.get_idle_instances()
        if idle:
            target = idle[0]
            logger.info(f"✅ Found idle instance {target.name}: {target.mirror_url}")
            return target
        
        # 2. 找 running 中负载未满且 ComfyUI 就绪的实例
        running = self.get_running_instances()
        if running:
            available = [
                i for i in running
                if i.current_jobs < self.max_jobs_per_instance
                and i.comfy_status == "running"
            ]
            if available:
                min_jobs = min(inst.current_jobs for inst in available)
                target = [i for i in available if i.current_jobs == min_jobs][0]
                logger.info(
                    f"✅ Using available instance {target.name} "
                    f"(jobs={target.current_jobs}/{self.max_jobs_per_instance}, "
                    f"comfy={target.comfy_status})"
                )
                return target
        
        return None

    # ====================================================================
    # ⭐ 后台调度循环（核心新功能）
    # ====================================================================
    
    async def _dispatch_loop(self):
        """
        后台调度循环，负责：
        
        1. 检查优先级队列中的等待任务
        2. 如果队列非空且有空闲实例 → 分配任务
        3. 如果队列非空且无空闲实例 → 根据队列深度自动开机
        4. 扩缩容规则：
           - 等待 > 0 且无空闲实例 → 开机 1 台关机实例
           - 等待 > 5 且无空闲实例 → 开机第 2 台关机实例（如果有）
           - 等待 > 10 → 开机所有可用关机实例
        5. 每 2 秒轮询一次
        """
        POLL_INTERVAL = 2.0  # 调度轮询间隔（秒）
        
        logger.info("🚀 [调度循环] 后台调度循环已启动 (poll_interval=2s)")
        
        while self._running:
            try:
                await self._dispatch_tick()
            except Exception as e:
                logger.error(f"❌ [调度循环] 异常: {e}")
            
            await asyncio.sleep(POLL_INTERVAL)
        
        logger.info("🛑 [调度循环] 已停止")
    
    async def _dispatch_tick(self):
        """
        单次调度 tick。
        
        1. 从优先级队列取出最高优先级的任务
        2. 如果队列为空，什么都不做
        3. 尝试查找空闲实例
        4. 如果有空闲实例 → 分配，设置 future 结果
        5. 如果无空闲实例 → 检查是否需要自动开机
        6. 如果队列非空但无实例可用 → 下一个 tick 重试
        """
        # 读取队列长度（不加锁，近似值即可）
        waiting = self._task_queue.waiting_count()
        if waiting == 0:
            return
        
        # ===== 出队所有可分配的任务 =====
        while waiting > 0:
            # 查找可用实例
            found = self._find_available_instance()
            if found:
                # 有可用实例，出队一个任务
                task = await self._task_queue.get_next()
                if task is None:
                    break  # 队列为空
                
                # 预占实例槽位
                mirror_url, instance_uuid = self._reserve_and_return(found)
                
                # 设置 future 结果，唤醒等待的调用方
                if not task.future.done():
                    task.future.set_result((mirror_url, instance_uuid))
                    logger.info(
                        f"✅ [调度] 分配实例 {found.name} 给任务 "
                        f"{task.task_id[:8]}... (priority={task.priority})"
                    )
                waiting = self._task_queue.waiting_count()
                continue
            
            # ===== 没有可用实例，检查是否需要扩容 =====
            # ⭐ 先尝试从 AutoDL 拉取最新实例列表，确保 self.instances 完整
            # 因为真实环境中可能是首次使用，实例还未被注册
            try:
                if self._instance_manager and self._default_token:
                    result = await self._instance_manager.list_instances(self._default_token)
                    for item in result.get("list", []):
                        uuid = item.get("uuid") or item.get("instance_uuid") or ""
                        if not uuid or uuid in self.instances:
                            continue
                        is_master = uuid == self._master_instance_uuid
                        item_status = item.get("status", "shutdown")
                        new_inst = InstanceState(
                            instance_uuid=uuid,
                            status=item_status,
                            name=item.get("name") or item.get("machine_alias") or uuid,
                            gpu_name=item.get("gpu_name") or item.get("gpu_spec_uuid", ""),
                            auto_managed=not is_master,
                        )
                        # ⭐ 如果实例已经是 running 状态（如主控机），将 comfy_status 也设为 running
                        # 因为它的 ComfyUI 已经在运行中，可以立即接任务
                        if item_status == "running":
                            new_inst.comfy_status = "running"
                        self.register_instance(new_inst)
            except Exception as e:
                logger.warning(f"⚠️ [调度] 拉取实例列表异常: {e}")
            
            shutdown_instances = self.get_shutdown_instances()
            shutdown_count = len(shutdown_instances)
            running_count = len(self.get_running_instances())
            
            if shutdown_count == 0:
                logger.info(
                    f"⏳ [调度] 队列有 {waiting} 个等待任务，"
                    f"运行中={running_count}，但无空闲实例且无关机实例可启动"
                )
                break
            
            logger.info(
                f"⏳ [调度] 队列有 {waiting} 个等待任务，"
                f"运行中={running_count}，关机={shutdown_count}"
            )
            
            # ----- 扩容决策 -----
            # 计算当前可用槽位：空闲实例数（current_jobs=0 且 comfy running）
            available_slots = len(self.get_idle_instances())
            # 计算已经在开机中的实例数（排除已完成的）
            already_starting = len(self._pending_power_ons)
            # 计算真正需要启动的数量
            # = 排队任务数 - 已可用槽位 - 正在开机中的（完成后会提供新槽位）
            needed = max(0, waiting - available_slots - already_starting)
            instances_to_start = min(shutdown_count, needed)
            
            if instances_to_start > 0:
                logger.info(
                    f"🚀 [调度] 决定启动 {instances_to_start} 台实例 "
                    f"(waiting={waiting}, shutdown={shutdown_count}, "
                    f"already_starting={already_starting})"
                )
                for _ in range(instances_to_start):
                    await self._power_on_and_setup_next()
            
            break  # while 循环退出
    
    async def _power_on_and_setup_next(self) -> Optional[str]:
        """
        在后台启动一台关机实例，并注册事件。
        与 _background_power_on_next 类似，但被 dispatch 循环使用。
        
        Returns:
            开机中的实例 UUID，或 None（没有可用的关机实例）
        """
        token = self._default_token
        if not token:
            logger.warning("[调度] No token configured for auto power-on")
            return None
        
        instance_uuid = await self.auto_power_on(token, skip_uuids=self._pending_power_ons)
        if not instance_uuid:
            return None
        
        # 注册到幂等保护集
        self._pending_power_ons.add(instance_uuid)
        if instance_uuid not in self._power_on_events:
            self._power_on_events[instance_uuid] = asyncio.Event()
        self._power_on_results[instance_uuid] = None
        
        # 在后台等待开机完成（不阻塞 dispatch 循环）
        asyncio.create_task(self._wait_and_finalize_power_on(instance_uuid, token))
        
        return instance_uuid
    
    async def _wait_and_finalize_power_on(self, instance_uuid: str, token: str):
        """
        等待实例开机完成并注册就绪状态（后台任务，不阻塞 dispatch 循环）。
        """
        try:
            mirror_url = await self.wait_and_setup_instance(instance_uuid, token)
            inst = self.instances.get(instance_uuid)
            
            if mirror_url and inst:
                self._power_on_results[instance_uuid] = (mirror_url, instance_uuid)
                logger.info(f"✅ [调度] 实例 {instance_uuid} 开机就绪: {mirror_url}")
            else:
                self._power_on_results[instance_uuid] = None
                if inst:
                    logger.warning(f"❌ [调度] 实例 {inst.name} 开机失败")
                else:
                    logger.warning(f"❌ [调度] 实例 {instance_uuid} 开机失败（未注册）")
        except Exception as e:
            logger.error(f"❌ [调度] 实例 {instance_uuid} 开机异常: {e}")
            self._power_on_results[instance_uuid] = None
        finally:
            # 触发事件通知等待者
            event = self._power_on_events.get(instance_uuid)
            if event:
                event.set()
    
    # ---- 后台监控循环 ----
    
    async def _monitor_loop(self):
        """后台监控循环：检查空闲实例，自动关机/释放"""
        while self._running:
            try:
                await self._check_idle_instances()
            except Exception as e:
                logger.error(f"Idle check error: {e}")
            
            await asyncio.sleep(self.check_interval_seconds)
    
    async def _check_idle_instances(self):
        """
        检查所有实例的空闲状态，执行关机/释放。
        
        ⭐ 改进：如果优先级队列中还有等待任务，不关机任何实例。
        避免一边排队一边关机的矛盾情况。
        """
        # 如果有排队等待的任务，跳过关机检查
        waiting = self._task_queue.waiting_count()
        if waiting > 0:
            return
        
        now = datetime.now()
        
        for inst in list(self.instances.values()):
            if inst.status != "running":
                continue
            if inst.current_jobs > 0:
                continue
            
            # ⛔ 主控机永不自动关机/释放
            if inst.instance_uuid == self._master_instance_uuid:
                continue
            
            idle_seconds = (now - inst.last_active_time).total_seconds()
            idle_days = (now - inst.created_at).total_seconds() / 86400
            
            # 检查是否满足释放条件（7天无任务）
            if idle_days >= self.idle_release_days:
                logger.info(f"🔄 Instance {inst.name} idle for {idle_days:.1f}d, releasing...")
                await self.auto_release(inst.instance_uuid)
                continue
            
            # 检查是否满足关机条件（10分钟无任务）
            idle_minutes = idle_seconds / 60
            if idle_minutes >= self.idle_shutdown_minutes:
                logger.info(f"🔄 Instance {inst.name} idle for {idle_minutes:.0f}min, shutting down...")
                await self.auto_power_off(inst.instance_uuid)
    
    # ---- 快照 ----
    
    def get_snapshot(self) -> dict:
        """获取当前状态快照（包含队列信息）"""
        return {
            "total_instances": len(self.instances),
            "running": len(self.get_running_instances()),
            "idle": len(self.get_idle_instances()),
            "shutdown": len(self.get_shutdown_instances()),
            "queue_waiting": self._task_queue.waiting_count(),
            "instances": [inst.to_dict() for inst in self.instances.values()],
        }


# ========================================================================
# Global Singleton
# ========================================================================

_global_monitor: Optional[AutoScalingMonitor] = None


def get_global_monitor() -> AutoScalingMonitor:
    """获取全局 AutoScalingMonitor 单例"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = AutoScalingMonitor()
    return _global_monitor