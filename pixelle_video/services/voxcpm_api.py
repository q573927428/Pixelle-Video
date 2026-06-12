"""
VoxCPM TTS via HuggingFace Spaces API

Calls the openbmb/VoxCPM-Demo /generate endpoint on HuggingFace Spaces
using the gradio_client library.

Supports long text splitting: automatically splits text into segments
to avoid trailing quality degradation in voice-cloned TTS.
"""

import os
import re
import uuid
import subprocess
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
    
    @staticmethod
    def _split_text(text: str, max_chars: int = 80) -> list[str]:
        """
        Split long text into segments at sentence boundaries.
        Each segment will be at most max_chars characters (except single sentences > max_chars).
        
        Args:
            text: Input text to split
            max_chars: Maximum characters per segment
        
        Returns:
            List of text segments
        """
        # Split by Chinese/English sentence-ending punctuation and mid-sentence delimiters
        sentences = re.split(r'(?<=[。！？.!?、，；])', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return [text]
        
        # Short text: no split needed
        if len(text) <= max_chars:
            return [text]
        
        segments = []
        current = ""
        
        for sentence in sentences:
            # If a single sentence exceeds max_chars, split it by comma as fallback
            if len(sentence) > max_chars:
                if current:
                    segments.append(current)
                    current = ""
                # Split long sentence by commas/delimiters
                parts = re.split(r'(?<=[，,、；])', sentence)
                for part in parts:
                    if not part.strip():
                        continue
                    if current and len(current) + len(part) > max_chars:
                        segments.append(current)
                        current = part
                    else:
                        current += part
            # Normal case: append sentence to current segment
            elif current and len(current) + len(sentence) > max_chars:
                segments.append(current)
                current = sentence
            else:
                current += sentence
        
        if current:
            segments.append(current)
        
        # Merge very short segments into previous one
        merged = []
        for seg in segments:
            if merged and (len(seg) < 10 or len(merged[-1]) < 25):
                merged[-1] += seg
            else:
                merged.append(seg)
        
        return merged if merged else [text]
    
    @staticmethod
    def _concat_audio_segments(segment_paths: list[str], output_path: str) -> str:
        """
        Concatenate multiple audio segments into one file using ffmpeg.
        
        Args:
            segment_paths: List of audio file paths to concatenate
            output_path: Final output file path
        
        Returns:
            Path to the concatenated audio file
        """
        if len(segment_paths) == 1:
            import shutil
            shutil.copy2(segment_paths[0], output_path)
            logger.info(f"✅ Single segment audio (no concat needed): {output_path}")
            return output_path
        
        # Create concat file list in cwd (not in output subdir) to avoid ffmpeg relative path issues
        concat_list_name = os.path.basename(output_path) + ".concat_list.txt"
        concat_list_path = os.path.join(os.getcwd(), concat_list_name)
        try:
            with open(concat_list_path, 'w', encoding='utf-8') as f:
                for seg_path in segment_paths:
                    normalized_path = os.path.abspath(seg_path).replace('\\', '/')
                    f.write(f"file '{normalized_path}'\n")
            
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_list_path,
                "-c", "copy",
                output_path
            ]
            
            logger.info(f"🎵 Concatenating {len(segment_paths)} audio segments...")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                logger.error(f"ffmpeg concat failed: {result.stderr}")
                raise RuntimeError(f"Audio concatenation failed: {result.stderr}")
            
            logger.info(f"✅ Concatenated audio: {output_path}")
            return output_path
        
        finally:
            if os.path.exists(concat_list_path):
                os.remove(concat_list_path)
    
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
        max_chars_per_segment: int = 80,
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
        
        # ====================================================================
        # Split long text into segments to avoid trailing quality degradation
        # ====================================================================
        segments = self._split_text(text, max_chars=max_chars_per_segment)
        
        if len(segments) > 1:
            logger.info(f"📝 Long text detected: {len(text)} chars, split into {len(segments)} segments")
            for i, seg in enumerate(segments):
                logger.info(f"  Segment {i+1}: {seg[:60]}... ({len(seg)} chars)")
        else:
            logger.info(f"📝 Text length: {len(text)} chars, single segment")
        
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
            
            # ====================================================================
            # Generate each segment separately, then concatenate
            # ====================================================================
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            segment_paths = []
            
            for idx, seg_text in enumerate(segments):
                if len(segments) > 1:
                    logger.info(f"🔊 Generating segment {idx+1}/{len(segments)}: '{seg_text[:50]}...'")
                else:
                    logger.info(f"🔊 VoxCPM generating speech for text: {text[:50]}...")
                
                # Generate segment to temp file
                seg_output = f"{output_path}.seg{idx}.mp3"
                
                client = self._get_client()
                
                # All segments use consistent cloning mode parameters for voice consistency
                result = client.predict(
                    text_input=seg_text,
                    control_instruction=control_instruction,
                    reference_wav_path_input=ref_audio_input,
                    use_prompt_text=use_prompt_text,
                    prompt_text_input=prompt_text,
                    cfg_value_input=cfg,
                    do_normalize=do_normalize,
                    denoise=denoise,
                    api_name="/generate"
                )
                
                if not result:
                    raise Exception(f"VoxCPM API returned empty result for segment {idx+1}")
                
                audio_source_path = str(result)
                logger.debug(f"  Segment {idx+1} audio at: {audio_source_path}")
                
                # Copy segment to local temp file
                import shutil
                shutil.copy2(audio_source_path, seg_output)
                segment_paths.append(seg_output)
            
            # ====================================================================
            # Concatenate all segments
            # ====================================================================
            if len(segment_paths) > 1:
                logger.info(f"🎵 Merging {len(segment_paths)} audio segments...")
                self._concat_audio_segments(segment_paths, output_path)
                
                # Cleanup temp segment files
                for seg_path in segment_paths:
                    if os.path.exists(seg_path):
                        os.remove(seg_path)
                
                logger.info(f"✅ Generated audio (merged from {len(segment_paths)} segments): {output_path}")
            else:
                # Single segment, just copy to output
                import shutil
                shutil.copy2(segment_paths[0], output_path)
                if os.path.exists(segment_paths[0]) and segment_paths[0] != output_path:
                    os.remove(segment_paths[0])
                logger.info(f"✅ Generated audio: {output_path}")
            
            return output_path
        
        except Exception as e:
            logger.error(f"❌ VoxCPM generation failed: {e}")
            raise
    
    def __repr__(self) -> str:
        return f"<VoxCPMAPIService space={self.SPACE_ID}>"