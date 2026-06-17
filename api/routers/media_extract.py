"""
短视频文案提取接口

将抖音/快手/小红书等平台的分享链接通过哼哼猫 API 提取视频，
再用 ffmpeg 提取音频 + DashScope ASR 语音转文字，最终返回口播文案。

替代原有基于 Playwright 的 douyin.py，更稳定且支持多平台。
"""

import asyncio
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Optional

import aiohttp
from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel

router = APIRouter(prefix="/media", tags=["Content Parsing"])


class MediaTranscribeRequest(BaseModel):
    share_text: str


class MediaTranscribeResponse(BaseModel):
    success: bool
    text: str
    title: str = ""
    message: str = ""
    platform: str = ""


# 哼哼猫 API 配置，优先从环境变量读取
_HHMEOW_API_URL = os.getenv("HHMEOW_API_URL", "https://api.meowload.net/openapi/extract/post")
_HHMEOW_API_KEY = os.getenv("HHMEOW_API_KEY", "")

# 常用短视频平台分享链接正则
_PLATFORM_PATTERNS = {
    "douyin": re.compile(r"https?://v\.douyin\.com/[a-zA-Z0-9_\-]+/?", re.IGNORECASE),
    "kuaishou": re.compile(r"https?://v\.kuaishou\.com/[a-zA-Z0-9_\-]+/?", re.IGNORECASE),
    "xiaohongshu": re.compile(r"https?://(www\.)?xiaohongshu\.com/[a-zA-Z0-9_\-/]+", re.IGNORECASE),
    "bilibili": re.compile(r"https?://(www\.)?bilibili\.com/video/[a-zA-Z0-9_\-/]+", re.IGNORECASE),
}


def _detect_platform(share_text: str) -> tuple[Optional[str], Optional[str]]:
    """
    从分享文本中检测平台，并提取平台链接。
    返回 (platform_name, url) 或 (None, None)
    """
    for platform, pattern in _PLATFORM_PATTERNS.items():
        m = pattern.search(share_text)
        if m:
            url = m.group(0).rstrip("/")
            return platform, url
    return None, None


async def _extract_via_henghengmao(url: str) -> dict:
    """
    通过哼哼猫 API 提取视频信息。
    返回 JSON 包含资源 URL 等信息。
    """
    if not _HHMEOW_API_KEY:
        raise RuntimeError("哼哼猫 API Key 未配置，请在 .env 中设置 HHMEOW_API_KEY")

    logger.info(f"通过哼哼猫 API 提取视频: {url[:80]}...")

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
        async with session.post(
            _HHMEOW_API_URL,
            json={"url": url},
            headers={
                "x-api-key": _HHMEOW_API_KEY,
                "Content-Type": "application/json",
            },
        ) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise RuntimeError(
                    f"哼哼猫 API 请求失败 (HTTP {resp.status}): {error_text[:200]}"
                )
            data = await resp.json()
            logger.debug(f"哼哼猫 API 返回: {str(data)[:200]}...")
            return data


def _extract_video_url(media_data: dict) -> Optional[str]:
    """
    从哼哼猫 API 返回数据中提取视频下载地址。
    兼容多种可能的返回格式。
    """
    # 尝试常见字段路径
    # 格式1: data.resource_url (直接资源链接)
    resource_url = media_data.get("resource_url") or media_data.get("resourceUrl")
    if resource_url:
        return resource_url

    # 格式2: data.data[0].resource_url (数组格式)
    data_field = media_data.get("data") or media_data.get("result") or media_data.get("media") or media_data.get("medias")
    if isinstance(data_field, list) and len(data_field) > 0:
        item = data_field[0]
        url = item.get("resource_url") or item.get("resourceUrl") or item.get("url")
        if url:
            return url
    elif isinstance(data_field, dict):
        url = data_field.get("resource_url") or data_field.get("resourceUrl") or data_field.get("url")
        if url:
            return url

    # 格式3: 返回中直接包含 text（文案），如果有 text 但没有视频 URL，先找 medias
    text = media_data.get("text", "")
    
    # 格式4: 嵌套在 formats 中
    formats = media_data.get("formats")
    if not formats and isinstance(data_field, dict):
        formats = data_field.get("formats")
    if isinstance(formats, list) and len(formats) > 0:
        # 优先取最高清晰度，或返回第一个有效视频 URL
        for fmt in sorted(formats, key=lambda x: x.get("quality", 0) or 0, reverse=True):
            video_url = fmt.get("video_url") or fmt.get("url") or fmt.get("resource_url")
            if video_url:
                return video_url
        # 如果没有 video_url 返回第一个
        first = formats[0]
        return first.get("video_url") or first.get("url") or first.get("resource_url")

    return None


async def _download_and_transcribe(video_url: str) -> str:
    """
    下载视频文件，用 ffmpeg 提取音频，然后运行 ASR 语音识别。
    与原来的 douyin.py 中流程一致。
    """
    temp_dir = tempfile.mkdtemp(prefix="media_asr_")
    try:
        video_path = os.path.join(temp_dir, "media_video.mp4")
        audio_path = os.path.join(temp_dir, "media_audio.wav")

        # 下载视频
        logger.info(f"下载视频: {video_url[:80]}...")
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120)) as client:
            async with client.get(
                video_url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/125.0.0.0 Safari/537.36"
                    ),
                },
            ) as resp:
                # aiohttp 默认自动跟随重定向
                resp.raise_for_status()
                with open(video_path, "wb") as f:
                    f.write(await resp.read())
        logger.info(f"视频下载完成 ({os.path.getsize(video_path)} bytes)")

        # 用 ffmpeg 提取音频
        ffmpeg_path = shutil.which("ffmpeg")
        if not ffmpeg_path:
            raise RuntimeError("ffmpeg 未找到，无法提取音频")

        logger.info("用 ffmpeg 提取音频...")
        proc = await asyncio.create_subprocess_exec(
            ffmpeg_path,
            "-y",
            "-i", video_path,
            "-ac", "1",
            "-ar", "16000",
            "-f", "wav",
            audio_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg 音频提取失败 (code={proc.returncode})")

        logger.info(f"音频提取完成 ({os.path.getsize(audio_path)} bytes)")

        # DashScope ASR 语音识别
        from pixelle_video.services.dashscope_asr import get_asr_service

        asr_service = get_asr_service()
        text = asr_service.transcribe(audio_path)
        return text

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@router.post("/transcribe", response_model=MediaTranscribeResponse)
async def media_transcribe(request: MediaTranscribeRequest):
    """
    解析抖音/快手/小红书/B站等短视频平台分享链接，
    提取视频 → 音频 → 语音转文字，返回口播文案。
    
    - **share_text**: 从 App 复制的分享信息（包含链接即可）
    """
    try:
        # Step 1: 检测平台并提取链接
        platform, url = _detect_platform(request.share_text)
        if not platform or not url:
            raise HTTPException(
                status_code=400,
                detail="未找到支持的短视频分享链接。当前支持：抖音、快手、小红书、B站"
            )
        logger.info(f"检测到平台: {platform}, 链接: {url}")

        # Step 2: 通过哼哼猫 API 获取视频地址
        media_data = await _extract_via_henghengmao(url)
        video_url = _extract_video_url(media_data)
        if not video_url:
            logger.error(f"无法从哼哼猫返回数据提取视频地址: {str(media_data)[:300]}")
            raise HTTPException(
                status_code=502,
                detail="无法从平台提取视频地址，链接可能已失效"
            )
        logger.info(f"提取到视频地址: {video_url[:80]}...")

        # Step 3: 下载视频，提取音频，语音转文字
        text = await _download_and_transcribe(video_url)
        if not text or not text.strip():
            platform_name_map = {
                "douyin": "抖音",
                "kuaishou": "快手",
                "xiaohongshu": "小红书",
                "bilibili": "B站",
            }
            return MediaTranscribeResponse(
                success=False,
                text="",
                platform=platform,
                message=f"{platform_name_map.get(platform, platform)}语音识别完成，但未提取到有效文本（视频可能没有语音或语音不清晰）"
            )

        logger.info(f"语音识别完成: {text[:100]}...")
        return MediaTranscribeResponse(
            success=True,
            text=text.strip(),
            title=Path(url).stem,
            platform=platform,
            message="语音识别成功"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"视频文案提取错误: {e}")
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")