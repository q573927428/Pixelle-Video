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
Config API Router - Read/write system configuration from the modern UI
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Any

from pixelle_video.config import config_manager
from pixelle_video.llm_presets import get_preset_names, get_preset, find_preset_by_base_url_and_model
from pixelle_video.utils.llm_util import fetch_available_models, test_llm_connection
from api.auth.dependencies import require_admin
from api.auth.schemas import UserInfo

router = APIRouter(tags=["config"])


class LLMConfig(BaseModel):
    api_key: str = ""
    base_url: str = ""
    model: str = ""


class ComfyUIConfig(BaseModel):
    comfyui_url: str = "http://127.0.0.1:8188"
    comfyui_api_key: str = ""
    runninghub_api_key: str = ""
    runninghub_concurrent_limit: int = 1
    runninghub_instance_type: str = ""


class APIProviderCommonConfig(BaseModel):
    print_model_input: bool = False
    local_proxy: str = ""


class APIProviderEntry(BaseModel):
    api_key: str = ""
    base_url: str = ""
    use_proxy: bool = False
    access_key: str = ""
    secret_key: str = ""


class FullConfigResponse(BaseModel):
    llm: LLMConfig
    comfyui: ComfyUIConfig
    api_providers: dict[str, Any]
    presets: list[str]


class SaveConfigRequest(BaseModel):
    llm: LLMConfig
    comfyui: ComfyUIConfig
    api_providers: dict[str, Any]


class LoadModelsRequest(BaseModel):
    api_key: str
    base_url: str


class TestConnectionRequest(BaseModel):
    api_key: str
    base_url: str


class LoadModelsResponse(BaseModel):
    models: list[str]


class TestConnectionResponse(BaseModel):
    success: bool
    message: str
    model_count: int = 0


@router.get("/config", response_model=FullConfigResponse)
async def get_config(admin: UserInfo = Depends(require_admin)):
    """Get full system configuration (admin only)"""
    llm_cfg = config_manager.get_llm_config()
    comfyui_cfg = config_manager.get_comfyui_config()
    api_cfg = config_manager.get_api_providers_config()

    return FullConfigResponse(
        llm=LLMConfig(
            api_key=llm_cfg.get("api_key", ""),
            base_url=llm_cfg.get("base_url", ""),
            model=llm_cfg.get("model", ""),
        ),
        comfyui=ComfyUIConfig(
            comfyui_url=comfyui_cfg.get("comfyui_url", "http://127.0.0.1:8188"),
            comfyui_api_key=comfyui_cfg.get("comfyui_api_key", ""),
            runninghub_api_key=comfyui_cfg.get("runninghub_api_key", ""),
            runninghub_concurrent_limit=comfyui_cfg.get("runninghub_concurrent_limit", 1),
            runninghub_instance_type=comfyui_cfg.get("runninghub_instance_type") or "",
        ),
        api_providers=api_cfg,
        presets=get_preset_names(),
    )


@router.put("/config", response_model=dict)
async def save_config(request: SaveConfigRequest, admin: UserInfo = Depends(require_admin)):
    """Save system configuration (admin only)"""
    try:
        # Save LLM config
        if request.llm.api_key and request.llm.base_url and request.llm.model:
            config_manager.set_llm_config(
                api_key=request.llm.api_key,
                base_url=request.llm.base_url,
                model=request.llm.model,
            )

        # Save ComfyUI config
        comfyui_updates = {}
        if request.comfyui.comfyui_url:
            comfyui_updates["comfyui_url"] = request.comfyui.comfyui_url
        if request.comfyui.comfyui_api_key:
            comfyui_updates["comfyui_api_key"] = request.comfyui.comfyui_api_key
        if request.comfyui.runninghub_api_key:
            comfyui_updates["runninghub_api_key"] = request.comfyui.runninghub_api_key
        if request.comfyui.runninghub_concurrent_limit:
            comfyui_updates["runninghub_concurrent_limit"] = request.comfyui.runninghub_concurrent_limit
        comfyui_updates["runninghub_instance_type"] = (
            request.comfyui.runninghub_instance_type
            if request.comfyui.runninghub_instance_type
            else None
        )
        if comfyui_updates:
            config_manager.set_comfyui_config(
                comfyui_url=request.comfyui.comfyui_url or None,
                comfyui_api_key=request.comfyui.comfyui_api_key or None,
                runninghub_api_key=request.comfyui.runninghub_api_key or None,
                runninghub_concurrent_limit=request.comfyui.runninghub_concurrent_limit,
                runninghub_instance_type=request.comfyui.runninghub_instance_type or "",
            )

        # Save API providers config
        for provider_key in ("common", "openai", "dashscope", "ark", "kling"):
            if provider_key in request.api_providers:
                config_manager.set_api_provider_config(
                    provider_key, request.api_providers[provider_key]
                )

        config_manager.save()
        return {"success": True, "message": "Configuration saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config/llm/load-models", response_model=LoadModelsResponse)
async def load_models(request: LoadModelsRequest, admin: UserInfo = Depends(require_admin)):
    """Load available models from LLM provider (admin only)"""
    try:
        models = fetch_available_models(request.api_key, request.base_url)
        return LoadModelsResponse(models=models)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config/preset/{name}", response_model=dict)
async def get_preset_config(name: str, admin: UserInfo = Depends(require_admin)):
    """Get preset configuration by name (admin only)"""
    preset = get_preset(name)
    if not preset:
        raise HTTPException(status_code=404, detail=f"Preset '{name}' not found")
    return preset


@router.get("/config/llm/detect-preset", response_model=dict)
async def detect_preset(admin: UserInfo = Depends(require_admin)):
    """Detect which preset matches current LLM configuration (admin only)"""
    llm_cfg = config_manager.get_llm_config()
    matched = find_preset_by_base_url_and_model(
        llm_cfg.get("base_url", ""),
        llm_cfg.get("model", "")
    )
    return {"preset": matched or "Custom"}


@router.post("/config/llm/test-connection", response_model=TestConnectionResponse)
async def test_connection(request: TestConnectionRequest, admin: UserInfo = Depends(require_admin)):
    """Test LLM provider connection (admin only)"""
    try:
        success, message, model_count = test_llm_connection(request.api_key, request.base_url)
        return TestConnectionResponse(
            success=success,
            message=message,
            model_count=model_count,
        )
    except Exception as e:
        return TestConnectionResponse(
            success=False,
            message=str(e),
            model_count=0,
        )


@router.post("/config/reset", response_model=dict)
async def reset_config(admin: UserInfo = Depends(require_admin)):
    """Reset configuration to defaults (admin only)"""
    try:
        from pixelle_video.config.schema import PixelleVideoConfig
        config_manager.config = PixelleVideoConfig()
        config_manager.save()
        return {"success": True, "message": "Configuration reset to defaults"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))