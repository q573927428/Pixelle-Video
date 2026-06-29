"""
Instance Management API Router - AutoDL 实例管理与自动扩缩容

提供 AutoDL 实例的全生命周期管理 + 镜像机 ComfyUI 控制 API。
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Any, Optional

from api.auth.dependencies import require_admin
from api.auth.schemas import UserInfo
from pixelle_video.services.instance_manager import (
    AutoDLInstanceManager,
    MirrorComfyUIController,
    AutoScalingMonitor,
    InstanceState,
    get_global_monitor,
)

from pixelle_video.config import config_manager

router = APIRouter(tags=["instances"])


# ========================================================================
# Request / Response Models
# ========================================================================

class TokenRequest(BaseModel):
    token: str


class InstanceActionRequest(BaseModel):
    token: str
    instance_uuid: str


class InstanceListRequest(BaseModel):
    token: str
    page_index: int = 1
    page_size: int = 50


class CreateInstanceRequest(BaseModel):
    token: str
    gpu_spec_uuid: str
    req_gpu_amount: int = 1
    instance_name: str = "并发生成-镜像机"
    expand_system_disk_by_gb: int = 0


class MirrorActionRequest(BaseModel):
    mirror_url: str


class MirrorVersionSwitchRequest(BaseModel):
    mirror_url: str
    version: str


class AutoScalingConfigRequest(BaseModel):
    token: str = ""
    idle_shutdown_minutes: Optional[int] = None
    idle_release_days: Optional[int] = None
    check_interval_seconds: Optional[int] = None


# ========================================================================
# Helper: Get panel base URL from configuration
# ========================================================================

def _get_panel_base_url() -> str:
    """从配置中获取远程 ComfyUI 面板地址作为 BASE_URL"""
    comfyui_cfg = config_manager.get_comfyui_config()
    rc = comfyui_cfg.get("remote_comfy", {})
    base_url = rc.get("base_url", "")
    if not base_url:
        raise HTTPException(status_code=400, detail="未配置远程 ComfyUI 面板地址，请先在系统配置中设置")
    return base_url


def _get_instance_manager() -> AutoDLInstanceManager:
    """获取 AutoDL 实例管理器"""
    base_url = _get_panel_base_url()
    return AutoDLInstanceManager(base_url)


def _get_mirror_controller() -> MirrorComfyUIController:
    """获取镜像机控制器"""
    base_url = _get_panel_base_url()
    return MirrorComfyUIController(base_url)


# ========================================================================
# AutoDL Instance Management Endpoints
# ========================================================================

@router.post("/instances/list")
async def list_instances(
    request: InstanceListRequest,
    admin: UserInfo = Depends(require_admin),
):
    """
    分页列出账号下的所有 AutoDL 实例
    """
    try:
        mgr = _get_instance_manager()
        result = await mgr.list_instances(
            token=request.token,
            page_index=request.page_index,
            page_size=request.page_size,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/instances/status")
async def get_instance_status(
    request: InstanceActionRequest,
    admin: UserInfo = Depends(require_admin),
):
    """
    查询单个实例的开关机/计费状态
    """
    try:
        mgr = _get_instance_manager()
        result = await mgr.get_instance_status(
            token=request.token,
            instance_uuid=request.instance_uuid,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/instances/snapshot")
async def get_instance_snapshot(
    token: str = Query(..., description="AutoDL Token"),
    instance_uuid: str = Query(..., description="实例 UUID"),
    admin: UserInfo = Depends(require_admin),
):
    """
    查询实例完整快照（含 service_6008_domain，即镜像机面板地址）
    """
    try:
        mgr = _get_instance_manager()
        result = await mgr.get_instance_snapshot(
            token=token,
            instance_uuid=instance_uuid,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/instances/power-on")
async def power_on_instance(
    request: InstanceActionRequest,
    admin: UserInfo = Depends(require_admin),
):
    """
    开机指定实例
    """
    try:
        mgr = _get_instance_manager()
        result = await mgr.power_on(
            token=request.token,
            instance_uuid=request.instance_uuid,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/instances/power-off")
async def power_off_instance(
    request: InstanceActionRequest,
    admin: UserInfo = Depends(require_admin),
):
    """
    关机指定实例（停止计费，数据和实例保留）
    """
    try:
        mgr = _get_instance_manager()
        result = await mgr.power_off(
            token=request.token,
            instance_uuid=request.instance_uuid,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/instances/release")
async def release_instance(
    request: InstanceActionRequest,
    admin: UserInfo = Depends(require_admin),
):
    """
    释放（销毁）实例（必须先关机；释放后数据丢失）
    """
    try:
        mgr = _get_instance_manager()
        result = await mgr.release_instance(
            token=request.token,
            instance_uuid=request.instance_uuid,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/instances/create")
async def create_instance(
    request: CreateInstanceRequest,
    admin: UserInfo = Depends(require_admin),
):
    """
    基于 Zealman 公共镜像创建一台新 AutoDL 实例
    """
    try:
        mgr = _get_instance_manager()
        result = await mgr.create_instance(
            token=request.token,
            gpu_spec_uuid=request.gpu_spec_uuid,
            req_gpu_amount=request.req_gpu_amount,
            instance_name=request.instance_name,
            expand_system_disk_by_gb=request.expand_system_disk_by_gb,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========================================================================
# Mirror ComfyUI Control Endpoints
# ========================================================================

@router.post("/instances/mirror/start")
async def mirror_start_comfyui(
    request: MirrorActionRequest,
    admin: UserInfo = Depends(require_admin),
):
    """
    远程启动镜像机的 ComfyUI
    """
    try:
        ctrl = _get_mirror_controller()
        result = await ctrl.start_comfyui(request.mirror_url)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/instances/mirror/stop")
async def mirror_stop_comfyui(
    request: MirrorActionRequest,
    admin: UserInfo = Depends(require_admin),
):
    """
    停止镜像机的 ComfyUI 进程（不影响 AutoDL 计费）
    """
    try:
        ctrl = _get_mirror_controller()
        result = await ctrl.stop_comfyui(request.mirror_url)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/instances/mirror/comfy-status")
async def mirror_comfy_status(
    mirror_url: str = Query(..., description="镜像机面板地址"),
    admin: UserInfo = Depends(require_admin),
):
    """
    查询镜像机 ComfyUI 运行状态
    
    返回 running/starting 等状态信息
    """
    try:
        ctrl = _get_mirror_controller()
        result = await ctrl.get_comfy_status(mirror_url)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/instances/mirror/interrupt")
async def mirror_interrupt(
    request: MirrorActionRequest,
    admin: UserInfo = Depends(require_admin),
):
    """
    中断镜像机 ComfyUI 当前任务
    """
    try:
        ctrl = _get_mirror_controller()
        result = await ctrl.interrupt(request.mirror_url)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/instances/mirror/free")
async def mirror_free_memory(
    request: MirrorActionRequest,
    admin: UserInfo = Depends(require_admin),
):
    """
    释放镜像机显存（卸载模型 + 清显存）
    """
    try:
        ctrl = _get_mirror_controller()
        result = await ctrl.free_memory(request.mirror_url)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/instances/mirror/versions")
async def mirror_versions(
    mirror_url: str = Query(..., description="镜像机面板地址"),
    admin: UserInfo = Depends(require_admin),
):
    """
    查询镜像机可切换的 ComfyUI 版本列表
    """
    try:
        ctrl = _get_mirror_controller()
        result = await ctrl.get_versions(mirror_url)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/instances/mirror/switch-version")
async def mirror_switch_version(
    request: MirrorVersionSwitchRequest,
    admin: UserInfo = Depends(require_admin),
):
    """
    切换镜像机的 ComfyUI 版本
    
    推荐顺序：先 stop → switch-version → 再 start
    """
    try:
        ctrl = _get_mirror_controller()
        result = await ctrl.switch_version(
            mirror_url=request.mirror_url,
            version=request.version,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/instances/mirror/probe")
async def mirror_probe(
    mirror_url: str = Query(..., description="镜像机面板地址"),
    admin: UserInfo = Depends(require_admin),
):
    """
    探测镜像机连通性（面板可达 + ComfyUI 状态）
    """
    try:
        ctrl = _get_mirror_controller()
        result = await ctrl.probe(mirror_url)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========================================================================
# Auto-Scaling Monitor Endpoints
# ========================================================================

@router.post("/instances/auto-scaling/start")
async def start_auto_scaling(
    request: AutoScalingConfigRequest,
    admin: UserInfo = Depends(require_admin),
):
    """
    启动自动扩缩容监控服务
    """
    try:
        base_url = _get_panel_base_url()
        monitor = get_global_monitor()
        
        # 更新配置
        if request.idle_shutdown_minutes is not None:
            monitor.idle_shutdown_minutes = request.idle_shutdown_minutes
        if request.idle_release_days is not None:
            monitor.idle_release_days = request.idle_release_days
        if request.check_interval_seconds is not None:
            monitor.check_interval_seconds = request.check_interval_seconds
        
        monitor.panel_base_url = base_url
        
        # 使用请求传入的 AutoDL Token（用户在前端输入的）
        await monitor.start(token=request.token)
        return {"success": True, "message": "自动扩缩容服务已启动"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/instances/auto-scaling/stop")
async def stop_auto_scaling(
    admin: UserInfo = Depends(require_admin),
):
    """
    停止自动扩缩容监控服务
    """
    try:
        monitor = get_global_monitor()
        await monitor.stop()
        return {"success": True, "message": "自动扩缩容服务已停止"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/instances/auto-scaling/status")
async def get_auto_scaling_status(
    admin: UserInfo = Depends(require_admin),
):
    """
    获取自动扩缩容状态快照
    """
    try:
        monitor = get_global_monitor()
        snapshot = monitor.get_snapshot()
        return {
            "success": True,
            "running": monitor.is_running(),
            "idle_shutdown_minutes": monitor.idle_shutdown_minutes,
            "idle_release_days": monitor.idle_release_days,
            "check_interval_seconds": monitor.check_interval_seconds,
            "total_instances": snapshot.get("total_instances", 0),
            "running_instances": snapshot.get("running", 0),
            "idle_instances": snapshot.get("idle", 0),
            "shutdown_instances": snapshot.get("shutdown", 0),
            "instances": snapshot.get("instances", []),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/instances/auto-scaling/ensure-ready")
async def auto_scaling_ensure_ready(
    token: str = Query("", description="AutoDL Token（可选，默认从配置读取）"),
    admin: UserInfo = Depends(require_admin),
):
    """
    确保有一台就绪的镜像机可用
    
    如果空闲实例不足，自动开机并启动 ComfyUI
    """
    try:
        monitor = get_global_monitor()
        
        # 如果还没启动，先尝试启动
        comfyui_cfg = config_manager.get_comfyui_config()
        rc = comfyui_cfg.get("remote_comfy", {})
        base_url = rc.get("base_url", "")
        if base_url:
            monitor.panel_base_url = base_url
        
        actual_token = token or comfyui_cfg.get("runninghub_api_key", "")
        
        result = await monitor.ensure_ready_instance(token=actual_token)
        if result:
            mirror_url, instance_uuid = result
            return {
                "success": True,
                "mirror_url": mirror_url,
                "instance_uuid": instance_uuid,
                "message": "就绪的镜像机可用",
            }
        else:
            return {
                "success": False,
                "mirror_url": None,
                "instance_uuid": None,
                "message": "无法获取就绪的镜像机",
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
