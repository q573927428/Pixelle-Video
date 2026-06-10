"""
VoxCPM TTS via HuggingFace Spaces API

Calls the openbmb/VoxCPM-Demo /generate endpoint on HuggingFace Spaces
using the gradio_client library.
"""

import os
import uuid
from pathlib import Path
from typing import Any, Optional

from loguru import logger

# Optional import - gradio_client may not be installed
try:
    from gradio_client import Client, handle_file
    HAS_GRADIO_CLIENT = True
except ImportError:
    HAS_GRADIO_CLIENT = False
    Client = None
    handle_file = None


class VoxCPMAPIService:
    """
    VoxCPM TTS via HuggingFace Spaces API

    Calls openbmb/VoxCPM-Demo on HuggingFace Spaces using its Gradio API.

    Usage:
        voxcpm = VoxCPMAPIService()
        audio_path = await voxcpm.generate(
            text="你好，世界！",
            output_path="output/test.mp3"
        )

    API Endpoint: /generate
    Parameters:
        - text_input (str): Text to synthesize
        - control_instruction (str): Control instruction (optional)
        - reference_wav_path_input (filepath | None): Reference audio for voice cloning
        - use_prompt_text (bool): Whether to use prompt text
        - prompt_text_input (str): Prompt text (optional)
        - cfg_value_input (float): CFG scale (1.0-5.0, default 2.0)
        - do_normalize (bool): Normalize audio
        - denoise (bool): Denoise audio
    Returns:
        Audio file path
    """
    
    SPACE_ID = "openbmb/VoxCPM-Demo"
    
    def __init__(self, hf_token: Optional[str] = None):
        """
        Initialize VoxCPM API client
        
        Args:
            hf_token: HuggingFace token (optional, for private spaces)
        """
        if not HAS_GRADIO_CLIENT:
            raise ImportError(
                "gradio_client is required for VoxCPM API. "
                "Install it with: pip install gradio-client"
            )
        
        self.hf_token = hf_token
        self._client: Optional[Any] = None
        logger.info(f"🔊 Initialized VoxCPM API client for {self.SPACE_ID}")
    
    def _get_client(self) -> Any:
        """Get or create the Gradio client (lazy initialization)"""
        if self._client is None:
            logger.debug(f"Creating Gradio client for {self.SPACE_ID}...")
            init_kwargs = {"src": self.SPACE_ID}
            if self.hf_token:
                init_kwargs["hf_token"] = self.hf_token
            self._client = Client(**init_kwargs)
            logger.debug("Gradio client created")
        return self._client
    
    async def generate(
        self,
        text: str,
        reference_audio: Optional[str] = None,
        control_instruction: str = "",
        use_prompt_text: bool = False,
        prompt_text: str = "",
        cfg: float = 2.0,
        do_normalize: bool = False,
        denoise: bool = False,
        output_path: Optional[str] = None,
    ) -> str:
        """
        Generate speech using VoxCPM API
        
        Args:
            text: Text to convert to speech
            reference_audio: Path to reference audio for voice cloning (optional)
            control_instruction: Control instruction (optional)
                支持的极致克隆模式指令，例如：
                - "克隆音色：沉稳、磁性" (Clone voice: deep, magnetic)
                - "自然说话风格，稍微活泼一点"
                - 留空则为普通模式
            use_prompt_text: Whether to use prompt text
            prompt_text: Prompt text for voice cloning reference
            cfg: CFG scale (1.0-5.0, default 2.0)
            do_normalize: Whether to normalize audio
            denoise: Whether to denoise audio
            output_path: Custom output path (auto-generated if None)
        
        Returns:
            Generated audio file path
        
        Raises:
            Exception: If generation fails
        """
        logger.info(f"🔊 VoxCPM generating speech for text: {text[:50]}...")
        
        # Generate output path if not provided
        if not output_path:
            unique_id = uuid.uuid4().hex
            output_path = f"output/{unique_id}.mp3"
            Path("output").mkdir(parents=True, exist_ok=True)
        
        try:
            # Prepare reference audio if provided (must be string path)
            ref_audio_input = None
            if reference_audio:
                ref_path = str(reference_audio)
                if os.path.exists(ref_path):
                    ref_audio_input = handle_file(ref_path)
                    logger.info(f"Using reference audio: {ref_path}")
                else:
                    logger.warning(f"Reference audio not found: {ref_path}")
            
            # Log cloning mode info
            if control_instruction:
                logger.info(f"  极致克隆模式: control_instruction='{control_instruction}'")
            if use_prompt_text and prompt_text:
                logger.info(f"  提示文本引导: prompt_text='{prompt_text}'")
            
            # Call the /generate endpoint
            logger.debug(f"Calling VoxCPM API with cfg={cfg}, normalize={do_normalize}, denoise={denoise}")
            client = self._get_client()
            
            result = client.predict(
                text_input=text,
                control_instruction=control_instruction,
                reference_wav_path_input=ref_audio_input,
                use_prompt_text=use_prompt_text,
                prompt_text_input=prompt_text,
                cfg_value_input=cfg,
                do_normalize=do_normalize,
                denoise=denoise,
                api_name="/generate"
            )
            
            # The result is a filepath (string) to the generated audio
            if not result:
                raise Exception("VoxCPM API returned empty result")
            
            audio_source_path = str(result)
            logger.debug(f"VoxCPM generated audio at: {audio_source_path}")
            
            # If output_path differs, copy the file
            if audio_source_path != output_path:
                import shutil
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                shutil.copy2(audio_source_path, output_path)
                logger.info(f"✅ Copied VoxCPM audio to: {output_path}")
            else:
                logger.info(f"✅ VoxCPM audio: {output_path}")
            
            return output_path
        
        except Exception as e:
            logger.error(f"❌ VoxCPM generation failed: {e}")
            raise
    
    def __repr__(self) -> str:
        return f"<VoxCPMAPIService space={self.SPACE_ID}>"