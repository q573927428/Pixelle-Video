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
Video generation endpoints

Supports both synchronous and asynchronous video generation.
"""

import os
from fastapi import APIRouter, Depends, HTTPException, Request
from loguru import logger

from api.dependencies import PixelleVideoDep
from api.schemas.video import (
    VideoGenerateRequest,
    VideoGenerateResponse,
    VideoGenerateAsyncResponse,
    VideoBatchGenerateRequest,
    VideoBatchGenerateResponse,
)
from api.tasks import task_manager, TaskType
from api.auth.dependencies import check_daily_limit, increment_daily_usage
from api.auth.schemas import UserInfo, UserDailyUsage

router = APIRouter(prefix="/video", tags=["Video Generation"])


def path_to_url(request: Request, file_path: str) -> str:
    """
    Convert file path to accessible URL
    
    Handles both absolute and relative paths, extracting the path relative
    to the output directory for URL construction.
    
    Args:
        request: FastAPI Request object (provides base_url from actual request)
        file_path: Absolute or relative file path
    
    Returns:
        Full URL to access the file
    
    Examples:
        Windows: G:\\...\\output\\20251205_233630_c939\\final.mp4
              -> http://localhost:8000/api/files/20251205_233630_c939/final.mp4
        
        Linux:   /home/user/.../output/20251205_233630_c939/final.mp4
              -> http://localhost:8000/api/files/20251205_233630_c939/final.mp4
        
        Domain:  With domain request -> https://your-domain.com/api/files/...
    """
    from pathlib import Path
    import os
    
    # Normalize path separators to forward slashes first (for cross-platform compatibility)
    file_path = file_path.replace("\\", "/")
    
    # Check if it's an absolute path (works for both Windows and Linux)
    is_absolute = os.path.isabs(file_path) or Path(file_path).is_absolute()
    
    if is_absolute:
        # Find "output" in the path and get everything after it
        # Split by / to work with normalized paths
        parts = file_path.split("/")
        try:
            output_idx = parts.index("output")
            # Get all parts after "output" and join them
            relative_parts = parts[output_idx + 1:]
            file_path = "/".join(relative_parts)
        except ValueError:
            # If "output" not in path, use the filename only
            file_path = Path(file_path).name
    else:
        # If relative path starting with "output/", remove it
        if file_path.startswith("output/"):
            file_path = file_path[7:]  # Remove "output/"
    
    # Build URL using request's base_url (automatically matches the request host)
    base_url = str(request.base_url).rstrip('/')
    return f"{base_url}/api/files/{file_path}"


@router.post("/generate/sync", response_model=VideoGenerateResponse)
async def generate_video_sync(
    request_body: VideoGenerateRequest,
    pixelle_video: PixelleVideoDep,
    request: Request,
    _user: UserInfo = Depends(check_daily_limit),
):
    """
    Generate video synchronously
    
    This endpoint blocks until video generation is complete.
    Suitable for small videos (< 30 seconds).
    
    **Note**: May timeout for large videos. Use `/generate/async` instead.
    
    Request body includes all video generation parameters.
    See VideoGenerateRequest schema for details.
    
    Returns path to generated video, duration, and file size.
    """
    try:
        logger.info(f"Sync video generation: {request_body.text[:50]}...")
        
        # Auto-determine media_width and media_height from template meta tags (required)
        if not request_body.frame_template:
            raise ValueError("frame_template is required to determine media size")
        
        from pixelle_video.services.frame_html import HTMLFrameGenerator
        from pixelle_video.utils.template_util import resolve_template_path
        template_path = resolve_template_path(request_body.frame_template)
        generator = HTMLFrameGenerator(template_path)
        media_width, media_height = generator.get_media_size()
        logger.debug(f"Auto-determined media size from template: {media_width}x{media_height}")
        
        # Build video generation parameters
        video_params = {
            "text": request_body.text,
            "mode": request_body.mode,
            "title": request_body.title,
            "n_scenes": request_body.n_scenes,
            "min_narration_words": request_body.min_narration_words,
            "max_narration_words": request_body.max_narration_words,
            "min_image_prompt_words": request_body.min_image_prompt_words,
            "max_image_prompt_words": request_body.max_image_prompt_words,
            "media_width": media_width,
            "media_height": media_height,
            "media_workflow": request_body.media_workflow,
            "video_fps": request_body.video_fps,
            "frame_template": request_body.frame_template,
            "prompt_prefix": request_body.prompt_prefix,
            "bgm_path": request_body.bgm_path,
            "bgm_volume": request_body.bgm_volume,
        }
        
        # Add TTS inference mode (local/comfyui)
        if request_body.tts_inference_mode:
            video_params["tts_inference_mode"] = request_body.tts_inference_mode
        
        # Add TTS engine (edge_tts/voxcpm_api)
        if request_body.tts_engine:
            video_params["tts_engine"] = request_body.tts_engine
        
        # Add TTS workflow if specified
        if request_body.tts_workflow:
            video_params["tts_workflow"] = request_body.tts_workflow
        
        # Add ref_audio if specified
        if request_body.ref_audio:
            video_params["ref_audio"] = request_body.ref_audio
        
        # Legacy voice_id support (deprecated)
        if request_body.voice_id:
            logger.warning("voice_id parameter is deprecated, please use tts_workflow instead")
            video_params["voice_id"] = request_body.voice_id
        
        # Add TTS speed if specified
        if request_body.tts_speed is not None:
            video_params["tts_speed"] = request_body.tts_speed
        
        # Add VoxCPM parameters
        if request_body.voxcpm_cfg is not None:
            video_params["voxcpm_cfg"] = request_body.voxcpm_cfg
        if request_body.voxcpm_normalize:
            video_params["voxcpm_normalize"] = request_body.voxcpm_normalize
        if request_body.voxcpm_denoise:
            video_params["voxcpm_denoise"] = request_body.voxcpm_denoise
        if request_body.voxcpm_control_instruction:
            video_params["voxcpm_control_instruction"] = request_body.voxcpm_control_instruction
        if request_body.voxcpm_use_prompt_text:
            video_params["voxcpm_use_prompt_text"] = True
            if request_body.voxcpm_prompt_text:
                video_params["voxcpm_prompt_text"] = request_body.voxcpm_prompt_text
        
        # Add custom template parameters if specified
        if request_body.template_params:
            video_params["template_params"] = request_body.template_params
        
        # Call video generator service
        result = await pixelle_video.generate_video(**video_params)
        
        # Increment daily usage after successful generation
        await increment_daily_usage(_user.id)
        
        # Get file size
        file_size = os.path.getsize(result.video_path) if os.path.exists(result.video_path) else 0
        
        # Convert path to URL
        video_url = path_to_url(request, result.video_path)
        
        return VideoGenerateResponse(
            video_url=video_url,
            duration=result.duration,
            file_size=file_size
        )
        
    except Exception as e:
        logger.error(f"Sync video generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/async", response_model=VideoGenerateAsyncResponse)
async def generate_video_async(
    request_body: VideoGenerateRequest,
    pixelle_video: PixelleVideoDep,
    request: Request,
    _user: UserInfo = Depends(check_daily_limit),
):
    """
    Generate video asynchronously
    
    Creates a background task for video generation.
    Returns immediately with a task_id for tracking progress.
    
    **Workflow:**
    1. Submit video generation request
    2. Receive task_id in response
    3. Poll `/api/tasks/{task_id}` to check status
    4. When status is "completed", retrieve video from result
    
    Request body includes all video generation parameters.
    See VideoGenerateRequest schema for details.
    
    Returns task_id for tracking progress.
    """
    user_id = _user.id
    try:
        logger.info(f"Async video generation: {request_body.text[:50]}...")
        
        # Create task
        task = task_manager.create_task(
            task_type=TaskType.VIDEO_GENERATION,
            request_params=request_body.model_dump()
        )
        
        # Define async execution function
        async def execute_video_generation():
            """Execute video generation in background"""
            # Auto-determine media_width and media_height from template meta tags (required)
            if not request_body.frame_template:
                raise ValueError("frame_template is required to determine media size")
            
            from pixelle_video.services.frame_html import HTMLFrameGenerator
            from pixelle_video.utils.template_util import resolve_template_path
            template_path = resolve_template_path(request_body.frame_template)
            generator = HTMLFrameGenerator(template_path)
            media_width, media_height = generator.get_media_size()
            logger.debug(f"Auto-determined media size from template: {media_width}x{media_height}")
            
            # Build video generation parameters
            video_params = {
                "text": request_body.text,
                "mode": request_body.mode,
                "title": request_body.title,
                "n_scenes": request_body.n_scenes,
                "min_narration_words": request_body.min_narration_words,
                "max_narration_words": request_body.max_narration_words,
                "min_image_prompt_words": request_body.min_image_prompt_words,
                "max_image_prompt_words": request_body.max_image_prompt_words,
                "media_width": media_width,
                "media_height": media_height,
                "media_workflow": request_body.media_workflow,
                "video_fps": request_body.video_fps,
                "frame_template": request_body.frame_template,
                "prompt_prefix": request_body.prompt_prefix,
                "bgm_path": request_body.bgm_path,
                "bgm_volume": request_body.bgm_volume,
            }
            
            # Add TTS inference mode (local/comfyui)
            if request_body.tts_inference_mode:
                video_params["tts_inference_mode"] = request_body.tts_inference_mode
            
            # Add TTS engine (edge_tts/voxcpm_api)
            if request_body.tts_engine:
                video_params["tts_engine"] = request_body.tts_engine
            
            # Add TTS workflow if specified
            if request_body.tts_workflow:
                video_params["tts_workflow"] = request_body.tts_workflow
            
            # Add ref_audio if specified
            if request_body.ref_audio:
                video_params["ref_audio"] = request_body.ref_audio
            
            # Legacy voice_id support (deprecated)
            if request_body.voice_id:
                logger.warning("voice_id parameter is deprecated, please use tts_workflow instead")
                video_params["voice_id"] = request_body.voice_id
            
            # Add TTS speed if specified
            if request_body.tts_speed is not None:
                video_params["tts_speed"] = request_body.tts_speed
            
            # Add VoxCPM parameters
            if request_body.voxcpm_cfg is not None:
                video_params["voxcpm_cfg"] = request_body.voxcpm_cfg
            if request_body.voxcpm_normalize:
                video_params["voxcpm_normalize"] = request_body.voxcpm_normalize
            if request_body.voxcpm_denoise:
                video_params["voxcpm_denoise"] = request_body.voxcpm_denoise
            if request_body.voxcpm_control_instruction:
                video_params["voxcpm_control_instruction"] = request_body.voxcpm_control_instruction
            if request_body.voxcpm_use_prompt_text:
                video_params["voxcpm_use_prompt_text"] = True
                if request_body.voxcpm_prompt_text:
                    video_params["voxcpm_prompt_text"] = request_body.voxcpm_prompt_text
            
            # Add custom template parameters if specified
            if request_body.template_params:
                video_params["template_params"] = request_body.template_params
            
            result = await pixelle_video.generate_video(**video_params)
            
            # Increment daily usage after successful generation
            await increment_daily_usage(user_id)
            
            # Get file size
            file_size = os.path.getsize(result.video_path) if os.path.exists(result.video_path) else 0
            
            # Convert path to URL
            video_url = path_to_url(request, result.video_path)
            
            return {
                "video_url": video_url,
                "duration": result.duration,
                "file_size": file_size
            }
        
        # Start execution
        await task_manager.execute_task(
            task_id=task.task_id,
            coro_func=execute_video_generation
        )
        
        return VideoGenerateAsyncResponse(
            task_id=task.task_id
        )
        
    except Exception as e:
        logger.error(f"Async video generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/batch", response_model=VideoBatchGenerateResponse)
async def generate_video_batch(
    request_body: VideoBatchGenerateRequest,
    pixelle_video: PixelleVideoDep,
    request: Request,
    _user: UserInfo = Depends(check_daily_limit),
):
    """
    Batch video generation (async)
    
    Creates a parent task that generates multiple videos in sequence.
    Each topic in the list generates one video with shared configuration.
    Returns immediately with a parent task_id for tracking overall progress.
    
    **Workflow:**
    1. Submit batch request with topics + shared config
    2. Receive parent task_id in response
    3. Poll `/api/tasks/{task_id}` to track overall batch progress
    4. Each video's progress is reported as sub-steps
    5. When status is "completed", all videos are generated
    
    Request body includes:
    - topics: List of topics (one per video)
    - title_prefix: Optional prefix for auto-generated titles
    - n_scenes and other shared config: Applied to all videos
    """
    try:
        n_topics = len(request_body.topics)
        logger.info(f"Batch video generation: {n_topics} topics")
        
        # Create parent batch task
        task = task_manager.create_task(
            task_type=TaskType.VIDEO_GENERATION,
            request_params=request_body.model_dump()
        )
        
        # Define async batch execution function
        async def execute_batch_generation():
            """Execute batch video generation in background"""
            # Validate frame_template
            if not request_body.frame_template:
                raise ValueError("frame_template is required to determine media size")
            
            from pixelle_video.services.frame_html import HTMLFrameGenerator
            from pixelle_video.utils.template_util import resolve_template_path
            template_path = resolve_template_path(request_body.frame_template)
            generator = HTMLFrameGenerator(template_path)
            media_width, media_height = generator.get_media_size()
            logger.debug(f"Batch: auto-determined media size: {media_width}x{media_height}")
            
            # Build shared config dict (filter out None values)
            shared_config = {
                "mode": "generate",
                "n_scenes": request_body.n_scenes or 5,
                "media_width": media_width,
                "media_height": media_height,
                "frame_template": request_body.frame_template,
                "prompt_prefix": request_body.prompt_prefix or "",
                "bgm_path": request_body.bgm_path,
                "bgm_volume": request_body.bgm_volume or 0.3,
                "video_fps": request_body.video_fps or 30,
            }
            
            # Add TTS params
            shared_config["tts_inference_mode"] = request_body.tts_inference_mode or "local"
            if request_body.tts_inference_mode == "local":
                if request_body.tts_voice:
                    shared_config["tts_voice"] = request_body.tts_voice
                if request_body.tts_speed is not None:
                    shared_config["tts_speed"] = request_body.tts_speed
                if request_body.tts_engine:
                    shared_config["tts_engine"] = request_body.tts_engine
                if request_body.ref_audio:
                    shared_config["ref_audio"] = request_body.ref_audio
                if request_body.voxcpm_cfg is not None:
                    shared_config["voxcpm_cfg"] = request_body.voxcpm_cfg
                if request_body.voxcpm_normalize:
                    shared_config["voxcpm_normalize"] = True
                if request_body.voxcpm_denoise:
                    shared_config["voxcpm_denoise"] = True
                if request_body.voxcpm_control_instruction:
                    shared_config["voxcpm_control_instruction"] = request_body.voxcpm_control_instruction
                if request_body.voxcpm_use_prompt_text:
                    shared_config["voxcpm_use_prompt_text"] = True
                    if request_body.voxcpm_prompt_text:
                        shared_config["voxcpm_prompt_text"] = request_body.voxcpm_prompt_text
            else:  # comfyui
                if request_body.tts_workflow:
                    shared_config["tts_workflow"] = request_body.tts_workflow
                if request_body.ref_audio:
                    shared_config["ref_audio"] = request_body.ref_audio
            
            # Add LLM params
            if request_body.min_narration_words is not None:
                shared_config["min_narration_words"] = request_body.min_narration_words
            if request_body.max_narration_words is not None:
                shared_config["max_narration_words"] = request_body.max_narration_words
            if request_body.min_image_prompt_words is not None:
                shared_config["min_image_prompt_words"] = request_body.min_image_prompt_words
            if request_body.max_image_prompt_words is not None:
                shared_config["max_image_prompt_words"] = request_body.max_image_prompt_words
            
            # Add media workflow
            if request_body.media_workflow:
                shared_config["media_workflow"] = request_body.media_workflow
            
            # Add template params
            if request_body.template_params:
                shared_config["template_params"] = request_body.template_params
            
            total = len(request_body.topics)
            results = []
            errors = []
            
            for idx, topic in enumerate(request_body.topics, 1):
                try:
                    logger.info(f"Batch task {idx}/{total}: {topic}")
                    
                    # Each video in batch consumes one daily quota
                    await increment_daily_usage(_user.id)
                    
                    # Build per-video params
                    video_params = dict(shared_config)
                    video_params["text"] = topic
                    
                    # Generate title
                    if request_body.title_prefix:
                        video_params["title"] = f"{request_body.title_prefix} - {topic}"
                    else:
                        video_params["title"] = topic
                    
                    # Update task progress for current video
                    task_manager.update_progress(
                        task_id=task.task_id,
                        current=idx - 1,
                        total=total,
                        message=f"正在生成第 {idx}/{total} 个视频: {topic[:30]}..."
                    )
                    
                    result = await pixelle_video.generate_video(**video_params)
                    
                    video_url = path_to_url(request, result.video_path)
                    results.append({
                        "index": idx,
                        "topic": topic,
                        "video_url": video_url,
                        "video_path": result.video_path,
                        "duration": result.duration,
                    })
                    
                    logger.info(f"Batch task {idx}/{total} completed: {result.video_path}")
                    
                except Exception as e:
                    logger.error(f"Batch task {idx}/{total} failed: {e}")
                    errors.append({
                        "index": idx,
                        "topic": topic,
                        "error": str(e),
                    })
                    # Continue to next topic
                    continue
            
            # Final progress update
            task_manager.update_progress(
                task_id=task.task_id,
                current=total,
                total=total,
                message=f"批量生成完成: {len(results)}/{total} 成功, {len(errors)} 失败"
            )
            
            return {
                "results": results,
                "errors": errors,
                "total_count": total,
                "success_count": len(results),
                "failed_count": len(errors),
            }
        
        # Start execution
        await task_manager.execute_task(
            task_id=task.task_id,
            coro_func=execute_batch_generation
        )
        
        return VideoBatchGenerateResponse(
            task_id=task.task_id,
            total_videos=n_topics
        )
        
    except Exception as e:
        logger.error(f"Batch video generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
