"""
Remote ComfyUI Service - Calls zealman API to execute workflows on remote ComfyUI

This service enables the Pixelle-Video pipeline to execute digital human workflows
on a remote ComfyUI instance (e.g., Seetacloud / zealman mirror) instead of via
RunningHub or local ComfyUI.

API Reference: scripts/zealman-api-docs.html (v8.8)

Key endpoints used:
  POST /api/workflow/generate    → Submit workflow task
  GET  /api/workflow/result      → Poll task result
  POST /api/comfy/upload/file    → Upload media files
  GET  /api/workflow/list        → List saved workflows
  GET  /api/workflow/config/{id} → Get workflow config (to resolve node IDs)
"""

import asyncio
import os
import time
from pathlib import Path
from typing import Any, Optional
from loguru import logger
import httpx


class RemoteComfyServiceError(Exception):
    """Base exception for remote ComfyUI service errors"""
    pass


class RemoteComfyService:
    """
    Service for executing workflows on a remote ComfyUI (zealman mirror) instance.
    
    Usage:
        service = RemoteComfyService(base_url="https://...:8443")
        
        # Upload a file
        name = await service.upload_file("/path/to/image.png")
        
        # Run workflow with simple param names (auto-resolves node IDs)
        result_urls = await service.run_workflow(
            workflow_id="digital_customize",
            input_values={
                "videoimage": "uploaded_image.png",
                "audio": "uploaded_audio.mp3"
            }
        )
    """
    
    def __init__(self, base_url: str = ""):
        self.base_url = base_url.rstrip("/")
        self._http_client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(600.0),  # 10 minutes for workflow execution
                follow_redirects=True,
            )
        return self._http_client
    
    async def close(self):
        """Close HTTP client"""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
    
    async def check_health(self) -> bool:
        """Check if the remote ComfyUI panel is alive"""
        try:
            client = await self._get_client()
            resp = await client.get(f"{self.base_url}/api/health", timeout=10.0)
            data = resp.json()
            return data.get("status") == "ok"
        except Exception as e:
            logger.warning(f"Remote ComfyUI health check failed: {e}")
            return False
    
    async def list_workflows(self) -> list[dict]:
        """List all saved API workflows on the remote ComfyUI"""
        try:
            client = await self._get_client()
            resp = await client.get(f"{self.base_url}/api/workflow/list", timeout=10.0)
            data = resp.json()
            if data.get("success"):
                return data.get("workflows", [])
            return []
        except Exception as e:
            logger.error(f"Failed to list remote workflows: {e}")
            return []
    
    async def get_workflow_config(self, workflow_id: str) -> dict:
        """
        Get the full workflow config from remote ComfyUI.
        
        This returns the workflow_template (node ID -> node definition) and
        api_config (enabledParams, formValues, customLabels).
        
        Used to discover node IDs for input_values.
        """
        try:
            client = await self._get_client()
            resp = await client.get(
                f"{self.base_url}/api/workflow/config/{workflow_id}",
                timeout=15.0,
            )
            data = resp.json()
            if data.get("success"):
                return data
            return {}
        except Exception as e:
            logger.warning(f"Failed to get workflow config for '{workflow_id}': {e}")
            return {}
    
    async def resolve_workflow_inputs(
        self,
        workflow_id: str,
        simple_inputs: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Resolve simple parameter names (e.g., 'videoimage', 'audio')
        to zealman API format '节点ID:字段名' (e.g., '12:image', '21:audio').
        
        Uses GET /api/workflow/config/{id} to discover node IDs by matching
        the Primitive node titles ($name.value!) or class_type names.
        
        Args:
            workflow_id: The workflow ID on remote ComfyUI
            simple_inputs: Dict with simple key names (e.g., {"videoimage": "file.png"})
            
        Returns:
            Dict with zealman format keys (e.g., {"12:image": "file.png"})
        """
        # Fetch workflow config to discover node IDs
        config_data = await self.get_workflow_config(workflow_id)
        workflow_template = config_data.get("workflow_template", {})
        api_config = config_data.get("api_config", {})
        
        # Debug: log workflow structure
        logger.debug(f"Workflow '{workflow_id}' template has {len(workflow_template)} nodes")
        for nid, ndef in list(workflow_template.items())[:10]:
            logger.debug(f"  Node {nid}: class_type={ndef.get('class_type')}, title={ndef.get('_meta', {}).get('title')}")
        logger.debug(f"API config keys: {list(api_config.keys())}")
        if api_config.get("enabledParams"):
            logger.debug(f"enabledParams: {api_config['enabledParams']}")
        if api_config.get("customLabels"):
            logger.debug(f"customLabels: {api_config['customLabels']}")
        
        # Strategy 0: Direct node scan - match by node title or input field names
        # This is the most robust approach, works with any workflow structure
        resolved = {}
        simple_keys_lower = {k.lower(): k for k in simple_inputs}
        
        # Collect enabled params (where value is True) and their node info
        enabled_params_raw = api_config.get("enabledParams", {})
        enabled_image_nodes = []  # (node_id, field_name) for LoadImage nodes
        enabled_audio_nodes = []  # (node_id, field_name) for LoadAudio nodes
        
        for node_id, node_def in workflow_template.items():
            class_type = node_def.get("class_type", "").lower()
            inputs = node_def.get("inputs", {})
            
            # Track LoadImage and LoadAudio nodes
            if "loadimage" in class_type:
                for input_key in inputs:
                    param_key = f"{node_id}:{input_key}"
                    is_enabled = enabled_params_raw.get(param_key, False)
                    enabled_image_nodes.append((node_id, input_key, is_enabled))
            if "loadaudio" in class_type or "audioload" in class_type:
                for input_key in inputs:
                    param_key = f"{node_id}:{input_key}"
                    is_enabled = enabled_params_raw.get(param_key, False)
                    enabled_audio_nodes.append((node_id, input_key, is_enabled))
        
        logger.debug(f"Found {len(enabled_image_nodes)} image nodes, {len(enabled_audio_nodes)} audio nodes in workflow")
        
        for simple_key, original_key in simple_keys_lower.items():
            if original_key in resolved:
                continue
            
            value = simple_inputs[original_key]
            
            # Check if this is an image param -> match to LoadImage nodes
            if simple_key in ("image", "videoimage", "firstimage", "secondimage", "character", "goods"):
                # Use first enabled LoadImage node, or first LoadImage node
                if enabled_image_nodes:
                    node_id, input_key, _ = enabled_image_nodes[0]
                    enabled_image_nodes.pop(0)  # Remove used node for next param
                    full_key = f"{node_id}:{input_key}"
                    resolved[original_key] = (full_key, value)
                    logger.info(f"✅ Resolved '{original_key}' -> '{full_key}' (LoadImage node)")
                    continue
            
            # Check if this is an audio param -> match to LoadAudio nodes
            if simple_key in ("audio", "audiofile", "audio_file", "voice"):
                if enabled_audio_nodes:
                    node_id, input_key, _ = enabled_audio_nodes[0]
                    enabled_audio_nodes.pop(0)
                    full_key = f"{node_id}:{input_key}"
                    resolved[original_key] = (full_key, value)
                    logger.info(f"✅ Resolved '{original_key}' -> '{full_key}' (LoadAudio node)")
                    continue
                # Fallback: try to find any node that takes audio input
                for node_id, node_def in workflow_template.items():
                    class_type = node_def.get("class_type", "").lower()
                    inputs = node_def.get("inputs", {})
                    for input_key in inputs:
                        if "audio" in input_key.lower():
                            full_key = f"{node_id}:{input_key}"
                            resolved[original_key] = (full_key, value)
                            logger.info(f"✅ Resolved '{original_key}' -> '{full_key}' (audio input)")
                            break
                    if original_key in resolved:
                        break
            
            if original_key in resolved:
                continue
            
            # General matching by node title containing the key
            for node_id, node_def in workflow_template.items():
                if original_key in resolved:
                    break
                class_type = node_def.get("class_type", "").lower()
                meta_title = (node_def.get("_meta", {}) or {}).get("title", "").lower()
                inputs = node_def.get("inputs", {})
                
                # Match by node title containing the key
                if simple_key in meta_title:
                    for input_key in inputs:
                        full_key = f"{node_id}:{input_key}"
                        resolved[original_key] = (full_key, value)
                        logger.info(f"✅ Resolved '{original_key}' -> '{full_key}' (title='{meta_title}')")
                        break
                    continue
                
                # Match by class_type containing the key
                if simple_key in class_type:
                    for input_key in inputs:
                        full_key = f"{node_id}:{input_key}"
                        resolved[original_key] = (full_key, value)
                        logger.info(f"✅ Resolved '{original_key}' -> '{full_key}' (class='{class_type}')")
                        break
                    continue
                
                # Match by input field name
                for input_key in inputs:
                    if simple_key in input_key.lower():
                        full_key = f"{node_id}:{input_key}"
                        resolved[original_key] = (full_key, value)
                        logger.debug(f"Resolved '{original_key}' -> '{full_key}' (input='{input_key}')")
                        break
        
        # Build final result dict
        result = {}
        for original_key in simple_inputs:
            if original_key in resolved:
                full_key, value = resolved[original_key]
                result[full_key] = value
            else:
                logger.warning(f"⚠️ Could not resolve '{original_key}', passing as raw key")
                result[original_key] = simple_inputs[original_key]
        
        if result:
            return result
        
        # Strategy 1: Use enabledParams from api_config (best case)
        enabled_params = api_config.get("enabledParams", {})
        if enabled_params:
            # Map customLabels to find the right node
            custom_labels = api_config.get("customLabels", {})
            
            # enabledParams is like {"12:image": true, "21:audio": true, ...}
            # custom_labels is like {"12:image": "上传图片", ...}
            
            # Build a reverse mapping from custom label to node_key
            label_to_key = {}
            for node_key, label in custom_labels.items():
                label_to_key[label] = node_key
            
            resolved = {}
            for simple_key, value in simple_inputs.items():
                # Try matching by label first (if customLabels has meaningful names)
                # Fall back to scanning all enabled params
                found = False
                for node_key in enabled_params:
                    field_name = node_key.split(":", 1)[-1] if ":" in node_key else ""
                    # Check if the simple key matches the node's title or class type
                    node_id = node_key.split(":")[0]
                    node_def = workflow_template.get(node_id, {})
                    class_type = node_def.get("class_type", "").lower()
                    node_title = node_def.get("_meta", {}).get("title", "").lower()
                    
                    # Match simple_key to class_type or node title
                    # e.g., "audio" -> matches "LoadAudio", "SaveAudio", "audio" in title
                    if simple_key.lower() in class_type or simple_key.lower() in node_title:
                        resolved[node_key] = value
                        found = True
                        logger.debug(f"Resolved '{simple_key}' -> '{node_key}' (class={class_type})")
                        break
                    
                    # Also match by field name in inputs
                    node_inputs = node_def.get("inputs", {})
                    for input_key in node_inputs:
                        if simple_key.lower() in input_key.lower():
                            full_key = f"{node_id}:{input_key}"
                            resolved[full_key] = value
                            found = True
                            logger.debug(f"Resolved '{simple_key}' -> '{full_key}' (input={input_key})")
                            break
                    if found:
                        break
                
                if not found:
                    logger.warning(f"Could not resolve '{simple_key}' for workflow '{workflow_id}', passing as-is")
                    resolved[simple_key] = value
            
            return resolved
        
        # Strategy 2: Scan workflow_template for Primitive nodes with matching titles
        # Primitive nodes have titles like "$name.value!" or "$prompt.value!"
        # We parse the title to get the parameter name
        resolved = {}
        for node_id, node_def in workflow_template.items():
            class_type = node_def.get("class_type", "")
            meta_title = node_def.get("_meta", {}).get("title", "")
            
            # Check Primitive nodes (they have titles like "$name.value!")
            if "Primitive" in class_type and "$" in meta_title:
                # Extract the param name from title e.g., "$videoimage.value!" -> "videoimage"
                import re
                match = re.match(r'\$(\w+)', meta_title)
                if match:
                    param_name = match.group(1).lower()
                    for simple_key, value in simple_inputs.items():
                        if simple_key.lower() == param_name:
                            # Find the input field name (usually "value", "text", etc.)
                            input_fields = node_def.get("inputs", {})
                            for input_key in input_fields:
                                full_key = f"{node_id}:{input_key}"
                                resolved[full_key] = value
                                logger.debug(f"Resolved '{simple_key}' -> '{full_key}' from Primitive title '{meta_title}'")
                                break
                            break
        
        # If no resolution worked, return as-is and let the remote API handle it
        if not resolved:
            logger.warning(
                f"Could not resolve any inputs for '{workflow_id}' using workflow_template. "
                f"Falling back to raw input_values. Template has {len(workflow_template)} nodes."
            )
            return simple_inputs
        
        return resolved
    
    async def upload_file(self, file_path: str, overwrite: bool = True) -> Optional[str]:
        """
        Upload a file to the remote ComfyUI's input directory.
        
        Args:
            file_path: Local path to the file
            overwrite: Whether to overwrite if file exists
            
        Returns:
            The filename (name) that can be used in input_values, or None on failure
        """
        if not os.path.exists(file_path):
            logger.error(f"File does not exist: {file_path}")
            return None
        
        try:
            client = await self._get_client()
            
            # Determine the form field name based on file extension
            ext = Path(file_path).suffix.lower()
            if ext in ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif'):
                field_name = 'image'
            elif ext in ('.mp3', '.wav', '.ogg', '.m4a', '.flac', '.aac'):
                field_name = 'audio'
            elif ext in ('.mp4', '.avi', '.mov', '.webm'):
                field_name = 'video'
            else:
                field_name = 'file'
            
            with open(file_path, 'rb') as f:
                files = {field_name: (Path(file_path).name, f, 'application/octet-stream')}
                params = {'overwrite': 'true'} if overwrite else {}
                
                resp = await client.post(
                    f"{self.base_url}/api/comfy/upload/file",
                    files=files,
                    params=params,
                    timeout=120.0,
                )
                data = resp.json()
                
                if data.get("name"):
                    logger.info(f"✅ Uploaded '{data['name']}' to remote ComfyUI")
                    return data["name"]
                else:
                    logger.error(f"Upload failed, response: {data}")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to upload file to remote ComfyUI: {e}")
            return None
    
    async def run_workflow(
        self,
        workflow_id: str,
        input_values: dict[str, Any],
        poll_interval: float = 2.0,
        max_poll_time: float = 600.0,
        auto_resolve: bool = True,
    ) -> list[dict]:
        """
        Submit a workflow task and wait for results.
        
        Args:
            workflow_id: The saved workflow ID/name on the remote ComfyUI
            input_values: Dict of node inputs
                Can use simple names (e.g., {"videoimage": "file.png", "audio": "file.mp3"})
                if auto_resolve=True. Otherwise use zealman format (e.g., {"12:image": "file.png"}).
            poll_interval: Seconds between poll attempts
            max_poll_time: Maximum total wait time
            auto_resolve: If True, try to resolve simple param names to node IDs
            
        Returns:
            List of result dicts with 'type' and 'url' keys
            
        Raises:
            RemoteComfyServiceError: If workflow fails or times out
        """
        client = await self._get_client()
        
        # Auto-resolve simple param names to node IDs
        actual_inputs = input_values
        if auto_resolve:
            # Check if inputs are already in zealman format (contain ":")
            has_zealman_keys = any(":" in k for k in input_values)
            if not has_zealman_keys:
                logger.info(f"🔄 Auto-resolving param names for workflow '{workflow_id}'...")
                try:
                    actual_inputs = await self.resolve_workflow_inputs(workflow_id, input_values)
                    logger.info(f"✅ Resolved inputs: {actual_inputs}")
                except Exception as e:
                    logger.warning(f"Auto-resolve failed: {e}, using raw inputs")
                    actual_inputs = input_values
            else:
                logger.debug("Inputs already in zealman format, skipping auto-resolve")
        
        # Step 1: Submit the workflow
        logger.info(f"🚀 Submitting workflow '{workflow_id}' to remote ComfyUI")
        
        try:
            resp = await client.post(
                f"{self.base_url}/api/workflow/generate",
                json={
                    "workflow_id": workflow_id,
                    "input_values": actual_inputs,
                },
                timeout=30.0,
            )
            data = resp.json()
        except Exception as e:
            raise RemoteComfyServiceError(f"Failed to submit workflow: {e}")
        
        if not data.get("success"):
            error_msg = data.get("error", "Unknown error")
            raise RemoteComfyServiceError(f"Workflow submission failed: {error_msg}")
        
        prompt_id = data.get("prompt_id")
        if not prompt_id:
            raise RemoteComfyServiceError("No prompt_id returned from workflow submission")
        
        logger.info(f"✅ Workflow submitted, prompt_id={prompt_id}")
        
        # Get the task_id from ComfyUI history to check for errors
        # Also check workflow result
        # Step 2: Poll for results
        start_time = time.time()
        last_log_time = 0
        
        while True:
            elapsed = time.time() - start_time
            if elapsed > max_poll_time:
                raise RemoteComfyServiceError(
                    f"Workflow timed out after {max_poll_time}s (prompt_id={prompt_id})"
                )
            
            # Log progress every 30 seconds
            if elapsed - last_log_time > 30:
                logger.info(f"⏳ Waiting for workflow... ({elapsed:.0f}s elapsed)")
                last_log_time = elapsed
            
            try:
                resp = await client.get(
                    f"{self.base_url}/api/workflow/result",
                    params={"prompt_id": prompt_id},
                    timeout=15.0,
                )
                result_data = resp.json()
            except Exception as e:
                logger.warning(f"Poll failed (retrying): {e}")
                await asyncio.sleep(poll_interval)
                continue
            
            if not result_data.get("success"):
                logger.warning(f"Poll returned error (retrying): {result_data}")
                await asyncio.sleep(poll_interval)
                continue
            
            if result_data.get("pending", True):
                await asyncio.sleep(poll_interval)
                continue
            
            # Task completed!
            results = result_data.get("results", [])
            logger.info(f"✅ Workflow completed! Got {len(results)} results (elapsed: {elapsed:.0f}s)")
            
            # Prepend base URL to relative paths
            for r in results:
                url = r.get("url", "")
                if url and url.startswith("/"):
                    r["url"] = f"{self.base_url}{url}"
            
            return results
    
    async def download_result(
        self,
        result_url: str,
        output_path: str,
    ) -> str:
        """
        Download a result file from the remote ComfyUI to local path.
        
        Args:
            result_url: Full URL to the remote file
            output_path: Local file path to save to
            
        Returns:
            The local output_path
        """
        try:
            client = await self._get_client()
            resp = await client.get(result_url, timeout=300.0)
            resp.raise_for_status()
            
            # Ensure output directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'wb') as f:
                f.write(resp.content)
            
            logger.info(f"✅ Downloaded result to {output_path} ({len(resp.content)} bytes)")
            return output_path
            
        except Exception as e:
            raise RemoteComfyServiceError(f"Failed to download result: {e}")
    
    async def run_digital_human_workflow(
        self,
        image_workflow_id: str,
        video_workflow_id: str,
        character_image_path: str,
        audio_path: str,
        goods_image_path: Optional[str] = None,
        goods_type: str = "",
        output_dir: str = "",
    ) -> tuple[str, str]:
        """
        Run the two-step digital human pipeline on remote ComfyUI.
        
        Step 1: Generate composite image (character + product)
        Step 2: Generate talking head video (image + audio)
        
        Args:
            image_workflow_id: Workflow name for image compositing (empty to skip)
            video_workflow_id: Workflow name for video generation
            character_image_path: Local path to character image
            audio_path: Local path to audio file
            goods_image_path: Optional local path to product image
            goods_type: Product type/name text
            output_dir: Local directory to save results
            
        Returns:
            Tuple of (generated_image_local_path, final_video_local_path)
        """
        task_dir = output_dir or os.path.join("output", "remote_comfy", str(int(time.time())))
        Path(task_dir).mkdir(parents=True, exist_ok=True)
        
        # Step 1: Upload files to remote ComfyUI
        logger.info("📤 Uploading character image...")
        char_filename = await self.upload_file(character_image_path)
        if not char_filename:
            raise RemoteComfyServiceError("Failed to upload character image")
        
        goods_filename = None
        if goods_image_path and os.path.exists(goods_image_path):
            logger.info("📤 Uploading goods image...")
            goods_filename = await self.upload_file(goods_image_path)
        
        logger.info("📤 Uploading audio file...")
        audio_filename = await self.upload_file(audio_path)
        if not audio_filename:
            raise RemoteComfyServiceError("Failed to upload audio file")
        
        # Step 2: Run image compositing workflow (if goods image exists)
        generated_image_local = None
        video_image_filename = char_filename  # default: use character image
        
        # If we have both goods and image_workflow, run image compositing
        if goods_filename and image_workflow_id:
            logger.info("🖼️ Running image compositing workflow...")
            image_inputs = {
                "firstimage": char_filename,
                "secondimage": goods_filename,
            }
            if goods_type:
                image_inputs["goodstype"] = goods_type
            
            image_results = await self.run_workflow(image_workflow_id, image_inputs)
            
            # Find image result
            image_url = None
            for r in image_results:
                if r.get("type") in ("image",):
                    image_url = r.get("url")
                    break
            
            if not image_url:
                # Try first result
                image_url = image_results[0].get("url") if image_results else None
            
            if image_url:
                generated_image_local = os.path.join(task_dir, "generated_image.png")
                await self.download_result(image_url, generated_image_local)
                # Use the generated image for video step
                logger.info("📤 Uploading generated image for video step...")
                video_image_filename = await self.upload_file(generated_image_local)
                if not video_image_filename:
                    video_image_filename = char_filename
            else:
                logger.warning("Image workflow returned no image, using character image for video")
        
        # Step 3: Run video generation workflow
        logger.info("🎬 Running video generation workflow...")
        video_inputs = {
            "videoimage": video_image_filename,
            "audio": audio_filename,
        }
        
        video_results = await self.run_workflow(video_workflow_id, video_inputs)
        
        # Find video result
        video_url = None
        for r in video_results:
            if r.get("type") in ("video",):
                video_url = r.get("url")
                break
        
        if not video_url:
            video_url = video_results[0].get("url") if video_results else None
        
        if not video_url:
            raise RemoteComfyServiceError("Video workflow did not return any video")
        
        final_video_local = os.path.join(task_dir, "final.mp4")
        await self.download_result(video_url, final_video_local)
        
        return generated_image_local or character_image_path, final_video_local