# Copyright (C) 2025 AIDC-AI
#
# Licensed under the Apache License, Version 2.0

"""
Modern UI pipeline endpoints.

These endpoints expose the Streamlit-only pipeline workflows through FastAPI so
the modern UI can run every existing tool without falling back to Streamlit.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from loguru import logger
from pydantic import BaseModel, Field

from api.auth.dependencies import check_daily_limit, increment_daily_usage, decrement_daily_usage
from api.auth.schemas import UserInfo
from api.dependencies import PixelleVideoDep
from api.routers.video import path_to_url
from api.tasks import TaskType, task_manager
from pixelle_video.pipelines.asset_based import AssetBasedPipeline
from pixelle_video.utils.os_util import create_task_output_dir
from api.utils.history_persistence import save_web_generation_history

router = APIRouter(prefix="/pipelines", tags=["Modern Pipelines"])


class AsyncTaskResponse(BaseModel):
    success: bool = True
    message: str = "Task created successfully"
    task_id: str


class AssetBasedRequest(BaseModel):
    assets: list[str] = Field(default_factory=list)
    video_title: str = ""
    intent: Optional[str] = None
    duration: int = Field(30, ge=5, le=300)
    source: str = "runninghub"
    analysis_image_workflow: Optional[str] = None
    analysis_video_workflow: Optional[str] = None
    analysis_vlm_model: Optional[str] = None
    api_video_workflow: Optional[str] = None
    api_video_params: dict[str, Any] = Field(default_factory=dict)
    voice_id: str = "zh-CN-YunjianNeural"
    tts_speed: float = 1.2
    bgm_path: Optional[str] = None
    bgm_volume: float = Field(0.2, ge=0.0, le=1.0)
    bgm_mode: str = "loop"


class ImageToVideoRequest(BaseModel):
    image_assets: list[str] = Field(default_factory=list)
    prompt_text: str
    workflow_key: str
    api_video_params: dict[str, Any] = Field(default_factory=dict)


class ActionTransferRequest(BaseModel):
    video_assets: list[str] = Field(default_factory=list)
    image_assets: list[str] = Field(default_factory=list)
    prompt_text: str
    duration: int = Field(5, ge=1, le=300)
    workflow_key: str
    api_video_params: dict[str, Any] = Field(default_factory=dict)


class DigitalWorkflowConfig(BaseModel):
    first_workflow_path: Optional[str] = "workflows/runninghub/digital_image.json"
    second_workflow_path: Optional[str] = "workflows/runninghub/digital_combination.json"
    third_workflow_path: Optional[str] = "workflows/runninghub/digital_customize.json"
    api_image_workflow: Optional[str] = None
    api_video_workflow: Optional[str] = None
    api_video_params: dict[str, Any] = Field(default_factory=dict)


class DigitalHumanRequest(BaseModel):
    mode: Literal["digital", "customize"] = "digital"
    character_assets: list[str] = Field(default_factory=list)
    goods_assets: list[str] = Field(default_factory=list)
    goods_title: str = ""
    goods_text: str = ""
    workflow_config: DigitalWorkflowConfig = Field(default_factory=DigitalWorkflowConfig)

    # TTS parameters compatible with the existing Streamlit UI.
    tts_inference_mode: str = "local"
    tts_engine: Optional[str] = None
    tts_voice: str = "zh-CN-YunjianNeural"
    tts_speed: float = 1.2
    tts_workflow: Optional[str] = None
    ref_audio: Optional[str] = None
    voxcpm_cfg: float = 2.0
    voxcpm_normalize: bool = False
    voxcpm_denoise: bool = False
    voxcpm_control_instruction: str = ""
    voxcpm_use_prompt_text: bool = False
    voxcpm_prompt_text: str = ""


def _is_api_workflow(workflow_key: str | None) -> bool:
    return bool(workflow_key and workflow_key.startswith("api/"))


def _extract_video_url(result: Any) -> Optional[str]:
    if hasattr(result, "url") and result.url:
        return result.url

    if hasattr(result, "videos") and result.videos:
        return result.videos[0]

    if hasattr(result, "outputs") and result.outputs:
        for node_output in result.outputs.values():
            if isinstance(node_output, dict) and node_output.get("videos"):
                return node_output["videos"][0]

    return None


def _extract_image_url(result: Any) -> Optional[str]:
    if hasattr(result, "url") and result.url:
        return result.url

    if hasattr(result, "images") and result.images:
        return result.images[0]

    if hasattr(result, "outputs") and result.outputs:
        for node_output in result.outputs.values():
            if isinstance(node_output, dict) and node_output.get("images"):
                return node_output["images"][0]

    return None


async def _download_to_file(url: str, output_path: str) -> str:
    if url.startswith(("http://", "https://")):
        timeout = httpx.Timeout(300.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            Path(output_path).write_bytes(response.content)
        return output_path

    if Path(url).exists():
        return url

    return url


def _workflow_input_from_config(workflow_path: Path, workflow_config: dict[str, Any]) -> str:
    if workflow_config.get("source") == "runninghub" and workflow_config.get("workflow_id"):
        return workflow_config["workflow_id"]
    return str(workflow_path)


async def _execute_comfy_video_workflow(
    pixelle_video: Any,
    *,
    workflow_key: str,
    workflow_params: dict[str, Any],
    final_video_path: str,
) -> str:
    kit = await pixelle_video._get_or_create_comfykit()
    workflow_path = Path("workflows") / workflow_key

    if not workflow_path.exists():
        raise FileNotFoundError(f"The workflow file does not exist: {workflow_path}")

    workflow_config = json.loads(workflow_path.read_text(encoding="utf-8"))
    workflow_input = _workflow_input_from_config(workflow_path, workflow_config)
    result = await kit.execute(workflow_input, workflow_params)

    # If the result contains an error status, propagate the original error
    # instead of masking it with a generic "no video returned" message.
    if hasattr(result, "status") and getattr(result, "status", "") == "error":
        error_msg = getattr(result, "msg", "Unknown workflow execution error")
        raise RuntimeError(f"Workflow execution failed: {error_msg}")

    generated_video_url = _extract_video_url(result)
    if not generated_video_url:
        raise RuntimeError("The workflow did not return a video. Please check the workflow configuration.")

    return await _download_to_file(generated_video_url, final_video_path)


async def _run_tts(pixelle_video: Any, request_body: DigitalHumanRequest, text: str, audio_path: str) -> str:
    tts_kwargs: dict[str, Any] = {
        "text": text,
        "output_path": audio_path,
        "inference_mode": request_body.tts_inference_mode,
    }

    # Determine effective engine: param > mode name
    effective_engine = request_body.tts_engine
    if not effective_engine and request_body.tts_inference_mode == "voxcpm_api":
        effective_engine = "voxcpm_api"

    if request_body.tts_inference_mode == "local" or effective_engine == "voxcpm_api":
        # Local TTS mode (Edge TTS or VoxCPM API)
        if effective_engine:
            tts_kwargs["engine"] = effective_engine

        if effective_engine == "voxcpm_api":
            tts_kwargs["cfg"] = request_body.voxcpm_cfg
            tts_kwargs["normalize"] = request_body.voxcpm_normalize
            tts_kwargs["denoise"] = request_body.voxcpm_denoise
            if request_body.voxcpm_control_instruction:
                tts_kwargs["control_instruction"] = request_body.voxcpm_control_instruction
            if request_body.voxcpm_use_prompt_text:
                tts_kwargs["use_prompt_text"] = True
                if request_body.voxcpm_prompt_text:
                    tts_kwargs["prompt_text"] = request_body.voxcpm_prompt_text
            if request_body.ref_audio:
                tts_kwargs["ref_audio"] = request_body.ref_audio
        else:
            tts_kwargs["voice"] = request_body.tts_voice
            tts_kwargs["speed"] = request_body.tts_speed

    elif request_body.tts_inference_mode == "comfyui":
        if request_body.tts_workflow:
            tts_kwargs["workflow"] = request_body.tts_workflow
        if request_body.ref_audio:
            tts_kwargs["ref_audio"] = request_body.ref_audio

    logger.info(f"🎙️  _run_tts: mode={request_body.tts_inference_mode}, engine={effective_engine}, text_len={len(text)}")
    await pixelle_video.tts(**tts_kwargs)
    return audio_path


async def _run_second_digital_workflow(
    pixelle_video: Any,
    *,
    workflow_path_str: str,
    generated_image: str,
    audio_path: str,
    final_video_path: str,
) -> str:
    second_workflow_path = Path(workflow_path_str)
    if not second_workflow_path.exists():
        raise FileNotFoundError(f"The second step workflow file does not exist: {second_workflow_path}")

    second_workflow_config = json.loads(second_workflow_path.read_text(encoding="utf-8"))
    workflow_input = _workflow_input_from_config(second_workflow_path, second_workflow_config)
    kit = await pixelle_video._get_or_create_comfykit()
    result = await kit.execute(workflow_input, {"videoimage": generated_image, "audio": audio_path})

    # If the result contains an error status, propagate the original error
    if result.status == "error":
        error_msg = result.msg or "Unknown workflow execution error"
        raise RuntimeError(f"Second workflow execution failed: {error_msg}")

    generated_video_url = _extract_video_url(result)
    if not generated_video_url:
        raise RuntimeError("The second step of the workflow did not return a video.")

    return await _download_to_file(generated_video_url, final_video_path)


async def _run_digital_human_pipeline(pixelle_video: Any, request_body: DigitalHumanRequest) -> str:
    task_dir, _task_id = create_task_output_dir()
    final_video_path = os.path.join(task_dir, "final.mp4")
    audio_path = os.path.join(task_dir, "narration.mp3")
    cfg = request_body.workflow_config

    character_assets = request_body.character_assets
    goods_assets = request_body.goods_assets

    if not character_assets:
        raise ValueError("Please upload at least one character image.")

    if request_body.mode == "digital" and not goods_assets:
        raise ValueError("Please upload at least one goods/product image in digital mode.")

    if request_body.mode == "customize" and not request_body.goods_text.strip():
        raise ValueError("Please provide speech text in customize mode.")

    if request_body.mode == "digital" and not (request_body.goods_text.strip() or request_body.goods_title.strip()):
        raise ValueError("Please provide goods title or speech text in digital mode.")

    async def get_script_text() -> str:
        if request_body.mode == "customize":
            return request_body.goods_text.strip()
        if request_body.goods_text.strip():
            return request_body.goods_text.strip()
        return await pixelle_video.llm(
            prompt=(
                f"请为商品“{request_body.goods_title}”写一段适合数字人口播短视频的中文推广文案。"
                "要求自然、有吸引力，控制在60字以内，只输出文案正文。"
            ),
            temperature=0.7,
            max_tokens=300,
        )

    generated_text = await get_script_text()

    # Normalize API workflow paths: ensure they have the "api/" prefix expected by media service
    if cfg.api_video_workflow and not cfg.api_video_workflow.startswith("api/"):
        cfg.api_video_workflow = f"api/{cfg.api_video_workflow}"
    if cfg.api_image_workflow and not cfg.api_image_workflow.startswith("api/"):
        cfg.api_image_workflow = f"api/{cfg.api_image_workflow}"

    if cfg.api_video_workflow:
        await _run_tts(pixelle_video, request_body, generated_text, audio_path)
        reference_image_paths = [character_assets[0]]
        if request_body.mode == "digital" and goods_assets:
            reference_image_paths.append(goods_assets[0])

        subject_prompt = "参考图1中的人物面对镜头自然口播。"
        if request_body.mode == "digital" and goods_assets:
            subject_prompt += "结合参考图2中的商品，生成竖屏商业口播视频。"
        prompt = f"{subject_prompt} 口播文案：{generated_text}"

        api_video_params = dict(cfg.api_video_params or {})
        duration = int(api_video_params.pop("duration", 5))
        media_result = await pixelle_video.media(
            **api_video_params,
            prompt=prompt,
            workflow=cfg.api_video_workflow,
            media_type="video",
            output_path=final_video_path,
            duration=duration,
            reference_image_paths=reference_image_paths,
            reference_audio_path=audio_path,
            audio=True,
            video_ratio=api_video_params.get("video_ratio", "9:16"),
        )
        return await _download_to_file(media_result.url, final_video_path)

    if request_body.mode == "customize":
        generated_image = character_assets[0]
        await _run_tts(pixelle_video, request_body, generated_text, audio_path)
        if not cfg.second_workflow_path:
            raise ValueError("second_workflow_path is required for customize mode.")
        return await _run_second_digital_workflow(
            pixelle_video,
            workflow_path_str=cfg.second_workflow_path,
            generated_image=generated_image,
            audio_path=audio_path,
            final_video_path=final_video_path,
        )

    # Digital product mode: generate/combine a product image first, then synthesize talking video.
    if cfg.api_image_workflow:
        image_prompt = (
            f"Create a polished digital-human product promotion image for '{request_body.goods_title}'. "
            f"Use the first reference image as the person/character and the second reference image as the product. "
            f"Make it vertical, clean, commercial, and suitable for a spoken short video. Script: {generated_text}"
        )
        generated_image_path = os.path.join(task_dir, "generated_digital_image.png")
        media_result = await pixelle_video.media(
            prompt=image_prompt,
            workflow=cfg.api_image_workflow,
            media_type="image",
            image_paths=[character_assets[0], goods_assets[0]],
            output_path=generated_image_path,
            width=1080,
            height=1920,
        )
        generated_image = media_result.url
    else:
        workflow_path_str = cfg.third_workflow_path if request_body.goods_text.strip() else cfg.first_workflow_path
        if not workflow_path_str:
            raise ValueError("first_workflow_path/third_workflow_path is required for digital mode.")

        workflow_path = Path(workflow_path_str)
        if not workflow_path.exists():
            raise FileNotFoundError(f"The image workflow file does not exist: {workflow_path}")

        workflow_config = json.loads(workflow_path.read_text(encoding="utf-8"))
        workflow_input = _workflow_input_from_config(workflow_path, workflow_config)
        kit = await pixelle_video._get_or_create_comfykit()
        workflow_params = (
            {"firstimage": character_assets[0], "secondimage": goods_assets[0]}
            if request_body.goods_text.strip()
            else {
                "firstimage": character_assets[0],
                "secondimage": goods_assets[0],
                "goodstype": request_body.goods_title,
            }
        )
        image_result = await kit.execute(workflow_input, workflow_params)
        generated_image = _extract_image_url(image_result)
        if not generated_image:
            raise RuntimeError("The image workflow did not return an image.")

        if not request_body.goods_text.strip() and hasattr(image_result, "texts") and image_result.texts:
            generated_text = image_result.texts[0]

    await _run_tts(pixelle_video, request_body, generated_text, audio_path)
    if not cfg.second_workflow_path:
        raise ValueError("second_workflow_path is required for digital mode.")

    return await _run_second_digital_workflow(
        pixelle_video,
        workflow_path_str=cfg.second_workflow_path,
        generated_image=generated_image,
        audio_path=audio_path,
        final_video_path=final_video_path,
    )


def _task_response(task_id: str) -> AsyncTaskResponse:
    return AsyncTaskResponse(task_id=task_id)


@router.post("/asset-based/async", response_model=AsyncTaskResponse)
async def generate_asset_based_async(
    request_body: AssetBasedRequest,
    pixelle_video: PixelleVideoDep,
    request: Request,
    _user: UserInfo = Depends(check_daily_limit),
):
    user_id = _user.id
    # Pre-deduct daily usage immediately at submission time
    await increment_daily_usage(user_id)
    try:
        task = task_manager.create_task(
            task_type=TaskType.VIDEO_GENERATION,
            request_params=request_body.model_dump(),
        )

        async def execute():
            def progress_callback(event):
                task_manager.update_progress(
                    task.task_id,
                    int(event.progress * 100),
                    100,
                    event.event_type,
                )

            try:
                pipeline = AssetBasedPipeline(pixelle_video)
                ctx = await pipeline(
                    assets=request_body.assets,
                    video_title=request_body.video_title,
                    intent=request_body.intent,
                    duration=request_body.duration,
                    source=request_body.source,
                    analysis_image_workflow=request_body.analysis_image_workflow,
                    analysis_video_workflow=request_body.analysis_video_workflow,
                    analysis_vlm_model=request_body.analysis_vlm_model,
                    bgm_path=request_body.bgm_path,
                    bgm_volume=request_body.bgm_volume,
                    bgm_mode=request_body.bgm_mode,
                    api_video_workflow=request_body.api_video_workflow,
                    api_video_params=request_body.api_video_params,
                    voice_id=request_body.voice_id,
                    tts_speed=request_body.tts_speed,
                    progress_callback=progress_callback,
                )
            except Exception:
                # Generation failed, refund the deducted daily usage
                await decrement_daily_usage(user_id)
                raise

            await save_web_generation_history(
                pixelle_video,
                task_id=getattr(ctx, "task_id", task.task_id),
                video_path=ctx.final_video_path,
                pipeline="custom_media",
                title=request_body.video_title or "素材创作",
                input_params=request_body.model_dump(),
                n_frames=len(ctx.storyboard.frames) if getattr(ctx, "storyboard", None) else 1,
                user_id=user_id,
            )
            return {
                "pipeline": "custom_media",
                "video_path": ctx.final_video_path,
                "video_url": path_to_url(request, ctx.final_video_path),
            }

        await task_manager.execute_with_concurrency_limit(task.task_id, execute)
        return _task_response(task.task_id)

    except Exception as exc:
        # Refund on unexpected errors during task creation / setup
        await decrement_daily_usage(user_id)
        logger.exception(exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/image-to-video/async", response_model=AsyncTaskResponse)
async def generate_image_to_video_async(
    request_body: ImageToVideoRequest,
    pixelle_video: PixelleVideoDep,
    request: Request,
    _user: UserInfo = Depends(check_daily_limit),
):
    user_id = _user.id
    # Pre-deduct daily usage immediately at submission time (prevents concurrent overuse)
    await increment_daily_usage(user_id)
    try:
        task = task_manager.create_task(TaskType.VIDEO_GENERATION, request_body.model_dump())

        async def execute():
            if not request_body.image_assets:
                raise ValueError("Please upload at least one image.")
            if not request_body.prompt_text.strip():
                raise ValueError("Please provide prompt text.")

            task_dir, task_dir_id = create_task_output_dir()
            final_video_path = os.path.join(task_dir, "final.mp4")
            image_path = request_body.image_assets[0]
            prompt = request_body.prompt_text

            task_manager.update_progress(task.task_id, 10, 100, "generating")

            try:
                if _is_api_workflow(request_body.workflow_key):
                    media_result = await pixelle_video.media(
                        **request_body.api_video_params,
                        prompt=prompt,
                        workflow=request_body.workflow_key,
                        media_type="video",
                        image_path=image_path,
                        output_path=final_video_path,
                    )
                    final_path = await _download_to_file(media_result.url, final_video_path)
                else:
                    final_path = await _execute_comfy_video_workflow(
                        pixelle_video,
                        workflow_key=request_body.workflow_key,
                        workflow_params={"image": image_path, "prompt": prompt},
                        final_video_path=final_video_path,
                    )
            except Exception:
                # Generation failed, refund the deducted daily usage
                await decrement_daily_usage(user_id)
                raise

            await save_web_generation_history(
                pixelle_video,
                task_id=task_dir_id,
                video_path=final_path,
                pipeline="image_to_video",
                title="图生视频",
                input_params=request_body.model_dump(),
                user_id=user_id,
            )

            task_manager.update_progress(task.task_id, 100, 100, "completed")
            return {
                "pipeline": "image_to_video",
                "video_path": final_path,
                "video_url": path_to_url(request, final_path) if Path(final_path).exists() else final_path,
            }

        await task_manager.execute_with_concurrency_limit(task.task_id, execute)
        return _task_response(task.task_id)

    except Exception as exc:
        # Refund on unexpected errors during task creation / setup
        await decrement_daily_usage(user_id)
        logger.exception(exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/action-transfer/async", response_model=AsyncTaskResponse)
async def generate_action_transfer_async(
    request_body: ActionTransferRequest,
    pixelle_video: PixelleVideoDep,
    request: Request,
    _user: UserInfo = Depends(check_daily_limit),
):
    user_id = _user.id
    # Pre-deduct daily usage immediately at submission time (prevents concurrent overuse)
    await increment_daily_usage(user_id)
    try:
        task = task_manager.create_task(TaskType.VIDEO_GENERATION, request_body.model_dump())

        async def execute():
            if not request_body.video_assets:
                raise ValueError("Please upload at least one reference video.")
            if not request_body.image_assets:
                raise ValueError("Please upload at least one reference image.")
            if not request_body.prompt_text.strip():
                raise ValueError("Please provide prompt text.")

            task_dir, task_dir_id = create_task_output_dir()
            final_video_path = os.path.join(task_dir, "final.mp4")
            video_path = request_body.video_assets[0]
            image_path = request_body.image_assets[0]
            prompt = request_body.prompt_text

            task_manager.update_progress(task.task_id, 10, 100, "generating")

            try:
                if _is_api_workflow(request_body.workflow_key):
                    media_result = await pixelle_video.media(
                        **request_body.api_video_params,
                        prompt=prompt,
                        workflow=request_body.workflow_key,
                        media_type="video",
                        output_path=final_video_path,
                        duration=request_body.duration,
                        first_clip_path=video_path,
                        reference_image_path=image_path,
                    )
                    final_path = await _download_to_file(media_result.url, final_video_path)
                else:
                    final_path = await _execute_comfy_video_workflow(
                        pixelle_video,
                        workflow_key=request_body.workflow_key,
                        workflow_params={
                            "video": video_path,
                            "image": image_path,
                            "prompt": prompt,
                            "second": request_body.duration,
                        },
                        final_video_path=final_video_path,
                    )
            except Exception:
                # Generation failed, refund the deducted daily usage
                await decrement_daily_usage(user_id)
                raise

            await save_web_generation_history(
                pixelle_video,
                task_id=task_dir_id,
                video_path=final_path,
                pipeline="action_transfer",
                title="动作迁移",
                input_params=request_body.model_dump(),
                user_id=user_id,
            )

            task_manager.update_progress(task.task_id, 100, 100, "completed")
            return {
                "pipeline": "action_transfer",
                "video_path": final_path,
                "video_url": path_to_url(request, final_path) if Path(final_path).exists() else final_path,
            }

        await task_manager.execute_with_concurrency_limit(task.task_id, execute)
        return _task_response(task.task_id)

    except Exception as exc:
        # Refund on unexpected errors during task creation / setup
        await decrement_daily_usage(user_id)
        logger.exception(exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/digital-human/async", response_model=AsyncTaskResponse)
async def generate_digital_human_async(
    request_body: DigitalHumanRequest,
    pixelle_video: PixelleVideoDep,
    request: Request,
    _user: UserInfo = Depends(check_daily_limit),
):
    user_id = _user.id
    # Pre-deduct daily usage immediately at submission time (prevents concurrent overuse)
    await increment_daily_usage(user_id)
    try:
        task = task_manager.create_task(TaskType.VIDEO_GENERATION, request_body.model_dump())

        async def execute():
            task_manager.update_progress(task.task_id, 10, 100, "preparing")
            try:
                final_path = await _run_digital_human_pipeline(pixelle_video, request_body)
            except Exception:
                # Generation failed, refund the deducted daily usage
                await decrement_daily_usage(user_id)
                raise

            await save_web_generation_history(
                pixelle_video,
                task_id=Path(final_path).parent.name if Path(final_path).exists() else task.task_id,
                video_path=final_path,
                pipeline="digital_human",
                title="数字人口播",
                input_params=request_body.model_dump(),
                user_id=user_id,
            )

            task_manager.update_progress(task.task_id, 100, 100, "completed")
            return {
                "pipeline": "digital_human",
                "video_path": final_path,
                "video_url": path_to_url(request, final_path) if Path(final_path).exists() else final_path,
            }

        await task_manager.execute_with_concurrency_limit(task.task_id, execute)
        return _task_response(task.task_id)

    except Exception as exc:
        # Refund on unexpected errors during task creation / setup
        await decrement_daily_usage(user_id)
        logger.exception(exc)
        raise HTTPException(status_code=500, detail=str(exc))
