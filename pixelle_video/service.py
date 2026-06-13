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
Pixelle-Video Core - Service Layer

Provides unified access to all capabilities (LLM, TTS, Image, etc.)
"""

import asyncio
import hashlib
import json
from typing import Optional

from loguru import logger
from comfykit import ComfyKit

from pixelle_video.config import config_manager
from pixelle_video.services.llm_service import LLMService
from pixelle_video.services.tts_service import TTSService
from pixelle_video.services.media import MediaService
from pixelle_video.services.api_media import APIProviderMediaService
from pixelle_video.services.image_analysis import ImageAnalysisService
from pixelle_video.services.video_analysis import VideoAnalysisService
from pixelle_video.services.api_asset_analysis import APIAssetAnalysisService
from pixelle_video.services.video import VideoService
from pixelle_video.services.frame_processor import FrameProcessor
from pixelle_video.services.persistence import PersistenceService
from pixelle_video.services.history_manager import HistoryManager
from pixelle_video.pipelines.standard import StandardPipeline
from pixelle_video.pipelines.custom import CustomPipeline
from pixelle_video.pipelines.asset_based import AssetBasedPipeline


class PixelleVideoCore:
    """
    Pixelle-Video Core - Service Layer
    
    Provides unified access to all capabilities.
    
    Usage:
        from pixelle_video import pixelle_video
        
        # Initialize
        await pixelle_video.initialize()
        
        # Use capabilities directly
        answer = await pixelle_video.llm("Explain atomic habits")
        audio = await pixelle_video.tts("Hello world")
        media = await pixelle_video.media(prompt="a cat")
        
        # Check active capabilities
        print(f"Using LLM: {pixelle_video.llm.active}")
        print(f"Available TTS: {pixelle_video.tts.available}")
    
    Architecture (Simplified):
        PixelleVideoCore (this class)
          ├── config (configuration)
          ├── llm (LLM service - direct OpenAI SDK)
          ├── tts (TTS service - ComfyKit workflows)
          ├── media (Media service - ComfyKit workflows, supports image & video)
          └── pipelines (video generation pipelines)
              ├── standard (standard workflow)
              ├── custom (custom workflow template)
              └── ... (extensible)
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize Pixelle-Video Core
        
        Args:
            config_path: Path to configuration file
        """
        # Use global config manager singleton
        self.config = config_manager.config.to_dict()
        self._initialized = False
        
        # ComfyKit lazy initialization (created on first use, recreated on config change)
        self._comfykit: Optional[ComfyKit] = None
        self._comfykit_config_hash: Optional[str] = None
        self._comfykit_lock = asyncio.Lock()  # 保护 ComfyKit 实例的并发访问

        # Global RunningHub concurrency semaphore.
        # Limits ALL RunningHub workflow executions (pipelines, TTS, media, etc.)
        # to the user-configured concurrent limit, preventing TASK_QUEUE_MAXED.
        # Supports hot-reload: detects config changes via _runninghub_semaphore_limit
        # and recreates the semaphore without requiring a server restart.
        self._runninghub_semaphore: Optional[asyncio.Semaphore] = None
        self._runninghub_semaphore_limit: Optional[int] = None
        
        # Core services (initialized in initialize())
        self.llm: Optional[LLMService] = None
        self.tts: Optional[TTSService] = None
        self.media: Optional[MediaService] = None
        self.api_media: Optional[APIProviderMediaService] = None
        self.video: Optional[VideoService] = None
        self.frame_processor: Optional[FrameProcessor] = None
        self.persistence: Optional[PersistenceService] = None
        self.history: Optional[HistoryManager] = None
        
        # Video generation pipelines (dictionary of pipeline_name -> pipeline_instance)
        self.pipelines = {}
        
        # Default pipeline callable (for backward compatibility)
        self.generate_video = None
    
    def _get_runninghub_concurrent_limit(self) -> int:
        """
        Read the RunningHub concurrent execution limit from config_manager.
        
        This value is configurable via the UI Settings page (runninghub_concurrent_limit).
        """
        try:
            comfyui_cfg = config_manager.get_comfyui_config()
            return int(comfyui_cfg.get("runninghub_concurrent_limit", 1))
        except Exception:
            return 1

    def _get_runninghub_semaphore(self) -> asyncio.Semaphore:
        """
        Get or recreate the global RunningHub concurrency semaphore.
        
        Supports hot-reload: each call checks if the config limit has changed.
        If so, the old semaphore is discarded and a new one is created.
        This allows users to change the concurrency limit via the UI Settings
        page without restarting the server.
        
        NOTE: In-flight tasks holding the old semaphore are not affected.
        The new limit applies to subsequent task submissions.
        """
        current_limit = self._get_runninghub_concurrent_limit()
        
        # Recreate if limit changed
        if self._runninghub_semaphore is not None and self._runninghub_semaphore_limit != current_limit:
            logger.info(
                f"🔒 RunningHub concurrency limit changed from "
                f"{self._runninghub_semaphore_limit} to {current_limit}, "
                f"recreating semaphore (in-flight tasks unaffected)"
            )
            self._runninghub_semaphore = None
            self._runninghub_semaphore_limit = None
        
        # Create if not exists
        if self._runninghub_semaphore is None:
            self._runninghub_semaphore = asyncio.Semaphore(current_limit)
            self._runninghub_semaphore_limit = current_limit
            logger.info(f"🔒 RunningHub concurrency semaphore set to: {current_limit}")
        
        return self._runninghub_semaphore

    async def acquire_runninghub_slot(self) -> None:
        """
        Acquire a RunningHub execution slot.
        
        Call this before any RunningHub workflow execution to ensure
        concurrency limits are respected. If all slots are occupied,
        this will wait until a slot becomes available.
        
        Usage:
            await pixelle_video.acquire_runninghub_slot()
            try:
                result = await kit.execute(workflow_id, params)
            finally:
                pixelle_video.release_runninghub_slot()
        """
        semaphore = self._get_runninghub_semaphore()
        await semaphore.acquire()
        logger.debug(f"RunningHub slot acquired (available: {semaphore._value})")

    def release_runninghub_slot(self) -> None:
        """
        Release a RunningHub execution slot.
        
        Must be called after RunningHub workflow execution completes,
        regardless of success or failure.
        """
        if self._runninghub_semaphore is not None:
            self._runninghub_semaphore.release()
            logger.debug(f"RunningHub slot released (available: {self._runninghub_semaphore._value + 1})")

    async def execute_with_concurrency(
        self,
        workflow_input: str,
        workflow_params: dict,
    ):
        """
        Execute a RunningHub workflow with concurrency limiting.
        
        This is the central execution method that all callers should use
        for RunningHub workflows. It ensures the global concurrency limit
        is respected, preventing TASK_QUEUE_MAXED errors.
        
        Args:
            workflow_input: RunningHub workflow ID or file path
            workflow_params: Workflow parameters
            
        Returns:
            ExecuteResult from ComfyKit
        """
        kit = await self._get_or_create_comfykit()
        await self.acquire_runninghub_slot()
        try:
            result = await kit.execute(workflow_input, workflow_params)
            return result
        finally:
            self.release_runninghub_slot()

    def _get_comfykit_config(self) -> dict:
        """
        Get current ComfyKit configuration from config_manager
        
        Returns:
            ComfyKit configuration dict
        """
        # Reload config from global config_manager (to support hot reload)
        self.config = config_manager.config.to_dict()
        
        comfyui_config = self.config.get("comfyui", {})
        kit_config = {}
        
        if comfyui_config.get("comfyui_url"):
            kit_config["comfyui_url"] = comfyui_config["comfyui_url"]
        if comfyui_config.get("comfyui_api_key"):
            kit_config["api_key"] = comfyui_config["comfyui_api_key"]
        if comfyui_config.get("runninghub_api_key"):
            kit_config["runninghub_api_key"] = comfyui_config["runninghub_api_key"]
        # Only pass instance_type if it has a non-empty value
        instance_type = comfyui_config.get("runninghub_instance_type")
        if instance_type and instance_type.strip():
            kit_config["runninghub_instance_type"] = instance_type
        
        return kit_config
    
    def _compute_comfykit_config_hash(self, config: dict) -> str:
        """
        Compute hash of ComfyKit configuration for change detection
        
        Args:
            config: ComfyKit configuration dict
        
        Returns:
            MD5 hash of config
        """
        # Sort keys for consistent hash
        config_str = json.dumps(config, sort_keys=True)
        return hashlib.md5(config_str.encode()).hexdigest()
    
    async def _get_or_create_comfykit(self) -> ComfyKit:
        """
        Get or create ComfyKit instance (lazy initialization with config change detection)
        
        Thread-safe: uses asyncio.Lock to prevent concurrent initialization races.
        
        This method:
        1. Creates ComfyKit on first use (lazy initialization)
        2. Detects configuration changes and recreates instance if needed
        3. Ensures proper cleanup of old instances
        
        Returns:
            ComfyKit instance
        """
        async with self._comfykit_lock:
            current_config = self._get_comfykit_config()
            current_hash = self._compute_comfykit_config_hash(current_config)
            
            # Check if we need to create or recreate ComfyKit
            if self._comfykit is None or self._comfykit_config_hash != current_hash:
                # Close old instance if exists
                if self._comfykit is not None:
                    logger.info("🔄 ComfyUI configuration changed, recreating ComfyKit instance...")
                    try:
                        await self._comfykit.close()
                    except Exception as e:
                        logger.warning(f"Failed to close old ComfyKit instance: {e}")
                    self._comfykit = None
                
                # Create new instance with current config
                logger.info("✨ Creating ComfyKit instance...")
                # Log config without sensitive fields
                safe_config = {k: v for k, v in current_config.items() if k not in ('api_key', 'runninghub_api_key')}
                logger.debug(f"ComfyKit config: {safe_config}")
                self._comfykit = ComfyKit(**current_config)
                self._comfykit_config_hash = current_hash
                logger.info("✅ ComfyKit instance created")
        
        return self._comfykit
    
    async def initialize(self):
        """
        Initialize core capabilities
        
        This initializes all services and must be called before using any capabilities.
        Note: ComfyKit is NOT initialized here - it's lazily initialized on first use.
        
        Example:
            await pixelle_video.initialize()
        """
        if self._initialized:
            logger.warning("Pixelle-Video already initialized")
            return
        
        logger.info("🚀 Initializing Pixelle-Video...")
        
        # 1. Initialize core services (ComfyKit will be lazy-loaded later)
        # Initialize services
        self.llm = LLMService(self.config)
        self.tts = TTSService(self.config, core=self)
        self.api_media = APIProviderMediaService(self.config, core=self)
        self.media = MediaService(self.config, core=self)
        self.image = self.media  # Alias for backward compatibility
        self.image_analysis = ImageAnalysisService(self.config, core=self)
        self.video_analysis = VideoAnalysisService(self.config, core=self)
        self.api_asset_analysis = APIAssetAnalysisService(self.config, core=self)
        self.video = VideoService()
        self.frame_processor = FrameProcessor(self)
        self.persistence = PersistenceService(output_dir="output")
        self.history = HistoryManager(self.persistence)
        
        # 2. Register video generation pipelines
        self.pipelines = {
            "standard": StandardPipeline(self),
            "custom": CustomPipeline(self),
            "asset_based": AssetBasedPipeline(self),
        }
        logger.info(f"📹 Registered pipelines: {', '.join(self.pipelines.keys())}")
        
        # 3. Set default pipeline callable (for backward compatibility)
        self.generate_video = self._create_generate_video_wrapper()
        
        self._initialized = True
        logger.info("✅ Pixelle-Video initialized successfully\n")
    
    async def cleanup(self):
        """
        Cleanup resources (close ComfyKit session)
        
        Example:
            await pixelle_video.cleanup()
        """
        if self._comfykit:
            logger.info("🧹 Closing ComfyKit session...")
            try:
                await self._comfykit.close()
                logger.info("✅ ComfyKit session closed")
            except Exception as e:
                logger.error(f"Failed to close ComfyKit: {e}")
            finally:
                self._comfykit = None
                self._comfykit_config_hash = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.cleanup()
    
    def _create_generate_video_wrapper(self):
        """
        Create a wrapper function for generate_video that supports pipeline selection
        
        This maintains backward compatibility while adding pipeline support.
        """
        async def generate_video_wrapper(
            text: str,
            pipeline: str = "standard",
            **kwargs
        ):
            """
            Generate video using specified pipeline
            
            Args:
                text: Input text
                pipeline: Pipeline name ("standard", "book_summary", etc.)
                **kwargs: Pipeline-specific parameters
            
            Returns:
                VideoGenerationResult
            
            Examples:
                # Use standard pipeline (default)
                result = await pixelle_video.generate_video(
                    text="如何提高学习效率",
                    n_scenes=5
                )
                
                # Use custom pipeline
                result = await pixelle_video.generate_video(
                    text=your_content,
                    pipeline="custom",
                    custom_param_example="custom_value"
                )
            """
            if pipeline not in self.pipelines:
                available = ", ".join(self.pipelines.keys())
                raise ValueError(
                    f"Unknown pipeline: '{pipeline}'. "
                    f"Available pipelines: {available}"
                )
            
            pipeline_instance = self.pipelines[pipeline]
            return await pipeline_instance(text=text, **kwargs)
        
        return generate_video_wrapper
    
    @property
    def project_name(self) -> str:
        """Get project name from config"""
        return self.config.get("project_name", "Pixelle-Video")
    
    def __repr__(self) -> str:
        """String representation"""
        status = "initialized" if self._initialized else "not initialized"
        pipelines = f"pipelines={list(self.pipelines.keys())}" if self._initialized else ""
        return f"<PixelleVideoCore project={self.project_name!r} status={status} {pipelines}>"


# Global instance
pixelle_video = PixelleVideoCore()