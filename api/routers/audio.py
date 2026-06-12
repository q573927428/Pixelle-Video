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
Audio endpoints - ASR (Automatic Speech Recognition) and other audio processing
"""

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel

from pixelle_video.services.dashscope_asr import get_asr_service

router = APIRouter(prefix="/audio", tags=["Basic Services"])


class AsrRequest(BaseModel):
    audio_path: str


class AsrResponse(BaseModel):
    text: str


@router.post("/asr", response_model=AsrResponse)
async def audio_asr(request: AsrRequest):
    """
    Automatic Speech Recognition (ASR) endpoint
    
    Transcribe audio file to text using DashScope ASR service.
    
    - **audio_path**: Path to the audio file to transcribe
    
    Returns the transcribed text.
    """
    try:
        logger.info(f"🎙️ ASR request: {request.audio_path}")
        
        asr_service = get_asr_service()
        text = asr_service.transcribe(request.audio_path)
        
        logger.info(f"✅ ASR completed: {text[:80]}...")
        return AsrResponse(text=text)
        
    except ImportError as e:
        logger.error(f"ASR service not available: {e}")
        raise HTTPException(status_code=501, detail=f"ASR 服务不可用: {e}")
    except FileNotFoundError as e:
        logger.error(f"Audio file not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"ASR error: {e}")
        raise HTTPException(status_code=500, detail=str(e))