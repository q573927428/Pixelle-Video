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
2. 格式为"#话题"（#后面紧跟话题内容，右侧无空格）
3. 与文案内容相关
4. 每行一个话题

文案：
{request.text}

请直接输出话题标签，每行一个："""
        
        result = await llm(prompt, temperature=0.7, max_tokens=1024)
        if isinstance(result, str):
            result_text = result
        elif isinstance(result, dict):
            result_text = result.get("content", "") or result.get("text", "") or str(result)
        else:
            result_text = str(result)
        
        # 按行分割，每行再按逗号/空格分割，展平处理
        raw_topics = []
        for line in result_text.split('\n'):
            # 替换逗号为空格再分割
            for part in line.replace('，', ' ').replace(',', ' ').split():
                part = part.strip()
                if part and not part.startswith('```') and part not in ('', '，', '。'):
                    raw_topics.append(part)
        # 确保每个话题以#开头
        topics = [t if t.startswith('#') else f'#{t}' for t in raw_topics]
        topics = topics[:request.count]
        
        if not topics:
            topics = ['#AI技术', '#数字人', '#短视频']
        
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
        
        # 2. Generate topics (1-5 hashtags, format: "#话题 #话题" space-separated)
        prompt = f"""根据以下文案，生成话题标签（1-5个）。
要求：
1. 每个话题格式为"#话题"（#后面紧跟话题内容，右侧无空格）
2. 多个话题之间用空格隔开，只输出一行
3. 与文案内容相关
4. 不要输出序号或其他内容

文案：
{request.text}

请直接输出空格隔开的话题标签："""
        
        result = await llm(prompt, temperature=0.7, max_tokens=1024)
        if isinstance(result, str):
            result_text = result
        elif isinstance(result, dict):
            result_text = result.get("content", "") or result.get("text", "") or str(result)
        else:
            result_text = str(result)
        
        # Parse hashtags - replace commas with spaces, then split by whitespace
        clean_text = result_text.replace('\n', ' ').replace('，', ' ').replace(',', ' ')
        topics = [
            t.strip()
            for t in clean_text.split()
            if t.strip().startswith('#') and len(t.strip()) > 1
        ]
        topics = topics[:5]
        if not topics:
            topics = ['#AI技术', '#数字人', '#短视频']
        
        return PublishPrepareResponse(
            title=title,
            topics=topics
        )
        
    except Exception as e:
        logger.error(f"Publish prepare error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

