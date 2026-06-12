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
Task management endpoints

Endpoints for managing async tasks (checking status, canceling, etc.)
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from api.tasks import task_manager, Task, TaskStatus
from api.dependencies import PixelleVideoDep

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get("", response_model=List[Task])
async def list_tasks(
    status: Optional[TaskStatus] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of tasks")
):
    """
    List tasks
    
    Retrieve list of tasks with optional filtering.
    
    - **status**: Optional filter by status (pending/running/completed/failed/cancelled)
    - **limit**: Maximum number of tasks to return (default 100)
    
    Returns list of tasks sorted by creation time (newest first).
    """
    try:
        tasks = task_manager.list_tasks(status=status, limit=limit)
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
):
    """
    List persisted task history (survives server restarts).
    Reads from the filesystem index built by PersistenceService.
    """
    try:
        if not pixelle_video.history:
            return {"tasks": [], "total": 0, "page": page, "page_size": page_size, "total_pages": 0}

        result = await pixelle_video.history.get_task_list(
            page=page,
            page_size=page_size,
            status=status or None,
        )
        return result

    except Exception as e:
        logger.error(f"List task history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{task_id}")
async def get_task_history_detail(
    task_id: str,
    pixelle_video: PixelleVideoDep,
):
    """
    Get full detail of a persisted task including storyboard.
    """
    try:
        if not pixelle_video.history:
            raise HTTPException(status_code=503, detail="History service not available")

        detail = await pixelle_video.history.get_task_detail(task_id)
        if not detail:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found in history")

        return detail

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get task history detail error: {e}")
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
async def cancel_task(task_id: str):
    """
    Cancel task
    
    Cancel a running or pending task.
    
    - **task_id**: Task ID
    
    Returns success status.
    """
    try:
        success = task_manager.cancel_task(task_id)
        
        if not success:
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