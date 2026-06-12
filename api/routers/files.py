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

Provides access to generated files (videos, images, audio) and resource files.
"""

import json
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from loguru import logger

from api.config import api_config

router = APIRouter(prefix="/files", tags=["Files"])


@router.get("/history/list")
async def list_upload_history(category: str = ""):
    """
    List upload history records.
    
    Args:
        category: Optional filter by category (image, video, audio, ref_audio, etc.)
    
    Returns list of recent upload records.
    """
    try:
        history_path = Path("temp") / "upload_history.json"
        history = []
        if history_path.exists():
            try:
                history = json.loads(history_path.read_text(encoding="utf-8"))
            except Exception:
                history = []
        
        # Filter by category if specified
        if category:
            history = [r for r in history if r.get("category") == category]
        
        # Limit to 50 most recent
        history = history[:50]
        
        return {"success": True, "records": history}
    
    except Exception as e:
        logger.error(f"List upload history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{file_path:path}")
async def get_file(file_path: str):
    """
    Get file by path
    
    Serves files from allowed directories:
    - output/ - Generated files (videos, images, audio)
    - workflows/ - ComfyUI workflow files
    - templates/ - HTML templates
    - bgm/ - Background music
    - data/bgm/ - Custom background music
    - data/templates/ - Custom templates
    - resources/ - Other resources (images, fonts, etc.)
    
    - **file_path**: File path relative to allowed directories
    
    Examples:
    - "abc123.mp4" → output/abc123.mp4
    - "workflows/runninghub/image_flux.json" → workflows/runninghub/image_flux.json
    - "templates/1080x1920/default.html" → templates/1080x1920/default.html
    - "bgm/default.mp3" → bgm/default.mp3
    - "resources/example.png" → resources/example.png
    
    Returns file for download or preview.
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
            "temp/",
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
            rel_path_str = str(rel_path)
            
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
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.html': 'text/html',
            '.json': 'application/json',
        }
        media_type = media_types.get(suffix, 'application/octet-stream')
        
        # Use inline disposition for browser preview
        return FileResponse(
            path=str(abs_path),
            media_type=media_type,
            headers={
                "Content-Disposition": f'inline; filename="{abs_path.name}"'
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File access error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    category: str = Form("misc"),
):
    """
    Upload a file for API/modern UI usage.

    Files are stored under temp/uploads/{category}/ and can be used as local
    paths by generation pipelines or previewed via /api/files/temp/uploads/...
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
            ".jpg", ".jpeg", ".png", ".gif", ".webp",
            ".mp4", ".mov", ".avi", ".mkv", ".webm",
            ".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg",
        }
        if suffix not in allowed_suffixes:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}")

        content = await file.read()
        if len(content) > api_config.max_upload_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Max size is {api_config.max_upload_size} bytes",
            )

        upload_dir = Path("temp") / "uploads" / safe_category
        upload_dir.mkdir(parents=True, exist_ok=True)

        safe_stem = "".join(
            ch if ch.isalnum() or ch in ("-", "_") else "_"
            for ch in Path(original_name).stem
        ).strip("_") or "upload"
        stored_name = f"{safe_stem}_{uuid.uuid4().hex[:8]}{suffix}"
        stored_path = upload_dir / stored_name
        stored_path.write_bytes(content)

        history_path = Path("temp") / "upload_history.json"
        history = []
        if history_path.exists():
            try:
                history = json.loads(history_path.read_text(encoding="utf-8"))
            except Exception:
                history = []

        record = {
            "id": str(uuid.uuid4()),
            "category": safe_category,
            "name": original_name,
            "path": str(stored_path.absolute()),
        }
        history.insert(0, record)
        history_path.parent.mkdir(parents=True, exist_ok=True)
        history_path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")

        relative_path = stored_path.as_posix()
        return {
            "success": True,
            "filename": original_name,
            "stored_name": stored_name,
            "category": safe_category,
            "path": str(stored_path.absolute()),
            "relative_path": relative_path,
            "url": f"/api/files/{relative_path}",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

