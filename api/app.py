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
Pixelle-Video FastAPI Application

Main FastAPI app with all routers and middleware.

Run this script to start the FastAPI server:
    uv run python api/app.py
    
Or with custom settings:
    uv run python api/app.py --host 0.0.0.0 --port 8080 --reload
"""

import sys
from pathlib import Path

# Add project root to sys.path for module imports
# This ensures imports work correctly in both development and packaged environments
_script_dir = Path(__file__).resolve().parent
_project_root = _script_dir.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import argparse
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from api.config import api_config
from api.tasks import task_manager
from api.dependencies import shutdown_pixelle_video
from api.auth.database import Database
from pixelle_video.services.instance_manager import get_global_monitor
from pixelle_video.config import config_manager

# Import routers
from pixelle_video.patches.comfykit_patch import apply_patches

from api.routers import (
    config_router,
    health_router,
    llm_router,
    tts_router,
    image_router,
    content_router,
    video_router,
    tasks_router,
    files_router,
    resources_router,
    frame_router,
    pipelines_router,
    audio_router,
    media_extract_router,
    instances_router,
)
from api.auth.router import router as auth_router
from api.auth.sms_router import router as sms_router
from api.payment.router import router as payment_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("🚀 Starting Pixelle-Video API...")
    apply_patches()  # Apply comfykit monkey patches
    await task_manager.start()
    
    # Auto-start auto-scaling monitor if configured
    try:
        comfyui_cfg = config_manager.get_comfyui_config()
        rc = comfyui_cfg.get("remote_comfy", {})
        panel_base_url = rc.get("base_url", "")
        token = comfyui_cfg.get("runninghub_api_key", "")
        if panel_base_url and token:
            monitor = get_global_monitor()
            monitor.panel_base_url = panel_base_url
            await monitor.start(token=token)
            logger.info("✅ Auto-scaling monitor auto-started on server boot")
        elif panel_base_url and not token:
            logger.warning("⚠️ Auto-scaling monitor not started: AutoDL token not configured (runninghub_api_key)")
        else:
            logger.info("ℹ️ Auto-scaling monitor not started: remote_comfy panel not configured")
    except Exception as e:
        logger.warning(f"⚠️ Failed to auto-start auto-scaling monitor: {e}")
    
    # Initialize MySQL database connection and auto-create tables
    try:
        await Database.get_pool()
        await Database.init_tables()
        logger.info("✅ MySQL database connected and tables initialized")
    except Exception as e:
        logger.warning(f"⚠️ MySQL database connection failed: {e}")
        logger.warning("Auth features will be unavailable until database is configured")
    
    logger.info("✅ Pixelle-Video API started successfully\n")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Pixelle-Video API...")
    await task_manager.stop()
    await shutdown_pixelle_video()
    await Database.close()
    # Stop auto-scaling monitor
    try:
        monitor = get_global_monitor()
        if monitor.is_running():
            await monitor.stop()
            logger.info("✅ Auto-scaling monitor stopped")
    except Exception as e:
        logger.warning(f"⚠️ Failed to stop auto-scaling monitor: {e}")
    logger.info("✅ Pixelle-Video API shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Pixelle-Video API",
    description="""
    ## Pixelle-Video - AI Video Generation Platform API
    
    ### Features
    - 🤖 **LLM**: Large language model integration
    - 🔊 **TTS**: Text-to-speech synthesis
    - 🎨 **Image**: AI image generation
    - 📝 **Content**: Automated content generation
    - 🎬 **Video**: End-to-end video generation
    
    ### Video Generation Modes
    - **Sync**: `/api/video/generate/sync` - For small videos (< 30s)
    - **Async**: `/api/video/generate/async` - For large videos with task tracking
    
    ### Getting Started
    1. Check health: `GET /health`
    2. Generate narrations: `POST /api/content/narration`
    3. Generate video: `POST /api/video/generate/sync` or `/async`
    4. Track task progress: `GET /api/tasks/{task_id}`
    """,
    version="0.1.0",
    docs_url=api_config.docs_url,
    redoc_url=api_config.redoc_url,
    openapi_url=api_config.openapi_url,
    lifespan=lifespan,
)

# Add CORS middleware
if api_config.cors_enabled:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=api_config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info(f"CORS enabled for origins: {api_config.cors_origins}")

# Include routers
# Health check (no prefix)
app.include_router(health_router)

# API routers (with /api prefix)
app.include_router(config_router, prefix=api_config.api_prefix)
app.include_router(llm_router, prefix=api_config.api_prefix)
app.include_router(tts_router, prefix=api_config.api_prefix)
app.include_router(image_router, prefix=api_config.api_prefix)
app.include_router(content_router, prefix=api_config.api_prefix)
app.include_router(video_router, prefix=api_config.api_prefix)
app.include_router(tasks_router, prefix=api_config.api_prefix)
app.include_router(files_router, prefix=api_config.api_prefix)
app.include_router(resources_router, prefix=api_config.api_prefix)
app.include_router(frame_router, prefix=api_config.api_prefix)
app.include_router(pipelines_router, prefix=api_config.api_prefix)
app.include_router(audio_router, prefix=api_config.api_prefix)
app.include_router(media_extract_router, prefix=api_config.api_prefix)
app.include_router(instances_router, prefix=api_config.api_prefix)

# Auth router (with /api prefix)
app.include_router(auth_router, prefix=api_config.api_prefix)
app.include_router(sms_router, prefix=api_config.api_prefix)

# Payment router (with /api prefix)
app.include_router(payment_router, prefix=api_config.api_prefix)

# Modern UI (Vue 3 + Element Plus + TypeScript) - SPA mode at root path
_modern_ui_dir = _project_root / "modern_ui"
_modern_ui_dist = _modern_ui_dir / "dist"
_modern_ui_index = _modern_ui_dist / "index.html"

if _modern_ui_dist.exists() and _modern_ui_index.exists():
    # Mount static assets directory
    _assets_dir = _modern_ui_dist / "assets"
    if _assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="ui-assets")

    # Mount other known static directories if they exist
    for _dir_name in ["videos", "images", "fonts"]:
        _dir_path = _modern_ui_dist / _dir_name
        if _dir_path.exists():
            app.mount(f"/{_dir_name}", StaticFiles(directory=str(_dir_path)), name=f"ui-{_dir_name}")

    # Serve frontend at root path
    @app.get("/")
    async def serve_frontend():
        """Serve the frontend SPA"""
        return FileResponse(str(_modern_ui_index))

    # SPA fallback middleware: for any 404 GET request to non-API paths,
    # serve index.html so Vue Router can handle client-side routing
    class _SPAFallbackMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            response = await call_next(request)
            if response.status_code == 404 and request.method == "GET":
                path = request.url.path
                # Don't intercept API, docs, health endpoints
                if not path.startswith(("/api", "/docs", "/redoc", "/openapi.json", "/health")):
                    # Try to serve static files from dist/ root (e.g. favicon.png, wechat.png)
                    file_path = _modern_ui_dist / path.lstrip("/")
                    if file_path.exists() and file_path.is_file():
                        return FileResponse(str(file_path))
                    # SPA fallback: let Vue Router handle client-side routing
                    return FileResponse(str(_modern_ui_index))
            return response

    app.add_middleware(_SPAFallbackMiddleware)

    logger.info("✅ Modern UI (SPA mode) mounted at /")
else:
    # Frontend not built - show API info as before
    @app.get("/")
    async def root():
        """Root endpoint with API information"""
        return {
            "service": "Pixelle-Video API",
            "version": "0.1.0",
            "docs": api_config.docs_url,
            "health": "/health",
            "api": {
                "llm": f"{api_config.api_prefix}/llm",
                "tts": f"{api_config.api_prefix}/tts",
                "image": f"{api_config.api_prefix}/image",
                "content": f"{api_config.api_prefix}/content",
                "video": f"{api_config.api_prefix}/video",
                "tasks": f"{api_config.api_prefix}/tasks",
                "files": f"{api_config.api_prefix}/files",
                "resources": f"{api_config.api_prefix}/resources",
                "frame": f"{api_config.api_prefix}/frame",
                "pipelines": f"{api_config.api_prefix}/pipelines",
            }
        }


if __name__ == "__main__":
    import uvicorn
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Start Pixelle-Video API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    
    args = parser.parse_args()
    
    # Print startup banner
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                    Pixelle-Video API Server                      ║
╚══════════════════════════════════════════════════════════════╝

Starting server at http://{args.host}:{args.port}
API Docs: http://{args.host}:{args.port}/docs
ReDoc: http://{args.host}:{args.port}/redoc

Press Ctrl+C to stop the server
""")
    
    # Start server
    uvicorn.run(
        "api.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )

