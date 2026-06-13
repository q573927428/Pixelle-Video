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
Task Manager

In-memory task management for video generation jobs.
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from loguru import logger

from api.tasks.models import Task, TaskStatus, TaskType, TaskProgress, ConfirmationData
from pixelle_video.config import config_manager
from api.config import api_config


class TaskConfirmationTimeout(Exception):
    """Raised when user confirmation times out or is rejected."""
    pass


class TaskConcurrencyLimitError(Exception):
    """
    Raised when the task queue is full and a new task cannot be accepted.

    This typically happens when the number of concurrent RunningHub tasks
    has reached its maximum capacity (TASK_QUEUE_MAXED).
    """
    pass


class TaskManager:
    """
    Task manager for handling async video generation tasks
    
    Features:
    - In-memory storage (can be replaced with Redis later)
    - Task lifecycle management
    - Progress tracking
    - User confirmation support (when tasks need user input)
    - Auto cleanup of old tasks
    - Concurrent task limiting via semaphore
    """
    
    def __init__(self):
        self._tasks: Dict[str, Task] = {}
        self._task_futures: Dict[str, asyncio.Task] = {}
        self._confirmation_events: Dict[str, asyncio.Event] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

        # Semaphore to limit concurrent RunningHub workflow executions.
        # This prevents TASK_QUEUE_MAXED errors when multiple users submit
        # tasks simultaneously. Tasks exceeding the limit will be queued
        # and executed sequentially as slots become available.
        self._concurrency_semaphore: Optional[asyncio.Semaphore] = None

    def _get_max_concurrent(self) -> int:
        """Get the max concurrent tasks limit from the UI-configurable setting.
        
        Reads from config_manager's runninghub_concurrent_limit which
        users can change via the Settings page (stored in config.yaml).
        Falls back to 1 if not configured.
        """
        try:
            comfyui_cfg = config_manager.get_comfyui_config()
            return int(comfyui_cfg.get("runninghub_concurrent_limit", 1))
        except Exception:
            return 1

    async def start(self):
        """Start task manager and cleanup scheduler"""
        if self._running:
            logger.warning("Task manager already running")
            return
        
        self._running = True
        max_concurrent = self._get_max_concurrent()
        self._concurrency_semaphore = asyncio.Semaphore(max_concurrent)
        logger.info(f"✅ Task manager started (max concurrent tasks: {max_concurrent})")
        
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def stop(self):
        """Stop task manager and cancel all tasks"""
        self._running = False
        
        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Cancel all running tasks
        for task_id, future in self._task_futures.items():
            if not future.done():
                future.cancel()
                logger.info(f"Cancelled task: {task_id}")
        
        self._tasks.clear()
        self._task_futures.clear()
        self._confirmation_events.clear()
        self._concurrency_semaphore = None
        logger.info("✅ Task manager stopped")
    
    def get_concurrency_semaphore(self) -> asyncio.Semaphore:
        """Get the concurrency semaphore, creating it if not initialized"""
        if self._concurrency_semaphore is None:
            max_concurrent = self._get_max_concurrent()
            self._concurrency_semaphore = asyncio.Semaphore(max_concurrent)
        return self._concurrency_semaphore

    def create_task(
        self,
        task_type: TaskType,
        request_params: Optional[dict] = None
    ) -> Task:
        """
        Create a new task
        
        Args:
            task_type: Type of task
            request_params: Original request parameters
            
        Returns:
            Created task
        """
        task_id = str(uuid.uuid4())
        task = Task(
            task_id=task_id,
            task_type=task_type,
            status=TaskStatus.PENDING,
            request_params=request_params,
        )
        
        self._tasks[task_id] = task
        logger.info(f"Created task {task_id} ({task_type})")
        return task
    
    def add_warning(self, task_id: str, warning: str):
        """
        Add a warning message to the task (non-blocking info).
        
        Args:
            task_id: Task ID
            warning: Warning message to display to the user
        """
        task = self._tasks.get(task_id)
        if not task:
            return
        if warning not in task.warnings:
            task.warnings.append(warning)
            logger.warning(f"Task {task_id} warning: {warning}")
    
    async def request_confirmation(
        self,
        task_id: str,
        confirmation: ConfirmationData,
        timeout: float = 300.0,
    ) -> bool:
        """
        Request user confirmation for a pending task.
        
        Sets the task status to PENDING_CONFIRMATION and waits for the user
        to respond via the confirm/reject API endpoint.
        
        Args:
            task_id: Task ID
            confirmation: Confirmation data describing what needs user input
            timeout: Maximum wait time in seconds (default 5 minutes)
            
        Returns:
            True if user confirmed, False if rejected or timed out
            
        Raises:
            TaskConfirmationTimeout: If confirmation times out
        """
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        # Create event if not exists
        if task_id not in self._confirmation_events:
            self._confirmation_events[task_id] = asyncio.Event()
        
        event = self._confirmation_events[task_id]
        
        # Set task to confirmation-pending state
        task.status = TaskStatus.PENDING_CONFIRMATION
        task.confirmation = confirmation
        event.clear()
        
        logger.info(
            f"Task {task_id} waiting for user confirmation: "
            f"{confirmation.type} - {confirmation.message}"
        )
        
        # Wait for user response with timeout
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f"Task {task_id} confirmation timed out after {timeout}s")
            task.status = TaskStatus.RUNNING
            task.confirmation = None
            self._confirmation_events.pop(task_id, None)
            raise TaskConfirmationTimeout(
                f"User confirmation timed out after {timeout} seconds"
            )
        
        # Check confirmation result
        result = getattr(event, "_confirm_result", True)
        self._confirmation_events.pop(task_id, None)
        task.confirmation = None
        
        if result:
            task.status = TaskStatus.RUNNING
            logger.info(f"Task {task_id} user confirmed, resuming execution")
        else:
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()
            logger.info(f"Task {task_id} user rejected, cancelling task")
        
        return result
    
    def confirm_task(self, task_id: str, confirmed: bool = True) -> bool:
        """
        Respond to a pending confirmation request.
        
        Args:
            task_id: Task ID
            confirmed: True to continue, False to cancel
            
        Returns:
            True if confirmation was processed, False if task not awaiting confirmation
        """
        event = self._confirmation_events.get(task_id)
        if not event:
            return False
        
        setattr(event, "_confirm_result", confirmed)
        event.set()
        return True
    
    async def execute_task(
        self,
        task_id: str,
        coro_func: Callable,
        *args,
        **kwargs
    ):
        """
        Execute task asynchronously
        
        Args:
            task_id: Task ID
            coro_func: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
        """
        task = self._tasks.get(task_id)
        if not task:
            logger.error(f"Task {task_id} not found")
            return
        
        # Create async task
        async def _execute():
            try:
                task.status = TaskStatus.RUNNING
                task.started_at = datetime.now()
                logger.info(f"Task {task_id} started")
                
                # Execute the actual work
                result = await coro_func(*args, **kwargs)
                
                # Update task with result
                task.status = TaskStatus.COMPLETED
                task.result = result
                task.completed_at = datetime.now()
                logger.info(f"Task {task_id} completed")
                
            except TaskConfirmationTimeout:
                # Confirmation timed out - fail gracefully
                task.status = TaskStatus.FAILED
                task.error = "User confirmation timed out"
                task.completed_at = datetime.now()
                logger.error(f"Task {task_id} failed: confirmation timeout")
                
            except asyncio.CancelledError:
                task.status = TaskStatus.CANCELLED
                task.completed_at = datetime.now()
                logger.info(f"Task {task_id} cancelled")
                
            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                task.completed_at = datetime.now()
                logger.error(f"Task {task_id} failed: {e}")
        
        # Start execution
        future = asyncio.create_task(_execute())
        self._task_futures[task_id] = future

    async def execute_with_concurrency_limit(
        self,
        task_id: str,
        coro_func: Callable,
        *args,
        **kwargs
    ):
        """
        Execute task asynchronously with concurrency limiting.
        
        Uses a semaphore to limit the number of concurrent RunningHub
        workflow executions. Tasks that exceed the limit will be queued
        and executed sequentially as slots become available.
        
        Args:
            task_id: Task ID
            coro_func: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
        """
        task = self._tasks.get(task_id)
        if not task:
            logger.error(f"Task {task_id} not found")
            return

        semaphore = self.get_concurrency_semaphore()

        async def _execute_with_semaphore():
            try:
                # Wait for a semaphore slot before starting execution
                logger.info(f"Task {task_id} waiting for concurrency slot (available: {semaphore._value})")
                async with semaphore:
                    task.status = TaskStatus.RUNNING
                    task.started_at = datetime.now()
                    logger.info(f"Task {task_id} acquired concurrency slot, started")
                    
                    result = await coro_func(*args, **kwargs)
                    
                    task.status = TaskStatus.COMPLETED
                    task.result = result
                    task.completed_at = datetime.now()
                    logger.info(f"Task {task_id} completed, released concurrency slot")
                    
            except TaskConfirmationTimeout:
                task.status = TaskStatus.FAILED
                task.error = "User confirmation timed out"
                task.completed_at = datetime.now()
                logger.error(f"Task {task_id} failed: confirmation timeout")
                
            except asyncio.CancelledError:
                task.status = TaskStatus.CANCELLED
                task.completed_at = datetime.now()
                logger.info(f"Task {task_id} cancelled")
                
            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                task.completed_at = datetime.now()
                logger.error(f"Task {task_id} failed: {e}")

        future = asyncio.create_task(_execute_with_semaphore())
        self._task_futures[task_id] = future
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        return self._tasks.get(task_id)
    
    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        limit: int = 100
    ) -> List[Task]:
        """
        List tasks with optional filtering
        
        Args:
            status: Filter by status
            limit: Maximum number of tasks to return
            
        Returns:
            List of tasks
        """
        tasks = list(self._tasks.values())
        
        if status:
            tasks = [t for t in tasks if t.status == status]
        
        # Sort by created_at descending
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        
        return tasks[:limit]
    
    def update_progress(
        self,
        task_id: str,
        current: int,
        total: int,
        message: str = ""
    ):
        """
        Update task progress
        
        Args:
            task_id: Task ID
            current: Current progress
            total: Total steps
            message: Progress message
        """
        task = self._tasks.get(task_id)
        if not task:
            return
        
        percentage = (current / total * 100) if total > 0 else 0
        task.progress = TaskProgress(
            current=current,
            total=total,
            percentage=percentage,
            message=message
        )
    
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running task
        
        Args:
            task_id: Task ID
            
        Returns:
            True if cancelled, False otherwise
        """
        task = self._tasks.get(task_id)
        if not task:
            return False
        
        # Do not cancel already-terminal tasks
        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            return False
        
        # Handle PENDING_CONFIRMATION: trigger confirmation event so pipeline
        # can cleanly exit instead of being forcefully cancelled mid-process
        if task.status == TaskStatus.PENDING_CONFIRMATION:
            event = self._confirmation_events.get(task_id)
            if event:
                setattr(event, "_confirm_result", False)
                event.set()

        # Cancel future if running
        future = self._task_futures.get(task_id)
        if future and not future.done():
            future.cancel()
        
        # Update task status
        task.status = TaskStatus.CANCELLED
        task.completed_at = datetime.now()
        task.confirmation = None
        self._confirmation_events.pop(task_id, None)
        logger.info(f"Cancelled task {task_id}")
        return True
    
    async def _cleanup_loop(self):
        """Periodically clean up old completed tasks"""
        while self._running:
            try:
                await asyncio.sleep(api_config.task_cleanup_interval)
                self._cleanup_old_tasks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    def _cleanup_old_tasks(self):
        """Remove old completed/failed tasks"""
        cutoff_time = datetime.now() - timedelta(seconds=api_config.task_retention_time)
        
        tasks_to_remove = []
        for task_id, task in self._tasks.items():
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                if task.completed_at and task.completed_at < cutoff_time:
                    tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            del self._tasks[task_id]
            if task_id in self._task_futures:
                del self._task_futures[task_id]
            self._confirmation_events.pop(task_id, None)
        
        if tasks_to_remove:
            logger.info(f"Cleaned up {len(tasks_to_remove)} old tasks")


# Global task manager instance
task_manager = TaskManager()