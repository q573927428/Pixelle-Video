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
Content generation endpoints

Endpoints for generating narrations, image prompts, and titles.
"""

from fastapi import APIRouter, HTTPException
from loguru import logger

from api.dependencies import PixelleVideoDep
from api.schemas.content import (
    NarrationGenerateRequest,
    NarrationGenerateResponse,
    ImagePromptGenerateRequest,
    ImagePromptGenerateResponse,
    TitleGenerateRequest,
    TitleGenerateResponse,
    TopicsGenerateRequest,
    TopicsGenerateResponse,
    PublishPrepareRequest,
    PublishPrepareResponse,
)
from pixelle_video.utils.content_generators import (
    generate_narrations_from_topic,
    generate_image_prompts,
    generate_title,
)
router = APIRouter(prefix="/content", tags=["Content Generation"])


@router.post("/narration", response_model=NarrationGenerateResponse)
async def generate_narration(
    request: NarrationGenerateRequest,
    pixelle_video: PixelleVideoDep
):
    """
    Generate narrations from text
    
    Uses LLM to break down text into multiple narration segments.
    
    - **text**: Source text
    - **n_scenes**: Number of narrations to generate
    - **min_words**: Minimum words per narration
    - **max_words**: Maximum words per narration
    
    Returns list of narration strings.
    """
    try:
        logger.info(f"Generating {request.n_scenes} narrations from text")
        
        # Call narration generator utility function
        narrations = await generate_narrations_from_topic(
            llm_service=pixelle_video.llm,
            topic=request.text,
            n_scenes=request.n_scenes,
            min_words=request.min_words,
            max_words=request.max_words
        )
        
        return NarrationGenerateResponse(
            narrations=narrations
        )
        
    except Exception as e:
        logger.error(f"Narration generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/image-prompt", response_model=ImagePromptGenerateResponse)
async def generate_image_prompt(
    request: ImagePromptGenerateRequest,
    pixelle_video: PixelleVideoDep
):
    """
    Generate image prompts from narrations
    
    Uses LLM to create detailed image generation prompts.
    
    - **narrations**: List of narration texts
    - **min_words**: Minimum words per prompt
    - **max_words**: Maximum words per prompt
    
    Returns list of image prompts.
    """
    try:
        logger.info(f"Generating image prompts for {len(request.narrations)} narrations")
        
        # Call image prompt generator utility function
        image_prompts = await generate_image_prompts(
            llm_service=pixelle_video.llm,
            narrations=request.narrations,
            min_words=request.min_words,
            max_words=request.max_words
        )
        
        return ImagePromptGenerateResponse(
            image_prompts=image_prompts
        )
        
    except Exception as e:
        logger.error(f"Image prompt generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/title", response_model=TitleGenerateResponse)
async def generate_title_endpoint(
    request: TitleGenerateRequest,
    pixelle_video: PixelleVideoDep
):
    """
    Generate video title from text
    
    Uses LLM to create an engaging title.
    
    - **text**: Source text
    - **style**: Optional title style hint
    
    Returns generated title.
    """
    try:
        logger.info("Generating title from text")
        
        # Call title generator utility function
        title = await generate_title(
            llm_service=pixelle_video.llm,
            content=request.text,
            strategy="llm"
        )
        
        return TitleGenerateResponse(
            title=title
        )
        
    except Exception as e:
        logger.error(f"Title generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/topics", response_model=TopicsGenerateResponse)
async def generate_topics_endpoint(
    request: TopicsGenerateRequest,
    pixelle_video: PixelleVideoDep
):
    """
    Generate hashtags/topics from text
    
    Uses LLM to create relevant hashtags for video publishing.
    
    - **text**: Source text
    - **count**: Number of topics to generate
    
    Returns list of topic strings.
    """
    try:
        logger.info(f"Generating {request.count} topics from text")
        
        llm = pixelle_video.llm
        if not llm:
            raise HTTPException(status_code=500, detail="LLM service not available")
        
        prompt = f"""根据以下文案，生成{request.count}个适合作为短视频话题标签的词语。
要求：
1. 每个话题2-5个字
2. 不要带#号
3. 与文案内容相关
4. 每行一个话题

文案：
{request.text}

请直接输出话题词语，每行一个："""
        
        result = await llm.chat([{"role": "user", "content": prompt}])
        if isinstance(result, str):
            result_text = result
        elif isinstance(result, dict):
            result_text = result.get("content", "") or result.get("text", "") or str(result)
        else:
            result_text = str(result)
        
        topics = [
            t.strip().strip('#').strip()
            for t in result_text.split('\n')
            if t.strip() and not t.strip().startswith('```') and t.strip() not in ('', '，', '。')
        ]
        topics = topics[:request.count]
        
        if not topics:
            topics = ['AI技术', '数字人', '短视频']
        
        return TopicsGenerateResponse(
            topics=topics
        )
        
    except Exception as e:
        logger.error(f"Topics generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/publish-prepare", response_model=PublishPrepareResponse)
async def generate_publish_prepare(
    request: PublishPrepareRequest,
    pixelle_video: PixelleVideoDep
):
    """
    One-click generate title + topics for publishing
    
    Uses LLM to create an engaging title and relevant hashtags.
    
    - **text**: Source text
    
    Returns generated title and topics list.
    """
    try:
        logger.info("Generating publish prepare (title + topics)")
        
        llm = pixelle_video.llm
        if not llm:
            raise HTTPException(status_code=500, detail="LLM service not available")
        
        # 1. Generate title
        title = await generate_title(
            llm_service=pixelle_video.llm,
            content=request.text,
            strategy="llm"
        )
        
        if not title:
            title = "精彩视频"
        
        # 2. Generate topics
        prompt = f"""根据以下文案，生成5个适合作为短视频话题标签的词语。
要求：
1. 每个话题2-5个字
2. 不要带#号
3. 与文案内容相关
4. 每行一个话题

文案：
{request.text}

请直接输出话题词语，每行一个："""
        
        result = await llm.chat([{"role": "user", "content": prompt}])
        if isinstance(result, str):
            result_text = result
        elif isinstance(result, dict):
            result_text = result.get("content", "") or result.get("text", "") or str(result)
        else:
            result_text = str(result)
        
        topics = [
            t.strip().strip('#').strip()
            for t in result_text.split('\n')
            if t.strip() and not t.strip().startswith('```') and t.strip() not in ('', '，', '。')
        ]
        topics = topics[:5]
        if not topics:
            topics = ['AI技术', '数字人', '短视频']
        
        return PublishPrepareResponse(
            title=title,
            topics=topics
        )
        
    except Exception as e:
        logger.error(f"Publish prepare error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

