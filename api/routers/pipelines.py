# Copyright (C) 2025 AIDC-AI
#
# Licensed under the Apache License, Version 2.0

"""
Modern UI pipeline endpoints.

These endpoints expose the Streamlit-only pipeline workflows through FastAPI so
the modern UI can run every existing tool without falling back to Streamlit.
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import re
from pathlib import Path
from typing import Any, Literal, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from loguru import logger
from pydantic import BaseModel, Field

from datetime import datetime
from api.auth.dependencies import (
    check_daily_limit,
    increment_daily_usage,
    decrement_daily_usage,
    freeze_balance,
    settle_generation,
)
from api.auth.schemas import UserInfo
from api.auth.database import Database
from api.dependencies import PixelleVideoDep
from api.routers.video import path_to_url
from api.tasks import TaskType, task_manager
from pixelle_video.utils.os_util import create_task_output_dir
from api.utils.history_persistence import save_web_generation_history
from pixelle_video.services.subtitle import SubtitleService, SubtitleConfigModel
from pixelle_video.services.overlay import OverlayService, TitleOverlayConfig, BusinessCardConfig, BgmOverlayConfig
from pixelle_video.services.video import VideoService
from pixelle_video.services.remote_comfy_service import RemoteComfyService, RemoteComfyServiceError
from pixelle_video.utils.os_util import get_temp_path
from pixelle_video.config import config_manager

# 统一文字清理正则（与前端 DigitalHumanView.vue 保持一致）
PATTERN_CLEAN_TEXT = r'[。！？；，、：；“”\'\'—…（）【】《》〈〉.!?,;:()\[\]{}<>""\'\'\-/\s]'

router = APIRouter(prefix="/pipelines", tags=["Modern Pipelines"])


class AsyncTaskResponse(BaseModel):
    success: bool = True
    message: str = "Task created successfully"
    task_id: str


class DigitalWorkflowConfig(BaseModel):
    first_workflow_path: Optional[str] = "workflows/runninghub/digital_image.json"
    second_workflow_path: Optional[str] = "workflows/runninghub/digital_combination.json"
    third_workflow_path: Optional[str] = "workflows/runninghub/digital_customize.json"
    api_image_workflow: Optional[str] = None
    api_video_workflow: Optional[str] = None
    api_video_params: dict[str, Any] = Field(default_factory=dict)


class SubtitleRequestConfig(BaseModel):
    """字幕配置（与前端 SubtitleConfig 接口对应）"""
    enabled: bool = False
    font_size: int = 56
    font_color: str = "#FFFFFF"
    font_family: str = "NotoSansSC-Bold"
    position_x: int = 0
    position_y: int = -390
    max_width: int = 900
    letter_spacing: int = 3
    background_color: str = "#000000"
    background_opacity: float = 0
    background_padding: str = "15 25"
    background_radius: int = 20
    font_border_width: int = 1
    font_border_color: str = "#000000"
    font_weight: int = 400


class DigitalHumanRequest(BaseModel):
    mode: Literal["customize"] = "customize"
    character_assets: list[str] = Field(default_factory=list)
    goods_assets: list[str] = Field(default_factory=list)
    goods_text: str = Field("", max_length=368, description="口播文案，最长368字")
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

    # 字幕配置
    subtitle_config: SubtitleRequestConfig = Field(default_factory=SubtitleRequestConfig)

    # 网感剪辑配置
    title_overlay_config: dict[str, Any] = Field(default_factory=lambda: {
        "enabled": False, "text": "", "font_size": 56, "font_color": "#FFFFFF",
        "font_weight": 700, "position_x": 0, "position_y": -800,
        "display_mode": "duration", "duration_seconds": 2,
    })
    business_card_config: dict[str, Any] = Field(default_factory=lambda: {
        "enabled": False, "title": "", "subtitle": "",
        "display_mode": "duration", "duration_seconds": 2,
    })
    bgm_config: dict[str, Any] = Field(default_factory=lambda: {
        "enabled": False, "selected_bgm": None, "volume": 50, "custom_bgm": None,
    })
    pip_mix_config: dict[str, Any] = Field(default_factory=dict)


def _get_user_priority(role: str) -> int:
    """
    根据用户角色获取队列优先级。
    0 = 普通用户, 1 = VIP, 2 = SVIP
    """
    if role == "svip":
        return 2
    if role == "vip":
        return 1
    return 0


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
    workflow_path = Path("workflows") / workflow_key

    if not workflow_path.exists():
        raise FileNotFoundError(f"The workflow file does not exist: {workflow_path}")

    workflow_config = json.loads(workflow_path.read_text(encoding="utf-8"))
    workflow_input = _workflow_input_from_config(workflow_path, workflow_config)
    result = await pixelle_video.execute_with_concurrency(workflow_input, workflow_params)

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
    
    # 🔍 调试日志
    logger.info(
        f"🎬 [运行数字人工作流] workflow={workflow_path_str}, "
        f"workflow_input={workflow_input}, "
        f"image_path={generated_image}, "
        f"audio_path={audio_path}, "
        f"audio_exists={Path(audio_path).exists()}"
    )
    
    # 🔧 关键修复：同时传递多个可能的参数名，兼容不同的加载节点
    workflow_params = {
        # 图片参数 - 兼容多种节点类型
        "videoimage": generated_image,
        "image": generated_image,
        "input_image": generated_image,
        "imagefile": generated_image,
        "image_file": generated_image,
        
        # 音频参数 - 兼容多种节点类型
        "audio": audio_path,
        "audiofile": audio_path,
        "audio_file": audio_path,
        "file": audio_path,
        "input_file": audio_path,
    }
    
    # 🔍 调试日志
    logger.debug(f"🎬 工作流参数: {workflow_params}")
    
    result = await pixelle_video.execute_with_concurrency(workflow_input, workflow_params)

    # If the result contains an error status, propagate the original error
    if result.status == "error":
        error_msg = result.msg or "Unknown workflow execution error"
        raise RuntimeError(f"Second workflow execution failed: {error_msg}")

    generated_video_url = _extract_video_url(result)
    if not generated_video_url:
        raise RuntimeError("The second step of the workflow did not return a video.")

    return await _download_to_file(generated_video_url, final_video_path)


def _burn_overlays_sync(
    video_path: str,
    request_body: DigitalHumanRequest,
    task_dir: str,
    video_width: int,
    video_height: int,
    video_duration: float,
) -> str:
    """
    同步叠加层烧录函数：标题叠加 + 个人名片 + BGM
    使用 OverlayService 生成帧图像，通过 FFmpeg overlay 叠加到视频上
    """
    rb = request_body

    try:
        import subprocess
        import json
        import ffmpeg

        overlay_service = OverlayService()
        video_service = VideoService()
        current_video = video_path

        # 关键修复：从实际视频文件中读取视频时长，替换传入的 audio_duration
        # 避免全视频模式（display_mode=full）因为传入了音频时长而非视频时长导致显示异常
        actual_video_duration = video_duration
        try:
            probe = ffmpeg.probe(video_path)
            video_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
            if video_stream:
                actual_video_duration = float(probe['format']['duration'])
                logger.info(f"[叠层] 从视频文件读取实际时长: {actual_video_duration:.2f}s (传入: {video_duration:.2f}s)")
        except Exception as e:
            logger.warning(f"[叠层] 无法从视频文件读取时长，使用传入值 {video_duration:.2f}s: {e}")
            actual_video_duration = video_duration

        # 1. 标题叠加
        try:
            title_cfg = TitleOverlayConfig.from_dict(rb.title_overlay_config if hasattr(rb, 'title_overlay_config') else {})
            if title_cfg.enabled and title_cfg.text:
                logger.info(f"[叠层] 标题叠加配置: enabled={title_cfg.enabled}, text={title_cfg.text}, "
                           f"display_mode={title_cfg.display_mode}, duration_seconds={title_cfg.duration_seconds}, "
                           f"actual_video_duration={actual_video_duration:.2f}s")
                title_dir = overlay_service.generate_title_overlay_frames(
                    config=title_cfg,
                    video_width=video_width,
                    video_height=video_height,
                    output_dir=task_dir,
                    video_duration=actual_video_duration,
                )
                if title_dir:
                    title_output = os.path.join(task_dir, "with_title.mp4")
                    video_service.burn_subtitle_frames(
                        video=current_video,
                        subtitle_dir=title_dir,
                        output=title_output,
                    )
                    if os.path.exists(title_output):
                        current_video = title_output
                        logger.info(f"✅ [叠层] 标题叠加成功: {title_output}")
        except Exception as e:
            logger.exception(f"⚠️ [叠层] 标题叠加失败，继续后续处理: {e}")

        # 2. 个人名片
        try:
            card_cfg = BusinessCardConfig.from_dict(rb.business_card_config if hasattr(rb, 'business_card_config') else {})
            if card_cfg.enabled and card_cfg.title:
                logger.info(f"[叠层] 个人名片配置: enabled={card_cfg.enabled}, title={card_cfg.title}, "
                           f"display_mode={card_cfg.display_mode}, duration_seconds={card_cfg.duration_seconds}, "
                           f"actual_video_duration={actual_video_duration:.2f}s")
                card_dir = overlay_service.generate_business_card_frames(
                    config=card_cfg,
                    video_width=video_width,
                    video_height=video_height,
                    output_dir=task_dir,
                    video_duration=actual_video_duration,
                )
                if card_dir:
                    card_output = os.path.join(task_dir, "with_card.mp4")
                    video_service.burn_subtitle_frames(
                        video=current_video,
                        subtitle_dir=card_dir,
                        output=card_output,
                    )
                    if os.path.exists(card_output):
                        current_video = card_output
                        logger.info(f"✅ [叠层] 个人名片叠加成功: {card_output}")
        except Exception as e:
            logger.exception(f"⚠️ [叠层] 个人名片叠加失败，继续后续处理: {e}")

        # 3. 背景音乐
        try:
            bgm_cfg = BgmOverlayConfig.from_dict(rb.bgm_config if hasattr(rb, 'bgm_config') else {})
            if bgm_cfg.enabled:
                # 解析 BGM 路径
                bgm_path = bgm_cfg.custom_bgm or bgm_cfg.selected_bgm
                if bgm_path:
                    volume = max(0.0, min(1.0, bgm_cfg.volume / 100.0))
                    bgm_output = os.path.join(task_dir, "with_bgm.mp4")
                    video_service.add_bgm(
                        video=current_video,
                        bgm=bgm_path,
                        output=bgm_output,
                        bgm_volume=volume,
                        loop=True,
                    )
                    if os.path.exists(bgm_output):
                        current_video = bgm_output
                        logger.info(f"✅ [叠层] 背景音乐叠加成功: {bgm_output}")
        except Exception as e:
            logger.exception(f"⚠️ [叠层] 背景音乐叠加失败，继续后续处理: {e}")

        return current_video
    except Exception as e:
        logger.exception(f"⚠️ [叠层] 叠加层处理整体异常，返回原视频: {e}")
        return video_path


def _burn_subtitles_sync(
    video_path: str,
    request_body: DigitalHumanRequest,
    generated_text: str,
    audio_path: str,
    task_dir: str,
) -> str:
    """
    同步字幕烧录函数（在 thread pool 中执行）
    如果字幕开启，生成字幕帧并叠加到视频上
    """
    subtitle_config = request_body.subtitle_config
    # 🔍 关键调试日志：打印接收到的字幕配置实际值
    logger.info(
        f"🎬 [字幕烧录入口] video_path={video_path}, "
        f"subtitle_config.enabled={getattr(subtitle_config, 'enabled', 'NO_CFG')}, "
        f"text_len={len(generated_text) if generated_text else 0}, "
        f"audio_path_exists={os.path.exists(audio_path) if audio_path else False}"
    )
    if not subtitle_config or not subtitle_config.enabled:
        logger.warning(
            f"⚠️  字幕开关未启用，跳过字幕烧录。subtitle_config={subtitle_config}"
        )
        return video_path

    if not generated_text or not generated_text.strip():
        logger.warning("⚠️  generated_text 为空，无法生成字幕，跳过字幕烧录")
        return video_path

    if not os.path.exists(video_path):
        logger.error(f"❌ 源视频文件不存在，无法烧录字幕：{video_path}")
        return video_path

    if not os.path.exists(audio_path):
        logger.error(f"❌ 音频文件不存在，无法获取时长：{audio_path}")
        return video_path

    try:
        cfg_model = SubtitleConfigModel.from_dict(subtitle_config.model_dump())
        subtitle_service = SubtitleService()

        # 获取音频时长
        video_service = VideoService()
        audio_duration = video_service._get_audio_duration(audio_path)
        logger.info(f"🎬 音频时长={audio_duration:.2f}s, 字幕文本前30字={generated_text[:30]!r}")

        # 生成 SRT 字幕文件
        srt_path = subtitle_service.generate_srt_file(
            text=generated_text,
            audio_duration=audio_duration,
            output_dir=task_dir,
        )
        logger.info(f"✅ SRT subtitle file generated: {srt_path}")

        # 获取实际视频分辨率，不再硬编码
        import ffmpeg
        probe = ffmpeg.probe(video_path)
        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        if not video_stream:
            logger.error(f"❌ 无法读取视频流信息，无法烧录字幕: {video_path}")
            return video_path
        video_width = int(video_stream['width'])
        video_height = int(video_stream['height'])
        logger.info(f"🎬 实际视频分辨率: {video_width}x{video_height}")

        # 前端配置是基于1080x1920设计的，需要按实际分辨率比例缩放参数
        design_width = 1080
        design_height = 1920
        scale_factor_width = video_width / design_width
        scale_factor_height = video_height / design_height
        # 取较小的缩放因子保持比例一致
        scale_factor = min(scale_factor_width, scale_factor_height)
        logger.info(f"🎬 字幕参数缩放比例: {scale_factor:.4f} (宽: {scale_factor_width:.4f}, 高: {scale_factor_height:.4f})")

        # 缩放所有字幕配置参数
        cfg_model.font_size = max(12, int(cfg_model.font_size * scale_factor))
        cfg_model.max_width = int(cfg_model.max_width * scale_factor)
        cfg_model.position_x = int(cfg_model.position_x * scale_factor)
        cfg_model.position_y = int(cfg_model.position_y * scale_factor)
        cfg_model.background_radius = max(0, int(cfg_model.background_radius * scale_factor))
        cfg_model.letter_spacing = max(0, int(cfg_model.letter_spacing * scale_factor))
        if cfg_model.font_border_width > 0:
            cfg_model.font_border_width = max(1, int(cfg_model.font_border_width * scale_factor))
        
        # 缩放padding
        pad_parts = (cfg_model.background_padding or '10 20').split(' ')
        scaled_pad = []
        for p in pad_parts:
            p = p.strip()
            if p.isdigit():
                scaled_pad.append(str(max(1, int(int(p) * scale_factor))))
        if scaled_pad:
            cfg_model.background_padding = ' '.join(scaled_pad)

        # 生成字幕帧
        frames_dir = subtitle_service.generate_subtitle_frames(
            text=generated_text,
            audio_duration=audio_duration,
            config=cfg_model,
            output_dir=task_dir,
            video_width=video_width,
            video_height=video_height,
            fps=30,
        )

        if not frames_dir:
            logger.warning("⚠️  No subtitle frames generated, skipping subtitle burn")
            return video_path

        # 烧录字幕到视频
        subtitled_path = os.path.join(task_dir, "final_subtitled.mp4")
        video_service.burn_subtitle_frames(
            video=video_path,
            subtitle_dir=frames_dir,
            output=subtitled_path,
            fps=30,
        )

        if not os.path.exists(subtitled_path):
            logger.error(f"❌ 字幕烧录完成但输出文件不存在：{subtitled_path}")
            return video_path

        logger.info(f"✅ Subtitles burned to video: {subtitled_path}")
        return subtitled_path
    except Exception as e:
        # 🔒 关键：字幕烧录失败不应导致整个数字人流程失败
        # 此前异常会向上抛，使任务 FAILED；现在改为退化为返回原视频
        logger.exception(f"❌ 字幕烧录异常，将返回原始视频（无字幕）：{e}")
        return video_path


async def _run_digital_human_pipeline(
    pixelle_video: Any,
    request_body: DigitalHumanRequest,
    user_id: str = "",
    priority: int = 0,
    task_id: str = "",
) -> str:
    task_dir, _task_id = create_task_output_dir()
    final_video_path = os.path.join(task_dir, "final.mp4")
    audio_path = os.path.join(task_dir, "narration.mp3")
    cfg = request_body.workflow_config

    character_assets = request_body.character_assets
    goods_assets = request_body.goods_assets

    if not character_assets:
        raise ValueError("Please upload at least one character image.")

    if not request_body.goods_text.strip():
        raise ValueError("Please provide speech text.")

    async def get_script_text() -> str:
        return request_body.goods_text.strip()

    generated_text = await get_script_text()

    # ===== Check if remote ComfyUI mode is enabled =====
    try:
        comfyui_cfg = config_manager.get_comfyui_config()
        rc = comfyui_cfg.get("remote_comfy", {})
        remote_enabled = rc.get("enabled", False)
        remote_base_url = rc.get("base_url", "")
    except Exception:
        remote_enabled = False
        remote_base_url = ""

    if remote_enabled and remote_base_url:
        logger.info(f"🌐 Using remote ComfyUI mode: {remote_base_url}")
        
        # ===== [实例管理] 自动确保有就绪镜像机并获取动态地址 =====
        assigned_instance_uuid = None
        effective_base_url = remote_base_url  # 默认使用主控机地址
        monitor = None  # 预初始化，确保后续引用安全
        
        try:
            from pixelle_video.services.instance_manager import get_global_monitor
            monitor = get_global_monitor()
            if monitor._running:
                comfyui_cfg_all = config_manager.get_comfyui_config()
                # 使用 autodl_api_key 作为实例管理 Token，与 runninghub_api_key 完全独立
                autodl_token = comfyui_cfg_all.get("autodl_api_key") or monitor._default_token or ""
                # ⭐ 使用优先级队列调度（新版本）
                # 如果任务已经被 task_manager 创建，使用其 task_id
                task_id_for_queue = task_id if task_id else ""
                if not task_id_for_queue:
                    import uuid
                    task_id_for_queue = str(uuid.uuid4())
                result = await monitor.enqueue_and_wait(
                    task_id=task_id_for_queue,
                    user_id=user_id,
                    priority=priority,
                    token=autodl_token,
                )
                if result:
                    dynamic_mirror_url, assigned_instance_uuid = result
                    # 使用动态分配的镜像机地址，而不是固定的主控机地址
                    effective_base_url = dynamic_mirror_url
                    # 通知 monitor 该实例有新的任务
                    monitor.on_task_submitted(assigned_instance_uuid)
                    logger.info(f"✅ [实例管理] 优先级队列分配镜像机: {dynamic_mirror_url} (instance={assigned_instance_uuid}, priority={priority})")
                else:
                    # ⭐ 如果 enqueue_and_wait 返回 None（任务被取消/超时）
                    # 不应该降级使用默认面板，而是让任务失败，保证排队机制的完整性
                    logger.warning("⚠️ [实例管理] 无法获取就绪镜像机")
            else:
                logger.info("⏹️ [实例管理] 自动扩缩容未启动，跳过")
        except Exception as e:
            logger.warning(f"⚠️ [实例管理] enqueue_and_wait 异常，继续使用默认面板: {e}")
        
        # Get workflow IDs from config:
        compose_workflow_id = rc.get("customize_workflow_id", "digital_customize")
        video_workflow_id = rc.get("video_workflow_id", "digital_combination")
        
        # Generate TTS locally first
        await _run_tts(pixelle_video, request_body, generated_text, audio_path)
        
        # Create remote ComfyUI service with the dynamically assigned mirror URL
        remote_svc = RemoteComfyService(effective_base_url)
        try:
            if request_body.mode == "customize":
                # 口播模式: 人物图 + 音频 → 直接走 digital_combination 生成口播视频
                _, final_video_local = await remote_svc.run_digital_human_workflow(
                    image_workflow_id="",
                    video_workflow_id=video_workflow_id,
                    character_image_path=character_assets[0],
                    audio_path=audio_path,
                    output_dir=task_dir,
                )
                final_path = final_video_local
            else:
                goods_image = goods_assets[0] if goods_assets else None
                _, final_video_local = await remote_svc.run_digital_human_workflow(
                    image_workflow_id=compose_workflow_id if goods_image else "",
                    video_workflow_id=video_workflow_id,
                    character_image_path=character_assets[0],
                    audio_path=audio_path,
                    goods_image_path=goods_image,
                    goods_type=request_body.goods_title,
                    output_dir=task_dir,
                )
                final_path = final_video_local

            # ===== 字幕烧录 =====
            if request_body.subtitle_config and request_body.subtitle_config.enabled:
                final_path = _burn_subtitles_sync(final_path, request_body, generated_text, audio_path, task_dir)

            # ===== 标题叠加 + 个人名片 =====
            try:
                import ffmpeg
                probe = ffmpeg.probe(final_path)
                video_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
                if video_stream:
                    vw, vh = int(video_stream['width']), int(video_stream['height'])
                    vs = VideoService()
                    dur = vs._get_audio_duration(audio_path)
                    final_path = _burn_overlays_sync(final_path, request_body, task_dir, vw, vh, dur)
            except Exception as e:
                logger.exception(f"⚠️ [叠层] 远程模式 overlays 处理异常: {e}")
            
            return final_path
        finally:
            # 无论成功还是失败，都确保任务计数被释放
            if assigned_instance_uuid and monitor is not None and monitor._running:
                try:
                    monitor.on_task_completed(assigned_instance_uuid)
                except Exception as e:
                    logger.warning(f"⚠️ [实例管理] on_task_completed 异常: {e}")
            await remote_svc.close()

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
        final_path = await _download_to_file(media_result.url, final_video_path)

        # ===== 字幕烧录 =====
        if request_body.subtitle_config and request_body.subtitle_config.enabled:
            final_path = _burn_subtitles_sync(final_path, request_body, generated_text, audio_path, task_dir)

        # ===== 标题叠加 + 个人名片 =====
        try:
            import ffmpeg
            probe = ffmpeg.probe(final_path)
            video_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
            if video_stream:
                vw, vh = int(video_stream['width']), int(video_stream['height'])
                vs = VideoService()
                dur = vs._get_audio_duration(audio_path)
                final_path = _burn_overlays_sync(final_path, request_body, task_dir, vw, vh, dur)
        except Exception as e:
            logger.exception(f"⚠️ [叠层] api_video_workflow 模式 overlays 处理异常: {e}")

        return final_path

    if request_body.mode == "customize":
        generated_image = character_assets[0]
        await _run_tts(pixelle_video, request_body, generated_text, audio_path)
        if not cfg.second_workflow_path:
            raise ValueError("second_workflow_path is required for customize mode.")
        final_path = await _run_second_digital_workflow(
            pixelle_video,
            workflow_path_str=cfg.second_workflow_path,
            generated_image=generated_image,
            audio_path=audio_path,
            final_video_path=final_video_path,
        )

        # ===== 字幕烧录 =====
        if request_body.subtitle_config and request_body.subtitle_config.enabled:
            final_path = _burn_subtitles_sync(final_path, request_body, generated_text, audio_path, task_dir)

        # ===== 标题叠加 + 个人名片 =====
        try:
            import ffmpeg
            probe = ffmpeg.probe(final_path)
            video_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
            if video_stream:
                vw, vh = int(video_stream['width']), int(video_stream['height'])
                vs = VideoService()
                dur = vs._get_audio_duration(audio_path)
                final_path = _burn_overlays_sync(final_path, request_body, task_dir, vw, vh, dur)
        except Exception as e:
            logger.exception(f"⚠️ [叠层] customize 模式 overlays 处理异常: {e}")

        return final_path

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
        workflow_params = (
            {"firstimage": character_assets[0], "secondimage": goods_assets[0]}
            if request_body.goods_text.strip()
            else {
                "firstimage": character_assets[0],
                "secondimage": goods_assets[0],
                "goodstype": request_body.goods_title,
            }
        )
        image_result = await pixelle_video.execute_with_concurrency(workflow_input, workflow_params)
        generated_image = _extract_image_url(image_result)
        if not generated_image:
            raise RuntimeError("The image workflow did not return an image.")

        if not request_body.goods_text.strip() and hasattr(image_result, "texts") and image_result.texts:
            generated_text = image_result.texts[0]

    await _run_tts(pixelle_video, request_body, generated_text, audio_path)
    if not cfg.second_workflow_path:
        raise ValueError("second_workflow_path is required for digital mode.")

    final_path = await _run_second_digital_workflow(
        pixelle_video,
        workflow_path_str=cfg.second_workflow_path,
        generated_image=generated_image,
        audio_path=audio_path,
        final_video_path=final_video_path,
    )

    # ===== 字幕烧录 =====
    if request_body.subtitle_config and request_body.subtitle_config.enabled:
        final_path = _burn_subtitles_sync(final_path, request_body, generated_text, audio_path, task_dir)

    # ===== 标题叠加 + 个人名片 =====
    try:
        import ffmpeg
        probe = ffmpeg.probe(final_path)
        video_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
        if video_stream:
            vw, vh = int(video_stream['width']), int(video_stream['height'])
            vs = VideoService()
            dur = vs._get_audio_duration(audio_path)
            final_path = _burn_overlays_sync(final_path, request_body, task_dir, vw, vh, dur)
    except Exception as e:
        logger.exception(f"⚠️ [叠层] digital 模式 overlays 处理异常: {e}")

    return final_path


def _task_response(task_id: str) -> AsyncTaskResponse:
    return AsyncTaskResponse(task_id=task_id)


class SubtitlePreviewRequest(BaseModel):
    """字幕预览请求"""
    text: str = Field(..., description="文案内容")
    audio_duration: float = Field(..., description="音频时长（秒）")
    video_width: int = Field(1080, description="视频宽度")
    video_height: int = Field(1920, description="视频高度")
    video_path: Optional[str] = Field(None, description="实际视频路径，如果提供则使用该视频替代 demo 视频")
    subtitle_config: SubtitleRequestConfig = Field(default_factory=SubtitleRequestConfig)

    # 标题叠加和个人名片配置（预览时也一并渲染）
    title_overlay_config: dict[str, Any] = Field(default_factory=lambda: {
        "enabled": False, "text": "", "font_size": 56, "font_color": "#FFFFFF",
        "font_weight": 700, "position_x": 0, "position_y": -800,
        "display_mode": "full", "duration_seconds": 5,
    })
    business_card_config: dict[str, Any] = Field(default_factory=lambda: {
        "enabled": False, "title": "", "subtitle": "",
        "display_mode": "full", "duration_seconds": 5,
    })
    bgm_config: dict[str, Any] = Field(default_factory=lambda: {
        "enabled": False, "selected_bgm": None, "volume": 50, "custom_bgm": None,
    })


class SubtitlePreviewResponse(BaseModel):
    """字幕预览响应"""
    success: bool = True
    preview_video_url: str = ""
    subtitle_url: str = ""
    message: str = ""


class ApplyEffectsRequest(BaseModel):
    """应用后处理效果请求"""
    video_path: str = Field(..., description="原始视频路径")
    goods_text: str = Field("", description="口播文案")
    subtitle_config: SubtitleRequestConfig = Field(default_factory=SubtitleRequestConfig)
    title_overlay_config: dict[str, Any] = Field(default_factory=lambda: {
        "enabled": False, "text": "", "font_size": 56, "font_color": "#FFFFFF",
        "font_weight": 700, "position_x": 0, "position_y": -800,
        "display_mode": "duration", "duration_seconds": 2,
    })
    business_card_config: dict[str, Any] = Field(default_factory=lambda: {
        "enabled": False, "title": "", "subtitle": "",
        "display_mode": "duration", "duration_seconds": 2,
    })
    bgm_config: dict[str, Any] = Field(default_factory=lambda: {
        "enabled": False, "selected_bgm": None, "volume": 50, "custom_bgm": None,
    })


class ApplyEffectsResponse(BaseModel):
    """应用后处理效果响应"""
    success: bool = True
    video_url: str = ""
    message: str = ""


@router.post("/digital-human/subtitle-preview", response_model=SubtitlePreviewResponse)
async def subtitle_preview(
    request_body: SubtitlePreviewRequest,
    request: Request,
):
    """
    字幕预览 API
    生成带字幕的预览视频（使用 demo 视频 shu-09.mp4）
    """
    try:
        import shutil
        from pixelle_video.utils.os_util import create_task_output_dir

        # 创建临时工作目录
        task_dir, _task_id = create_task_output_dir()
        
        import subprocess

        # 限制预览时长 5 秒
        preview_duration = min(request_body.audio_duration, 5.0)

        # 确定使用哪个视频：如果有提供 video_path 则使用实际视频，否则使用 demo 视频
        source_video_path = None
        if request_body.video_path:
            # 尝试直接使用提供的路径
            if os.path.exists(request_body.video_path):
                source_video_path = request_body.video_path
                logger.info(f"🎬 [字幕预览] 使用实际视频: {source_video_path}")
            else:
                # 处理 /api/files/ 开头的 URL
                vp = request_body.video_path
                if "/api/files/" in vp:
                    parts = vp.split("/api/files/")
                    if len(parts) > 1:
                        rel_path = parts[1].replace("%2F", "/").replace("%5C", "/").replace("\\", "/")
                        for root in ["output", "temp"]:
                            candidate = os.path.join(root, rel_path.split(root, 1)[-1] if root in rel_path else rel_path)
                            if os.path.exists(candidate):
                                source_video_path = candidate
                                logger.info(f"🎬 [字幕预览] 从URL解析实际视频: {source_video_path}")
                                break

        if not source_video_path:
            # 回退到 demo 视频
            preview_video_dir = Path("modern_ui/public/videos")
            source_video_path = str(preview_video_dir / "shu-09.mp4")
            if not os.path.exists(source_video_path):
                return SubtitlePreviewResponse(
                    success=False,
                    message=f"Preview video not found: {source_video_path}"
                )
            logger.info(f"🎬 [字幕预览] 使用 demo 视频: {source_video_path}")

        # 从源视频中截取前5秒作为预览基础
        preview_video_short = os.path.join(task_dir, "preview_short.mp4")
        subprocess.run(
            ["ffmpeg", "-y", "-i", source_video_path, "-t", "5",
             "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
             "-c:a", "aac", "-ar", "22050", "-ac", "1", preview_video_short],
            capture_output=True, text=True, check=True,
        )

        # 获取截取视频的实际分辨率
        import ffmpeg
        probe = ffmpeg.probe(preview_video_short)
        video_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
        if video_stream:
            preview_video_width = int(video_stream['width'])
            preview_video_height = int(video_stream['height'])
            logger.info(f"🎬 [字幕预览] 预览视频分辨率: {preview_video_width}x{preview_video_height}")
        else:
            preview_video_width = request_body.video_width or 540
            preview_video_height = request_body.video_height or 960

        # 生成 SRT 字幕文件
        subtitle_service = SubtitleService()
        srt_path = subtitle_service.generate_srt_file(
            text=request_body.text,
            audio_duration=preview_duration,
            output_dir=task_dir,
        )

        # 将 SubtitleRequestConfig 转换为 SubtitleConfigModel
        cfg_model = SubtitleConfigModel.from_dict(request_body.subtitle_config.model_dump())

        # 根据实际视频分辨率缩放字幕参数（配置基于1080x1920设计）
        design_width = 1080
        design_height = 1920
        sf = min(preview_video_width / design_width, preview_video_height / design_height)
        cfg_model.font_size = max(12, int(cfg_model.font_size * sf))
        cfg_model.max_width = int(cfg_model.max_width * sf)
        cfg_model.position_x = int(cfg_model.position_x * sf)
        cfg_model.position_y = int(cfg_model.position_y * sf)
        cfg_model.background_radius = max(0, int(cfg_model.background_radius * sf))
        cfg_model.letter_spacing = max(0, int(cfg_model.letter_spacing * sf))
        if cfg_model.font_border_width > 0:
            cfg_model.font_border_width = max(1, int(cfg_model.font_border_width * sf))
        pad_parts = (cfg_model.background_padding or '10 20').split(' ')
        scaled_pad = []
        for p in pad_parts:
            p = p.strip()
            if p.isdigit():
                scaled_pad.append(str(max(1, int(int(p) * sf))))
        if scaled_pad:
            cfg_model.background_padding = ' '.join(scaled_pad)

        # 生成字幕帧图像（使用实际视频分辨率）
        frames_dir = subtitle_service.generate_subtitle_frames(
            text=request_body.text,
            audio_duration=preview_duration,
            config=cfg_model,
            output_dir=task_dir,
            video_width=preview_video_width,
            video_height=preview_video_height,
            fps=30,
        )

        if not frames_dir:
            return SubtitlePreviewResponse(
                success=False,
                message="No subtitle frames generated"
            )

        # 烧录字幕到预览视频
        video_service = VideoService()
        preview_output = os.path.join(task_dir, "preview_subtitled.mp4")
        video_service.burn_subtitle_frames(
            video=preview_video_short,
            subtitle_dir=frames_dir,
            output=preview_output,
            fps=30,
        )

        # ===== 标题叠加（预览） =====
        current_video = preview_output
        overlay_service = OverlayService()

        # 1. 标题叠加
        try:
            title_cfg = TitleOverlayConfig.from_dict(request_body.title_overlay_config if hasattr(request_body, 'title_overlay_config') else {})
            if title_cfg.enabled and title_cfg.text:
                title_dir = overlay_service.generate_title_overlay_frames(
                    config=title_cfg,
                    video_width=preview_video_width,
                    video_height=preview_video_height,
                    output_dir=task_dir,
                    video_duration=preview_duration,
                    fps=30,
                )
                if title_dir:
                    title_output = os.path.join(task_dir, "preview_with_title.mp4")
                    video_service.burn_subtitle_frames(
                        video=current_video,
                        subtitle_dir=title_dir,
                        output=title_output,
                        fps=30,
                    )
                    if os.path.exists(title_output):
                        current_video = title_output
                        logger.info(f"✅ [预览 - 标题叠加] 成功: {title_output}")
        except Exception as e:
            logger.exception(f"⚠️ [预览 - 标题叠加] 失败: {e}")

        # 2. 个人名片
        try:
            card_cfg = BusinessCardConfig.from_dict(request_body.business_card_config if hasattr(request_body, 'business_card_config') else {})
            if card_cfg.enabled and card_cfg.title:
                card_dir = overlay_service.generate_business_card_frames(
                    config=card_cfg,
                    video_width=preview_video_width,
                    video_height=preview_video_height,
                    output_dir=task_dir,
                    video_duration=preview_duration,
                    fps=30,
                )
                if card_dir:
                    card_output = os.path.join(task_dir, "preview_with_card.mp4")
                    video_service.burn_subtitle_frames(
                        video=current_video,
                        subtitle_dir=card_dir,
                        output=card_output,
                        fps=30,
                    )
                    if os.path.exists(card_output):
                        current_video = card_output
                        logger.info(f"✅ [预览 - 个人名片] 成功: {card_output}")
        except Exception as e:
            logger.exception(f"⚠️ [预览 - 个人名片] 失败: {e}")

        # 3. 背景音乐（预览）
        try:
            bgm_cfg = BgmOverlayConfig.from_dict(request_body.bgm_config if hasattr(request_body, 'bgm_config') else {})
            if bgm_cfg.enabled:
                bgm_path = bgm_cfg.custom_bgm or bgm_cfg.selected_bgm
                if bgm_path:
                    volume = max(0.0, min(1.0, bgm_cfg.volume / 100.0))
                    bgm_output = os.path.join(task_dir, "preview_with_bgm.mp4")
                    video_service.add_bgm(
                        video=current_video,
                        bgm=bgm_path,
                        output=bgm_output,
                        bgm_volume=volume,
                        loop=True,
                    )
                    if os.path.exists(bgm_output):
                        current_video = bgm_output
                        logger.info(f"✅ [预览 - 背景音乐] 成功: {bgm_output}")
        except Exception as e:
            logger.exception(f"⚠️ [预览 - 背景音乐] 失败: {e}")

        preview_output = current_video

        # 生成预览视频 URL
        preview_url = path_to_url(request, preview_output) if Path(preview_output).exists() else ""

        # SRT 预览 URL（用于 <track> 标签）
        srt_url = path_to_url(request, srt_path) if Path(srt_path).exists() else ""

        return SubtitlePreviewResponse(
            success=True,
            preview_video_url=preview_url,
            subtitle_url=srt_url,
            message="字幕预览生成成功"
        )

    except Exception as e:
        logger.error(f"Subtitle preview error: {e}")
        return SubtitlePreviewResponse(
            success=False,
            message=str(e)
        )


@router.post("/digital-human/apply-effects", response_model=ApplyEffectsResponse)
async def apply_effects(
    request_body: ApplyEffectsRequest,
    request: Request,
    _user: UserInfo = Depends(check_daily_limit),
):
    """
    将字幕/标题/名片/BGM等效果应用到已有的视频上（后处理编辑）。
    复用现有的 _burn_subtitles_sync 和 _burn_overlays_sync 函数。
    """
    try:
        video_path = request_body.video_path
        if not video_path or not os.path.exists(video_path):
            # 尝试从 URL 转换为本地路径
            # 如果是 /api/files/ 开头的 URL，转换为本地文件路径
            if video_path and "/api/files/" in video_path:
                # 从 URL 中提取相对路径
                parts = video_path.split("/api/files/")
                if len(parts) > 1:
                    rel_path = parts[1].replace("%2F", "/").replace("%5C", "/").replace("\\", "/")
                    # 尝试多种可能的根目录
                    for root in ["output", "temp"]:
                        candidate = os.path.join(root, rel_path.split(root, 1)[-1] if root in rel_path else rel_path)
                        if os.path.exists(candidate):
                            video_path = candidate
                            break

        if not video_path or not os.path.exists(video_path):
            return ApplyEffectsResponse(
                success=False,
                message=f"原始视频文件不存在: {video_path}"
            )

        goods_text = request_body.goods_text.strip()
        if not goods_text:
            return ApplyEffectsResponse(
                success=False,
                message="文案为空，无法生成字幕"
            )

        # 获取视频文件所在目录作为 task_dir
        task_dir = os.path.dirname(video_path)
        if not task_dir:
            task_dir = os.path.join("output", "temp_effects")
            os.makedirs(task_dir, exist_ok=True)

        # 获取视频分辨率
        import ffmpeg
        probe = ffmpeg.probe(video_path)
        video_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
        if not video_stream:
            return ApplyEffectsResponse(
                success=False,
                message="无法读取视频流信息"
            )
        video_width = int(video_stream['width'])
        video_height = int(video_stream['height'])
        logger.info(f"🎬 [ApplyEffects] 视频分辨率: {video_width}x{video_height}, path={video_path}")

        # 获取视频时长
        video_duration = float(probe['format']['duration'])

        # 使用 ffmpeg 从视频中提取一段音频用于字幕时长计算
        audio_path = os.path.join(task_dir, "extracted_audio.mp3")
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-i", video_path, "-vn", "-acodec", "libmp3lame", "-ar", "22050", "-ac", "1",
                 audio_path],
                capture_output=True, text=True, check=True, timeout=60,
            )
        except Exception as e:
            logger.warning(f"[ApplyEffects] 提取音频失败，使用估算时长: {e}")
            audio_path = ""

        # ===== 1. 字幕烧录 =====
        current_video = video_path
        if request_body.subtitle_config.enabled:
            try:
                # 构造一个 DigitalHumanRequest 兼容对象
                class ReqProxy:
                    pass
                proxy = ReqProxy()
                proxy.subtitle_config = request_body.subtitle_config
                proxy.title_overlay_config = request_body.title_overlay_config
                proxy.business_card_config = request_body.business_card_config
                proxy.bgm_config = request_body.bgm_config

                subtitled = _burn_subtitles_sync(
                    video_path=current_video,
                    request_body=proxy,
                    generated_text=goods_text,
                    audio_path=audio_path,
                    task_dir=task_dir,
                )
                if subtitled and os.path.exists(subtitled):
                    current_video = subtitled
                    logger.info(f"✅ [ApplyEffects] 字幕烧录成功: {subtitled}")
            except Exception as e:
                logger.exception(f"⚠️ [ApplyEffects] 字幕烧录异常，继续: {e}")

        # ===== 2. 标题叠加 + 个人名片 + BGM =====
        try:
            overlayed = _burn_overlays_sync(
                video_path=current_video,
                request_body=proxy,
                task_dir=task_dir,
                video_width=video_width,
                video_height=video_height,
                video_duration=video_duration,
            )
            if overlayed and os.path.exists(overlayed):
                current_video = overlayed
                logger.info(f"✅ [ApplyEffects] 叠加层处理成功: {overlayed}")
        except Exception as e:
            logger.exception(f"⚠️ [ApplyEffects] 叠加层处理异常: {e}")

        # 生成结果视频 URL
        if os.path.exists(current_video):
            video_url = path_to_url(request, current_video)
            return ApplyEffectsResponse(
                success=True,
                video_url=video_url,
                message="效果应用成功"
            )
        else:
            return ApplyEffectsResponse(
                success=False,
                message="处理后的视频文件不存在"
            )

    except Exception as e:
        logger.exception(f"❌ [ApplyEffects] 处理异常: {e}")
        return ApplyEffectsResponse(
            success=False,
            message=str(e)
        )


@router.post("/digital-human/async", response_model=AsyncTaskResponse)
async def generate_digital_human_async(
    request_body: DigitalHumanRequest,
    pixelle_video: PixelleVideoDep,
    request: Request,
    _user: UserInfo = Depends(check_daily_limit),
):
    user_id = _user.id
    # 🔍 入口日志
    logger.info(
        f"📨 [数字人请求入口] mode={request_body.mode}, "
        f"goods_text_len={len(request_body.goods_text)}, "
        f"subtitle.enabled={request_body.subtitle_config.enabled}"
    )
    # Pre-deduct daily usage immediately at submission time
    await increment_daily_usage(user_id)

    # ====== ZS币预冻结：使用统一正则去除标点，计算预估时长（1秒=4字，计入语速因子） ======
    # 必须与前端 DigitalHumanView.vue 中 estimatedSeconds computed 逻辑完全一致
    frozen_zs = 0
    task_id_for_log = None
    goods_text = request_body.goods_text or ""
    clean_text = re.sub(PATTERN_CLEAN_TEXT, '', goods_text)
    tts_speed = max(0.5, min(3.0, getattr(request_body, 'tts_speed', 1.0)))
    # 基础：ceil(有效字数 / 4 / 语速) = 预估秒数（与前端公式完全一致）
    estimated_seconds = max(1, math.ceil(len(clean_text) / 4 / tts_speed)) if clean_text else 0
    if estimated_seconds > 0:
        ok, frozen, msg = await freeze_balance(user_id, estimated_seconds)
        if not ok:
            await decrement_daily_usage(user_id)
            raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=msg)
        frozen_zs = frozen
        task_id_for_log = f"dh_{int(datetime.now().timestamp())}_{user_id}"
        await Database.execute(
            "INSERT INTO generation_log (task_id, user_id, estimated_seconds, frozen_zs, status) "
            "VALUES (%s, %s, %s, %s, 'frozen')",
            (task_id_for_log, user_id, estimated_seconds, frozen_zs)
        )

    try:
        task = task_manager.create_task(TaskType.VIDEO_GENERATION, request_body.model_dump(), user_id=str(user_id))

        async def execute():
            nonlocal frozen_zs, task_id_for_log
            task_manager.update_progress(task.task_id, 80, 100, "preparing")
            try:
                final_path = await _run_digital_human_pipeline(
                    pixelle_video, request_body,
                    user_id=str(user_id),
                    priority=_get_user_priority(_user.role),
                    task_id=task.task_id,
                )
            except asyncio.CancelledError:
                # ZS币退款（取消任务时全额退还）
                if task_id_for_log and frozen_zs > 0:
                    await settle_generation(task_id_for_log, user_id, frozen_zs, 0, success=False)
                await decrement_daily_usage(user_id)
                raise
            except Exception:
                # ZS币退款（生成失败）
                if task_id_for_log and frozen_zs > 0:
                    await settle_generation(task_id_for_log, user_id, frozen_zs, 0, success=False)
                # Refund daily usage
                await decrement_daily_usage(user_id)
                raise

            # ====== ZS币结算（生成成功）：读取实际音频时长，按实际时长多退少补 ======
            deducted_zs = 0
            if task_id_for_log and frozen_zs > 0:
                actual_seconds = estimated_seconds  # 后备值
                # 获取 TTS 生成的音频文件路径，读出实际音频时长进行结算
                task_dir = None
                if os.path.exists(final_path):
                    task_dir = os.path.dirname(final_path)
                audio_path_candidate = os.path.join(task_dir, "narration.mp3") if task_dir else ""
                if audio_path_candidate and os.path.exists(audio_path_candidate):
                    try:
                        vs = VideoService()
                        audio_duration = vs._get_audio_duration(audio_path_candidate)
                        actual_seconds = max(1, round(audio_duration))
                        logger.info(f"💰 [ZS币结算] 读取实际音频时长={audio_duration:.2f}s → actual_seconds={actual_seconds}")
                    except Exception as e:
                        logger.warning(f"💰 [ZS币结算] 读取音频时长失败，使用预估时长: {e}")
                else:
                    logger.warning(f"💰 [ZS币结算] 音频文件不存在: {audio_path_candidate}，使用预估时长")

                settle_result = await settle_generation(task_id_for_log, user_id, frozen_zs, actual_seconds, success=True)
                deducted_zs = settle_result.get("deducted_zs", 0)

            await save_web_generation_history(
                pixelle_video,
                task_id=Path(final_path).parent.name if Path(final_path).exists() else task.task_id,
                video_path=final_path,
                pipeline="digital_human",
                title="数字人口播",
                input_params=request_body.model_dump(),
                user_id=user_id,
                deducted_zs=deducted_zs,
                frozen_zs=frozen_zs,
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
        # ZS币退款（生成失败）
        if task_id_for_log and frozen_zs > 0:
            await settle_generation(task_id_for_log, user_id, frozen_zs, 0, success=False)
        # Refund daily usage
        await decrement_daily_usage(user_id)
        logger.exception(exc)
        raise HTTPException(status_code=500, detail=str(exc))