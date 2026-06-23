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
File service endpoints

Provides per-user file upload with storage limit enforcement.
Each user can only view/use their own uploaded files.
"""

import uuid
import os
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, Depends, Request
from fastapi.responses import FileResponse, Response
from loguru import logger

from api.config import api_config
from api.auth.dependencies import require_user
from api.auth.database import Database
from api.auth.schemas import UserInfo

router = APIRouter(prefix="/files", tags=["Files"])


def _get_storage_limit(role: str) -> int:
    """Get storage limit for a role. -1 means unlimited."""
    return api_config.storage_limits.get(role, api_config.storage_limits["normal"])


def _format_bytes(size: int) -> str:
    """Format bytes to human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"


@router.get("/user/list")
async def list_user_uploads(
    category: str = "",
    user: UserInfo = Depends(require_user),
):
    """
    List uploaded files for the current user.
    
    Args:
        category: Optional filter by category (image, video, audio, ref_audio, etc.)
    
    Returns list of the user's upload records.
    """
    try:
        if category:
            rows = await Database.fetchall(
                "SELECT id, file_path, original_name, file_size, category, created_at "
                "FROM user_uploads WHERE user_id = %s AND category = %s "
                "ORDER BY created_at DESC LIMIT 100",
                (user.id, category),
            )
        else:
            rows = await Database.fetchall(
                "SELECT id, file_path, original_name, file_size, category, created_at "
                "FROM user_uploads WHERE user_id = %s "
                "ORDER BY created_at DESC LIMIT 100",
                (user.id,),
            )

        records = []
        for row in rows:
            raw_path = row["file_path"]
            # Normalize to forward slashes
            normalized = raw_path.replace('\\', '/')
            # Extract relative path from absolute path (find "temp/uploads/" or use as-is if already relative)
            idx = normalized.find('temp/uploads/')
            if idx >= 0:
                relative_path = normalized[idx:]
            else:
                relative_path = normalized
            records.append({
                "id": row["id"],
                "category": row["category"],
                "name": row["original_name"],
                "filename": row["original_name"],
                "file_size": row["file_size"],
                "path": raw_path,
                "relative_path": relative_path,
                "url": f"/api/files/{relative_path}",
                "created_at": row["created_at"].isoformat() if isinstance(row["created_at"], datetime) else str(row["created_at"]),
            })

        return {"success": True, "records": records}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"List user uploads error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/usage")
async def get_user_storage_usage(
    user: UserInfo = Depends(require_user),
):
    """
    Get storage usage statistics for the current user.
    
    Returns used bytes and limit based on user role.
    """
    try:
        row = await Database.fetchone(
            "SELECT COALESCE(SUM(file_size), 0) as total_bytes FROM user_uploads WHERE user_id = %s",
            (user.id,),
        )
        used_bytes = row["total_bytes"] if row else 0
        limit_bytes = _get_storage_limit(user.role)

        return {
            "success": True,
            "used_bytes": used_bytes,
            "limit_bytes": limit_bytes,
            "used_display": _format_bytes(used_bytes),
            "limit_display": _format_bytes(limit_bytes) if limit_bytes > 0 else "无限制",
            "is_unlimited": limit_bytes == -1,
            "usage_percent": 0 if limit_bytes <= 0 else round(used_bytes / limit_bytes * 100, 1),
        }

    except Exception as e:
        logger.error(f"Get storage usage error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/user/delete/{file_id}")
async def delete_user_upload(
    file_id: int,
    user: UserInfo = Depends(require_user),
):
    """
    Delete an uploaded file for the current user.
    
    Only the owner can delete their own files.
    """
    try:
        row = await Database.fetchone(
            "SELECT id, file_path FROM user_uploads WHERE id = %s AND user_id = %s",
            (file_id, user.id),
        )
        if not row:
            raise HTTPException(status_code=404, detail="文件不存在或无权删除")

        # Delete physical file
        file_path = Path(row["file_path"])
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted file: {file_path}")

        # Delete DB record
        await Database.execute(
            "DELETE FROM user_uploads WHERE id = %s AND user_id = %s",
            (file_id, user.id),
        )

        return {"success": True, "message": "文件已删除"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete user upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    category: str = Form("misc"),
    user: UserInfo = Depends(require_user),
):
    """
    Upload a file for the current authenticated user.

    Files are stored under temp/uploads/{user_id}/{category}/ and are only
    accessible by the uploader. Storage limit is enforced per user role.
    """
    try:
        allowed_categories = {
            "image",
            "video",
            "audio",
            "ref_audio",
            "character_image",
            "goods_image",
            "misc",
        }
        safe_category = category if category in allowed_categories else "misc"

        original_name = Path(file.filename or "upload.bin").name
        suffix = Path(original_name).suffix.lower()
        allowed_suffixes = {
            ".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".heif",
            ".mp4", ".mov", ".avi", ".mkv", ".webm",
            ".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".amr",
        }
        if suffix not in allowed_suffixes:
            raise HTTPException(status_code=400, detail=f"不支持的文件类型: {suffix}")

        content = await file.read()
        file_size = len(content)

        # Check single file size limit
        if file_size > api_config.max_upload_size:
            max_display = _format_bytes(api_config.max_upload_size)
            raise HTTPException(
                status_code=413,
                detail=f"单个文件过大，最大允许 {max_display}",
            )

        # Check per-user storage limit
        limit_bytes = _get_storage_limit(user.role)
        if limit_bytes > 0:
            row = await Database.fetchone(
                "SELECT COALESCE(SUM(file_size), 0) as total_bytes FROM user_uploads WHERE user_id = %s",
                (user.id,),
            )
            used_bytes = row["total_bytes"] if row else 0
            if used_bytes + file_size > limit_bytes:
                used_display = _format_bytes(used_bytes)
                limit_display = _format_bytes(limit_bytes)
                raise HTTPException(
                    status_code=413,
                    detail=f"存储空间已满（已用 {used_display} / {limit_display}），请清理空间后继续上传",
                )

        # Store file in user-specific directory
        upload_dir = Path("temp") / "uploads" / str(user.id) / safe_category
        upload_dir.mkdir(parents=True, exist_ok=True)

        # ======== 格式自动转换（兼容 RunningHub 工作流）========
        # RunningHub 工作流仅支持: 图片 JPG/PNG, 音频 MP3
        # 非目标格式的文件用 ffmpeg 自动转换后存储

        # 需要转换的图片格式 -> 目标格式 .jpg
        convert_image_suffixes = {".heic", ".heif", ".gif", ".webp", ".bmp", ".tiff", ".tif"}
        # 需要转换的音频格式 -> 目标格式 .mp3
        convert_audio_suffixes = {".wav", ".flac", ".m4a", ".aac", ".ogg", ".amr", ".opus", ".wma"}

        new_suffix = suffix  # 默认保持原后缀
        need_convert = False

        if suffix in convert_image_suffixes:
            new_suffix = ".jpg"
            need_convert = True
        elif suffix in convert_audio_suffixes:
            new_suffix = ".mp3"
            need_convert = True

        # 安全文件名：仅保留 ASCII 字母数字，去掉中文等非 ASCII 字符（避免 URL 中文问题导致手机端播放失败）
        import re
        safe_stem = re.sub(r'[^a-zA-Z0-9_-]', '_', Path(original_name).stem).strip('_') or "audio"
        stored_name = f"{safe_stem}_{uuid.uuid4().hex[:8]}{new_suffix}"
        stored_path = upload_dir / stored_name

        if need_convert:
            try:
                # 写入临时文件
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                    tmp.write(content)
                    tmp_path = tmp.name
                try:
                    if new_suffix == ".jpg":
                        # 图片转 JPG
                        subprocess.run(
                            ["ffmpeg", "-y", "-i", tmp_path, "-q:v", "3", str(stored_path)],
                            capture_output=True, timeout=30, check=True
                        )
                    else:
                        # 音频转 MP3
                        subprocess.run(
                            ["ffmpeg", "-y", "-i", tmp_path, "-q:a", "2", str(stored_path)],
                            capture_output=True, timeout=120, check=True
                        )
                    # 更新文件大小
                    content = stored_path.read_bytes()
                    file_size = len(content)
                    logger.info(f"Converted {original_name} -> {stored_name}")
                except subprocess.CalledProcessError as convert_err:
                    logger.error(f"FFmpeg conversion failed for {original_name}: {convert_err.stderr.decode()}")
                    # 转换失败：降级为原始格式存储
                    stored_name = f"{safe_stem}_{uuid.uuid4().hex[:8]}{suffix}"
                    stored_path = upload_dir / stored_name
                    stored_path.write_bytes(content)
                    logger.warning(f"Saved {original_name} as-is (fallback): {stored_name}")
                finally:
                    Path(tmp_path).unlink(missing_ok=True)
            except Exception as convert_err:
                logger.error(f"Conversion failed for {original_name}: {convert_err}")
                # 降级：直接保存原始文件
                stored_name = f"{safe_stem}_{uuid.uuid4().hex[:8]}{suffix}"
                stored_path = upload_dir / stored_name
                stored_path.write_bytes(content)
                logger.warning(f"Saved {original_name} as-is (error fallback): {stored_name}")
        else:
            # 已是目标格式，直接保存
            stored_path.write_bytes(content)
            logger.info(f"Saved {stored_name} ({_format_bytes(file_size)})")

        relative_path = stored_path.as_posix()

        # Record in database
        await Database.execute(
            "INSERT INTO user_uploads (user_id, file_path, original_name, file_size, category) VALUES (%s, %s, %s, %s, %s)",
            (user.id, str(stored_path.absolute()), original_name, file_size, safe_category),
        )

        logger.info(f"User {user.id} uploaded {stored_name} ({_format_bytes(file_size)}) to {safe_category}")

        return {
            "success": True,
            "filename": original_name,
            "stored_name": stored_name,
            "category": safe_category,
            "file_size": file_size,
            "path": str(stored_path.absolute()),
            "relative_path": relative_path,
            "url": f"/api/files/{relative_path}",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{file_path:path}")
async def get_file(file_path: str, request: Request):
    """
    Get file by path (supports HTTP Range Requests for mobile playback)
    
    Serves files from allowed directories:
    - output/ - Generated files (videos, images, audio)
    - workflows/ - ComfyUI workflow files
    - templates/ - HTML templates
    - bgm/ - Background music
    - data/bgm/ - Custom background music
    - data/templates/ - Custom templates
    - resources/ - Other resources (images, fonts, etc.)
    - temp/uploads/{user_id}/ - User uploaded files
    
    - **file_path**: File path relative to allowed directories
    """
    try:
        # Define allowed directories (in priority order)
        allowed_prefixes = [
            "output/",
            "workflows/",
            "templates/",
            "bgm/",
            "data/bgm/",
            "data/templates/",
            "resources/",
            "docs/",
            "temp/uploads/",
            "pixelle_video/services/code/result/",
        ]
        
        # Check if path starts with allowed prefix, otherwise try output/
        full_path = None
        for prefix in allowed_prefixes:
            if file_path.startswith(prefix):
                full_path = file_path
                break
        
        # If no prefix matched, assume it's in output/ (backward compatibility)
        if full_path is None:
            full_path = f"output/{file_path}"
        
        abs_path = Path.cwd() / full_path
        
        if not abs_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
        
        if not abs_path.is_file():
            raise HTTPException(status_code=400, detail=f"Path is not a file: {file_path}")
        
        # Security: only allow access to specified directories
        try:
            rel_path = abs_path.relative_to(Path.cwd())
            rel_path_str = str(rel_path).replace('\\', '/')
            
            # Check if path starts with any allowed prefix
            is_allowed = any(rel_path_str.startswith(prefix.rstrip('/')) for prefix in allowed_prefixes)
            
            if not is_allowed:
                raise HTTPException(
                    status_code=403, 
                    detail=f"Access denied: only {', '.join(p.rstrip('/') for p in allowed_prefixes)} directories are accessible"
                )
        except ValueError:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Determine media type
        suffix = abs_path.suffix.lower()
        media_types = {
            '.mp4': 'video/mp4',
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.amr': 'audio/amr',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.heic': 'image/heic',
            '.heif': 'image/heif',
            '.html': 'text/html',
            '.json': 'application/json',
        }
        media_type = media_types.get(suffix, 'application/octet-stream')
        
        file_size = abs_path.stat().st_size
        
        # 对 Content-Disposition 中的文件名做 URL 编码（兼容中文文件名，否则手机端无法播放）
        import urllib.parse
        encoded_filename = urllib.parse.quote(abs_path.name)
        content_disposition = f'inline; filename="{abs_path.name}"; filename*=UTF-8\'\'{encoded_filename}'
        
        # Handle HTTP Range Requests (required by mobile Safari/Chrome for audio playback)
        range_header = request.headers.get("range")
        if range_header:
            # Parse range header: "bytes=<start>-<end>"
            try:
                range_val = range_header.strip().replace("bytes=", "")
                if "-" in range_val:
                    parts = range_val.split("-")
                    start = int(parts[0]) if parts[0] else 0
                    end = int(parts[1]) if parts[1] else file_size - 1
                else:
                    start = int(range_val)
                    end = file_size - 1
                
                # Clamp values
                if start >= file_size:
                    # unsatisfiable range
                    return Response(
                        status_code=416,
                        headers={
                            "Content-Range": f"bytes */{file_size}",
                            "Accept-Ranges": "bytes",
                        }
                    )
                end = min(end, file_size - 1)
                content_length = end - start + 1
                
                # Read the partial content
                with open(abs_path, "rb") as f:
                    f.seek(start)
                    chunk = f.read(content_length)
                
                return Response(
                    content=chunk,
                    status_code=206,
                    media_type=media_type,
                    headers={
                        "Content-Range": f"bytes {start}-{end}/{file_size}",
                        "Content-Length": str(content_length),
                        "Accept-Ranges": "bytes",
                        "Content-Disposition": content_disposition,
                        "Cache-Control": "public, max-age=3600",
                    }
                )
            except (ValueError, IndexError):
                # Invalid range, serve full file
                pass
        
        # Full file response (non-range request)
        with open(abs_path, "rb") as f:
            content = f.read()
        
        return Response(
            content=content,
            media_type=media_type,
            headers={
                "Content-Disposition": content_disposition,
                "Accept-Ranges": "bytes",
                "Content-Length": str(file_size),
                "Cache-Control": "public, max-age=3600",
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File access error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
