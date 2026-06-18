"""
Task management endpoints

Endpoints for managing async tasks (checking status, canceling, etc.)
"""

import httpx
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from loguru import logger

from pixelle_video.config import config_manager

from api.tasks import task_manager, Task, TaskStatus
from api.dependencies import PixelleVideoDep
from api.auth.dependencies import get_current_user
from api.auth.schemas import UserInfo

router = APIRouter(prefix="/tasks", tags=["Tasks"])


class ConfirmRequest(BaseModel):
    confirmed: bool = True


class ConfirmResponse(BaseModel):
    success: bool
    message: str


@router.get("", response_model=List[Task])
async def list_tasks(
    status: Optional[TaskStatus] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of tasks"),
    current_user: Optional[UserInfo] = Depends(get_current_user),
):
    """
    List tasks
    
    Retrieve list of tasks with optional filtering.
    Normal users only see their own tasks; admins see all.
    
    - **status**: Optional filter by status (pending/running/completed/failed/cancelled)
    - **limit**: Maximum number of tasks to return (default 100)
    
    Returns list of tasks sorted by creation time (newest first).
    """
    try:
        is_admin = current_user is not None and current_user.role == "admin"
        # Normalize user_id to str for consistent comparison with task.user_id (which is str)
        raw_user_id = current_user.id if current_user else None
        user_id = str(raw_user_id) if raw_user_id is not None else None
        if is_admin:
            user_id = None
        tasks = task_manager.list_tasks(status=status, limit=limit, user_id=user_id, is_admin=is_admin)
        return tasks
        
    except Exception as e:
        logger.error(f"List tasks error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def list_task_history(
    pixelle_video: PixelleVideoDep,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status"),
    current_user: Optional[UserInfo] = Depends(get_current_user),
):
    """
    List persisted task history (survives server restarts).
    Reads from the filesystem index built by PersistenceService.
    Each user can only see their own task history.
    Unauthenticated users see nothing.
    """
    try:
        if not pixelle_video.history:
            return {"tasks": [], "total": 0, "page": page, "page_size": page_size, "total_pages": 0}

        # Unauthenticated users see no history
        if current_user is None:
            return {"tasks": [], "total": 0, "page": page, "page_size": page_size, "total_pages": 0}

        # Admin can see all tasks (including legacy tasks with no user_id)
        if current_user.role == "admin":
            user_id = None  # No filtering, show all
        else:
            user_id = current_user.id  # Normal users only see their own

        result = await pixelle_video.history.get_task_list(
            page=page,
            page_size=page_size,
            status=status or None,
            user_id=user_id,
        )
        return result

    except Exception as e:
        logger.error(f"List task history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/history/{task_id}")
async def delete_task_history(
    task_id: str,
    pixelle_video: PixelleVideoDep,
    current_user: Optional[UserInfo] = Depends(get_current_user),
):
    """
    Delete a task from history permanently (removes all files).
    Only the owner of the task can delete it.
    """
    try:
        if not pixelle_video.history:
            raise HTTPException(status_code=503, detail="History service not available")

        if current_user is None:
            raise HTTPException(status_code=401, detail="请先登录")

        # Get task detail to verify ownership
        detail = await pixelle_video.history.get_task_detail(task_id)
        if not detail:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found in history")

        # Check ownership: only task owner or admin can delete
        task_metadata = detail.get("metadata", {})
        task_user_id = task_metadata.get("user_id")
        is_owner = task_user_id is None or (task_user_id == current_user.id)
        if not is_owner and current_user.role != "admin":
            raise HTTPException(
                status_code=403,
                detail="您没有权限删除此任务",
            )

        success = await pixelle_video.history.delete_task(task_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found in history")

        return {
            "success": True,
            "message": f"Task {task_id} deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete task history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{task_id}")
async def get_task_history_detail(
    task_id: str,
    pixelle_video: PixelleVideoDep,
    current_user: Optional[UserInfo] = Depends(get_current_user),
):
    """
    Get full detail of a persisted task including storyboard.
    Only the owner of the task can view the detail.
    """
    try:
        if not pixelle_video.history:
            raise HTTPException(status_code=503, detail="History service not available")

        if current_user is None:
            raise HTTPException(status_code=401, detail="请先登录")

        detail = await pixelle_video.history.get_task_detail(task_id)
        if not detail:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found in history")

        # Check ownership: only task owner or admin can view detail
        task_metadata = detail.get("metadata", {})
        task_user_id = task_metadata.get("user_id")
        is_owner = task_user_id is None or (task_user_id == current_user.id)
        if not is_owner and current_user.role != "admin":
            raise HTTPException(
                status_code=403,
                detail="您没有权限查看此任务详情",
            )

        return detail

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get task history detail error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{task_id}/confirm", response_model=ConfirmResponse)
async def confirm_task(task_id: str, body: ConfirmRequest):
    """
    Confirm or reject a pending user confirmation request.
    
    When a task is in PENDING_CONFIRMATION status (e.g., audio too long),
    this endpoint allows the user to confirm (continue) or reject (cancel).
    
    - **task_id**: Task ID
    - **body.confirmed**: True to continue, False to cancel
    """
    try:
        task = task_manager.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
        if task.status != TaskStatus.PENDING_CONFIRMATION:
            raise HTTPException(
                status_code=409,
                detail=f"Task {task_id} is not awaiting confirmation (status={task.status})"
            )
        
        success = task_manager.confirm_task(task_id, confirmed=body.confirmed)
        if not success:
            raise HTTPException(status_code=409, detail=f"Task {task_id} confirmation already processed")
        
        action = "confirmed" if body.confirmed else "rejected"
        return ConfirmResponse(
            success=True,
            message=f"Task {task_id} {action} successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Confirm task error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{task_id}", response_model=Task)
async def get_task(task_id: str):
    """
    Get task details
    
    Retrieve detailed information about a specific task.
    
    - **task_id**: Task ID
    
    Returns task details including status, progress, and result (if completed).
    """
    try:
        task = task_manager.get_task(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
        return task
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get task error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{task_id}")
async def cancel_task(
    task_id: str,
    current_user: Optional[UserInfo] = Depends(get_current_user),
):
    """
    Cancel task
    
    Cancel a running or pending task.
    Only the task owner or admin can cancel a task.
    If the task is running on RunningHub, also cancels it there.
    
    - **task_id**: Task ID
    
    Returns success status.
    """
    try:
        task = task_manager.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        # Check ownership: only task owner or admin can cancel
        if current_user:
            # task.user_id is stored as str, current_user.id is int — compare both types
            task_user_id = task.user_id
            current_user_id = str(current_user.id)
            is_owner = task_user_id is None or task_user_id == current_user_id
            if not is_owner and current_user.role != "admin":
                raise HTTPException(status_code=403, detail="您没有权限取消此任务")
        else:
            # Unauthenticated users cannot cancel tasks with user_id set
            if task.user_id is not None:
                raise HTTPException(status_code=401, detail="请先登录")

        # Try to cancel on RunningHub using official openapi endpoint
        runninghub_id = task_manager.get_runninghub_task_id(task_id)
        if runninghub_id:
            try:
                comfyui_cfg = config_manager.get_comfyui_config()
                rh_api_key = comfyui_cfg.get("runninghub_api_key") or ""
                rh_url = "https://www.runninghub.cn"
                payload = {
                    "apiKey": rh_api_key,
                    "taskId": runninghub_id,
                }
                async with httpx.AsyncClient(timeout=10) as client:
                    cancel_resp = await client.post(
                        f"{rh_url}/task/openapi/cancel",
                        json=payload,
                        headers={
                            "Host": "www.runninghub.cn",
                            "Authorization": f"Bearer {rh_api_key}",
                            "Content-Type": "application/json",
                        },
                    )
                    if cancel_resp.is_success:
                        logger.info(f"RunningHub task {runninghub_id} cancelled successfully via openapi")
                    else:
                        logger.warning(f"RunningHub openapi cancel returned {cancel_resp.status_code}: {cancel_resp.text}")
            except Exception as rh_e:
                logger.warning(f"Failed to cancel RunningHub task {runninghub_id}: {rh_e}")

        # Cancel local task
        success = task_manager.cancel_task(task_id)
        if not success:
            # Task might already be in terminal state (completed/failed/cancelled)
            if task:
                logger.info(f"Task {task_id} already in terminal state ({task.status}), returning success")
                return {
                    "success": True,
                    "message": f"Task {task_id} is already in terminal state: {task.status.value}"
                }
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
        return {
            "success": True,
            "message": f"Task {task_id} cancelled successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cancel task error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
