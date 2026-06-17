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
Douyin video transcription endpoint

Parses a Douyin (TikTok China) share link, uses Playwright to open the page,
extracts the video's audio track via ffmpeg, then performs ASR (speech-to-text)
via DashScope to obtain the spoken narration/script from the video.
"""

import asyncio
import os
import re
import shutil
import tempfile
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel

router = APIRouter(prefix="/douyin", tags=["Content Parsing"])


class DouyinTranscribeRequest(BaseModel):
    share_text: str


class DouyinTranscribeResponse(BaseModel):
    success: bool
    text: str
    title: str = ""
    message: str = ""


# Regex to extract douyin short URL from arbitrary share text
_DOUYIN_URL_RE = re.compile(r"https?://v\.douyin\.com/[a-zA-Z0-9_\-]+/?")


def _extract_douyin_url(text: str) -> str | None:
    """Extract the first douyin short URL from the share text."""
    m = _DOUYIN_URL_RE.search(text)
    return m.group(0).rstrip("/") if m else None


def _resolve_redirect_url(short_url: str) -> str | None:
    """
    Follow HTTP redirect to resolve the short URL to the actual video page URL.
    Returns the final redirected URL.
    """
    try:
        resp = httpx.get(
            short_url,
            follow_redirects=True,
            timeout=15.0,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                )
            },
        )
        resp.raise_for_status()
        return str(resp.url)
    except Exception as e:
        logger.warning(f"Failed to resolve douyin URL '{short_url}': {e}")
        return None


async def _fetch_video_url_with_playwright(page_url: str) -> str | None:
    """
    Use Playwright to open the video page and extract the video source URL.
    
    Douyin pages typically embed the video in a <video> tag or a structured data
    attribute. We try multiple strategies:
      1. Find <video> tag with src attribute.
      2. Look for structured JSON data in <script> tags (RENDER_DATA, __INITIAL_STATE__, etc.).
      3. Intercept network responses for video content.
      4. Exhaustive search of all script content for video URLs.
    """
    from playwright.async_api import async_playwright

    for attempt in range(2):
        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                    ],
                )
                context = await browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/125.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1920, "height": 1080},
                    locale="zh-CN",
                )
                page = await context.new_page()

                # Strategy 0: Intercept network responses to capture video URLs
                video_urls_from_network = []

                async def on_response(response):
                    url = response.url
                    # Capture video file requests and m3u8 playlists
                    if any(ext in url.lower() for ext in ['.mp4', '.m3u8', 'playwm', 'video/']):
                        if url not in video_urls_from_network:
                            video_urls_from_network.append(url)
                    # Also check content-type header
                    content_type = response.headers.get('content-type', '')
                    if 'video' in content_type and url not in video_urls_from_network:
                        video_urls_from_network.append(url)

                page.on('response', on_response)

                await page.goto(page_url, wait_until="domcontentloaded", timeout=30000)
                # Wait for video element to appear if possible
                try:
                    await page.wait_for_selector('video', timeout=10000)
                except Exception:
                    pass
                # Additional wait for dynamic content to fully render
                await asyncio.sleep(3)
                # Scroll down to trigger lazy loading
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)

                # Strategy 1: look for <video> element with src
                video_src = await page.evaluate("""
                    () => {
                        const v = document.querySelector('video');
                        if (v) {
                            return v.getAttribute('src') || v.currentSrc || null;
                        }
                        return null;
                    }
                """)
                if video_src:
                    logger.info(f"Found video src via <video> tag: {video_src[:80]}...")
                    return video_src

                # Strategy 2: extract from JSON-LD / structured data in scripts
                json_src = await page.evaluate("""
                    () => {
                        const scripts = document.querySelectorAll('script');
                        for (const s of scripts) {
                            const txt = s.textContent || '';
                            try {
                                // Try RENDER_DATA (douyin common pattern) - multiple formats
                                // Format 1: window.RENDER_DATA = '...'
                                const raw1 = txt.match(/window\\.RENDER_DATA\\s*=\\s*'([^']+)'/);
                                if (raw1) {
                                    const decoded = decodeURIComponent(raw1[1]);
                                    const data = JSON.parse(decoded);
                                    const str = JSON.stringify(data);
                                    const m = str.match(/"video_url":\\s*"([^"]+)"/);
                                    if (m) return m[1];
                                }
                                // Format 2: RENDER_DATA = "..." (double quotes, escaped)
                                const raw2 = txt.match(/RENDER_DATA\\s*=\\s*"((?:[^"\\\\]|\\\\.)*)"/);
                                if (raw2) {
                                    const decoded = raw2[1].replace(/\\\\"/g, '"').replace(/\\\\n/g, '');
                                    if (decoded.includes('video_url')) {
                                        const str = decodeURIComponent(decoded);
                                        const m = str.match(/"video_url":\\s*"([^"]+)"/);
                                        if (m) return m[1];
                                    }
                                }
                                // Try __INITIAL_STATE__ (alternative pattern)
                                if (txt.includes('__INITIAL_STATE__')) {
                                    const raw3 = txt.match(/window\\.__INITIAL_STATE__\\s*=\\s*({.+?});/);
                                    if (raw3) {
                                        const data = JSON.parse(raw3[1]);
                                        const str = JSON.stringify(data);
                                        const m = str.match(/"video_url":\\s*"([^"]+)"/);
                                        if (m) return m[1];
                                    }
                                }
                                // Try __NEXT_DATA__ (Next.js pages)
                                if (s.id === '__NEXT_DATA__') {
                                    const data = JSON.parse(txt);
                                    const str = JSON.stringify(data);
                                    const m = str.match(/"video_url":\\s*"([^"]+)"/);
                                    if (m) return m[1];
                                }
                                // Try window.__NUXT__ (Nuxt.js pages)
                                if (txt.includes('__NUXT__')) {
                                    const raw4 = txt.match(/window\\.__NUXT__\\s*=\\s*({.+?});/);
                                    if (raw4) {
                                        const data = JSON.parse(raw4[1]);
                                        const str = JSON.stringify(data);
                                        const m = str.match(/"video_url":\\s*"([^"]+)"/);
                                        if (m) return m[1];
                                    }
                                }
                            } catch(e) {
                                // Ignore parse errors for individual scripts
                            }
                        }
                        return null;
                    }
                """)
                if json_src:
                    logger.info(f"Found video src via JSON data: {json_src[:80]}...")
                    return json_src

                # Strategy 3: try to get poster/src from any video-like element
                any_src = await page.evaluate("""
                    () => {
                        const all = document.querySelectorAll('[src]');
                        for (const el of all) {
                            const s = el.getAttribute('src') || '';
                            if (s.includes('.mp4') || s.includes('video') || s.includes('playwm') || s.includes('m3u8')) {
                                return s;
                            }
                        }
                        return null;
                    }
                """)
                if any_src:
                    logger.info(f"Found video src via attribute search: {any_src[:80]}...")
                    return any_src

                # Strategy 4: check network captured URLs (from interception)
                if video_urls_from_network:
                    # Prefer mp4 URLs over others
                    mp4_urls = [u for u in video_urls_from_network if '.mp4' in u.lower()]
                    target = mp4_urls[0] if mp4_urls else video_urls_from_network[0]
                    logger.info(f"Found video URL via network interception: {target[:80]}...")
                    return target

                # Strategy 5: exhaustive script content search for any video URL pattern
                script_video = await page.evaluate("""
                    () => {
                        const scripts = document.querySelectorAll('script');
                        const candidates = [];
                        for (const s of scripts) {
                            const txt = s.textContent || '';
                            // Search for various video URL patterns in script content
                            // Pattern: "play_url": { "url_list": ["..."] }
                            const playUrlMatch = txt.match(/"play_url"[^}]*"url_list"[^[]*\\[\\s*"([^"]+)"/);
                            if (playUrlMatch) candidates.push(playUrlMatch[1]);
                            // Pattern: "video": { "play_addr": { "url_list": ["..."] } }
                            const playAddrMatch = txt.match(/"play_addr"[^}]*"url_list"[^[]*\\[\\s*"([^"]+)"/);
                            if (playAddrMatch) candidates.push(playAddrMatch[1]);
                            // Pattern: "video_url": "..."
                            const videoUrlMatch = txt.match(/"video_url":\\s*"([^"]+)"/);
                            if (videoUrlMatch) candidates.push(videoUrlMatch[1]);
                            // Pattern: "source_url": "..."
                            const sourceUrlMatch = txt.match(/"source_url":\\s*"([^"]+)"/);
                            if (sourceUrlMatch) candidates.push(sourceUrlMatch[1]);
                            // Direct mp4/m3u8 URL in script
                            const directMatch = txt.match(/https?:\\/\\/[^"\\s'<>]+?\\.(mp4|m3u8)[^"\\s'<>]*/);
                            if (directMatch) candidates.push(directMatch[0]);
                        }
                        // Filter out duplicates and return the first valid candidate
                        for (const c of candidates) {
                            if (c && (c.startsWith('http://') || c.startsWith('https://') || c.startsWith('//'))) {
                                return c.startsWith('//') ? 'https:' + c : c;
                            }
                        }
                        return null;
                    }
                """)
                if script_video:
                    logger.info(f"Found video src via script content search: {script_video[:80]}...")
                    return script_video

                logger.warning("Failed to extract video URL from the page")
                return None

        except Exception as e:
            logger.warning(f"Playwright attempt {attempt + 1} failed: {e}")
            if attempt == 0:
                await asyncio.sleep(1)
                continue
            return None


async def _download_and_transcribe(video_url: str) -> str:
    """
    Download the video file, extract audio using ffmpeg, then run ASR.
    
    Returns the transcribed text.
    """
    temp_dir = tempfile.mkdtemp(prefix="douyin_asr_")
    try:
        video_path = os.path.join(temp_dir, "douyin_video.mp4")
        audio_path = os.path.join(temp_dir, "douyin_audio.wav")

        # Download video
        logger.info(f"Downloading video: {video_url[:80]}...")
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(
                video_url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/125.0.0.0 Safari/537.36"
                    ),
                    "Referer": "https://www.douyin.com/",
                },
                follow_redirects=True,
            )
            resp.raise_for_status()
            with open(video_path, "wb") as f:
                f.write(resp.content)
        logger.info(f"Video downloaded ({os.path.getsize(video_path)} bytes)")

        # Extract audio using ffmpeg
        ffmpeg_path = shutil.which("ffmpeg")
        if not ffmpeg_path:
            raise RuntimeError("ffmpeg not found, cannot extract audio")

        logger.info("Extracting audio with ffmpeg...")
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
            raise RuntimeError(f"ffmpeg audio extraction failed (code={proc.returncode})")

        logger.info(f"Audio extracted ({os.path.getsize(audio_path)} bytes)")

        # Run ASR
        from pixelle_video.services.dashscope_asr import get_asr_service

        asr_service = get_asr_service()
        text = asr_service.transcribe(audio_path)
        return text

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@router.post("/transcribe", response_model=DouyinTranscribeResponse)
async def douyin_transcribe(request: DouyinTranscribeRequest):
    """
    Parse a Douyin share link, download the video, transcribe the audio,
    and return the spoken text (narration/script).
    
    - **share_text**: The full share text copied from Douyin app, containing the URL.
    
    Returns the transcribed text and video title (if available).
    """
    try:
        # Step 1: Extract URL
        url = _extract_douyin_url(request.share_text)
        if not url:
            raise HTTPException(
                status_code=400,
                detail="未找到抖音分享链接，请确认分享内容包含 https://v.douyin.com/ 格式的链接"
            )
        logger.info(f"Extracted douyin URL: {url}")

        # Step 2: Resolve redirect to get actual page URL
        page_url = _resolve_redirect_url(url)
        if not page_url:
            raise HTTPException(
                status_code=400,
                detail="无法解析抖音分享链接，链接可能已失效"
            )
        logger.info(f"Resolved page URL: {page_url}")

        # Step 3: Extract video source URL via Playwright
        video_url = await _fetch_video_url_with_playwright(page_url)
        if not video_url:
            raise HTTPException(
                status_code=502,
                detail="无法提取抖音视频源地址，页面结构可能已变更"
            )

        # Step 4: Download video and run ASR
        text = await _download_and_transcribe(video_url)
        if not text or not text.strip():
            return DouyinTranscribeResponse(
                success=False,
                text="",
                message="语音识别完成，但未提取到有效文本（视频可能没有语音或语音不清晰）"
            )

        logger.info(f"Transcription completed: {text[:100]}...")
        return DouyinTranscribeResponse(
            success=True,
            text=text.strip(),
            title=Path(page_url).stem,
            message="语音识别成功"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Douyin transcription error: {e}")
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")