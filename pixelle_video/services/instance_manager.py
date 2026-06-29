"""
Instance Manager - AutoDL Instance Management & Auto-Scaling Service

基于 zealman API (v8.8) docs 实现 AutoDL 实例管理、镜像机 ComfyUI 控制、空闲监控与自动扩缩容。

功能：
1. AutoDL 实例管理：list/status/snapshot/power_on/power_off/release/create
2. 镜像机 ComfyUI 控制：start/stop/comfy-status/versions/switch-version/interrupt/free
3. 任务调度：空闲检测、自动开机、自动关机、自动释放
4. 空闲监控：无任务时自动 power_off，连续7天无任务自动释放
"""

import asyncio
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
        data = resp.json()
        if not data.get("success"):
            raise InstanceActionError(f"List instances failed: {data.get('message', 'unknown error')}")
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
    ):
        self.panel_base_url = panel_base_url
        self.idle_shutdown_minutes = idle_shutdown_minutes
        self.idle_release_days = idle_release_days
        self.check_interval_seconds = check_interval_seconds
        # 主控机实例 UUID（永远不会自动关机/释放）
        self._master_instance_uuid: Optional[str] = None
        
        # 实例状态跟踪
        self.instances: dict[str, InstanceState] = {}  # instance_uuid -> InstanceState
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        
        # 默认 AutoDL Token (从配置读取)
        self._default_token: str = ""
        
        # 组件
        self._instance_manager: Optional[AutoDLInstanceManager] = None
        self._mirror_controller: Optional[MirrorComfyUIController] = None
        
        # 日志目录
        self._log_dir = Path("output") / "instance_logs"
        self._log_dir.mkdir(parents=True, exist_ok=True)
    
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
        logger.info(
            f"✅ AutoScalingMonitor started "
            f"(idle_shutdown={self.idle_shutdown_minutes}min, "
            f"idle_release={self.idle_release_days}d)"
        )
    
    async def stop(self):
        """停止监控"""
        self._running = False
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
    
    # ---- 任务状态更新 ----
    
    def on_task_submitted(self, instance_uuid: str):
        """任务提交到实例时调用"""
        inst = self.instances.get(instance_uuid)
        if inst:
            inst.current_jobs += 1
            inst.last_active_time = datetime.now()
    
    def on_task_completed(self, instance_uuid: str):
        """任务完成时调用"""
        inst = self.instances.get(instance_uuid)
        if inst:
            inst.current_jobs = max(0, inst.current_jobs - 1)
            inst.total_jobs_completed += 1
            inst.last_active_time = datetime.now()
    
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
    ) -> Optional[str]:
        """
        自动开机一台关机中的镜像机
        
        Returns:
            开机的实例 UUID，如果没有可用关机实例返回 None
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
                    # AutoDL API 返回的字段是 uuid 而不是 instance_uuid
                    uuid = item.get("uuid") or item.get("instance_uuid") or ""
                    if not uuid or uuid in self.instances:
                        continue
                    # 检测主控机（从面板 base_url 提取的 UUID）
                    is_master = uuid == self._master_instance_uuid
                    self.register_instance(InstanceState(
                        instance_uuid=uuid,
                        status=item.get("status", "shutdown"),
                        name=item.get("name") or item.get("machine_alias") or uuid,
                        gpu_name=item.get("gpu_name") or item.get("gpu_spec_uuid", ""),
                        auto_managed=not is_master,  # 主控机不会自动管理
                    ))
                shutdown_instances = self.get_shutdown_instances()
            except Exception as e:
                logger.error(f"Failed to list instances for auto power-on: {e}")
                return None
        
        if not shutdown_instances:
            logger.warning("No shutdown instances available for auto power-on")
            return None
        
        # 选一台关机最久的
        target = min(shutdown_instances, key=lambda x: x.created_at)
        
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
            镜像机面板 URL，失败返回 None
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
        
        # 2. 启动 ComfyUI
        if start_comfyui:
            logger.info(f"🚀 Starting ComfyUI on {mirror_url}")
            try:
                await self._mirror_controller.start_comfyui(mirror_url)
                inst.comfy_status = "starting"
                
                # 等待 ComfyUI 就绪
                ready = await self._mirror_controller.wait_for_comfy_ready(mirror_url)
                if ready:
                    inst.comfy_status = "running"
                    logger.info(f"✅ ComfyUI ready on {mirror_url}")
                else:
                    logger.warning(f"⚠️ ComfyUI start timeout on {mirror_url}")
                    inst.comfy_status = "stopped"
            except Exception as e:
                logger.error(f"Failed to start ComfyUI on {mirror_url}: {e}")
                inst.comfy_status = "stopped"
        
        return mirror_url
    
    # ---- 自动关机 ----
    
    async def auto_power_off(self, instance_uuid: str, token: str = ""):
        """自动关机指定实例"""
        token = token or self._default_token
        inst = self.instances.get(instance_uuid)
        if not inst:
            return
        
        # 冷却期检查：3分钟内不重复尝试关机同一实例
        now = datetime.now()
        if inst._last_shutdown_attempt:
            cooldown_elapsed = (now - inst._last_shutdown_attempt).total_seconds()
            if cooldown_elapsed < 180:  # 3 分钟冷却期
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
            # 即使 API 返回错误，也标记为已关机，防止无限重试
            logger.error(f"Power off failed for {instance_uuid}: {e}")
            logger.warning(f"⚠️ Marking instance {instance_uuid} as shutdown despite error to prevent retry loop")
            inst.status = "shutdown"
            inst.mirror_url = ""
            inst.power_on_time = None
    
    # ---- 自动释放 ----
    
    async def auto_release(self, instance_uuid: str, token: str = ""):
        """自动释放（销毁）实例"""
        token = token or self._default_token
        inst = self.instances.get(instance_uuid)
        if not inst:
            return
        
        # 冷却期检查：5分钟内不重复尝试释放同一实例
        now = datetime.now()
        if inst._last_shutdown_attempt:
            cooldown_elapsed = (now - inst._last_shutdown_attempt).total_seconds()
            if cooldown_elapsed < 300:  # 5 分钟冷却期
                logger.warning(f"⏳ Instance {instance_uuid} release attempted {cooldown_elapsed:.0f}s ago, skipping (cooldown)")
                return
        
        inst._last_shutdown_attempt = now
        logger.warning(f"🔥 Auto-releasing instance {inst.name} ({instance_uuid}) - idle > {self.idle_release_days}d")
        
        # 先关机
        if inst.status == "running":
            await self.auto_power_off(instance_uuid, token)
        
        try:
            await self._instance_manager.release_instance(token, instance_uuid)
            self.unregister_instance(instance_uuid)
            logger.info(f"✅ Instance {instance_uuid} released")
        except Exception as e:
            logger.error(f"Release instance failed for {instance_uuid}: {e}")
    
    # ---- 智能扩缩容主逻辑 ----
    
    async def ensure_ready_instance(self, token: str = "") -> Optional[str]:
        """
        核心方法：确保有一台就绪的镜像机可用。
        
        1. 检查是否有空闲运行中的实例（ComfyUI running）
        2. 有 -> 返回其 mirror_url
        3. 没有 -> 尝试自动开机一台
        4. 等待开机 -> 启动 ComfyUI -> 返回 mirror_url
        
        Returns:
            就绪的镜像机面板 URL，如果无法获取返回 None
        """
        token = token or self._default_token
        
        # 1. 找空闲实例
        idle = self.get_idle_instances()
        if idle:
            target = idle[0]
            logger.info(f"✅ Found idle instance {target.name}: {target.mirror_url}")
            return target.mirror_url
        
        # 2. 找 running 中有任务的实例（看是否还有能力接收）
        running = self.get_running_instances()
        if running:
            # 如果 running 实例很多且任务少，选任务最少的
            min_jobs = min(inst.current_jobs for inst in running)
            if min_jobs < 2:
                target = [i for i in running if i.current_jobs == min_jobs][0]
                logger.info(f"✅ Using busy-but-available instance {target.name} (jobs={target.current_jobs})")
                return target.mirror_url
        
        # 3. 尝试自动开机
        logger.info("🔄 No ready instance, trying auto power-on...")
        instance_uuid = await self.auto_power_on(token)
        if not instance_uuid:
            logger.error("❌ No instance available for auto power-on")
            return None
        
        # 4. 等待就绪
        mirror_url = await self.wait_and_setup_instance(instance_uuid, token)
        return mirror_url
    
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
        """检查所有实例的空间状态，执行关机/释放"""
        now = datetime.now()
        
        for inst in list(self.instances.values()):
            if inst.status != "running":
                continue
            if inst.current_jobs > 0:
                continue  # 还有任务在跑
            
            idle_seconds = (now - inst.last_active_time).total_seconds()
            idle_days = (now - inst.created_at).total_seconds() / 86400
            
            # 检查是否满足释放条件（7天无任务）
            if idle_days >= self.idle_release_days:
                logger.info(f"🔄 Instance {inst.name} idle for {idle_days:.1f}d, releasing...")
                await self.auto_release(inst.instance_uuid)
                continue
            
            # 检查是否满足关机条件（10分钟无任务）
            idle_minutes = idle_seconds / 60
            if idle_minutes >= self.idle_shutdown_minutes and inst.auto_managed:
                logger.info(f"🔄 Instance {inst.name} idle for {idle_minutes:.0f}min, shutting down...")
                await self.auto_power_off(inst.instance_uuid)
    
    # ---- 快照 ----
    
    def get_snapshot(self) -> dict:
        """获取当前状态快照"""
        return {
            "total_instances": len(self.instances),
            "running": len(self.get_running_instances()),
            "idle": len(self.get_idle_instances()),
            "shutdown": len(self.get_shutdown_instances()),
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