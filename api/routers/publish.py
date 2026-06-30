"""
Publishing API Router

Endpoints for video publishing to Chinese short-video platforms.
"""

from pathlib import Path
from urllib.parse import urlparse
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends
from loguru import logger

from api.schemas.publish import (
    PublishStartRequest,
    PublishStartResponse,
    PublishStatusResponse,
    CookieSaveRequest,
    CookieSaveResponse,
    AccountListResponse,
    AccountInfo,
    PublishCancelResponse,
    PublishLoginRequest,
    PublishLoginResponse,
)
from api.auth.dependencies import get_current_user, require_user
from api.auth.schemas import UserInfo
from pixelle_video.services.publisher.session_manager import session_manager
from pixelle_video.services.publisher.cookie_manager import cookie_manager
from pixelle_video.services.publisher.publisher_base import BasePublisher, PublishParams

router = APIRouter(prefix="/publish", tags=["Publishing"])


SUPPORTED_PLATFORMS = {
    "douyin": "抖音",
    "kuaishou": "快手",
    "xiaohongshu": "小红书",
    "shipinhao": "视频号",
}


@router.post("/login", response_model=PublishLoginResponse)
async def start_login(
    request: PublishLoginRequest,
    user: UserInfo = Depends(require_user),
):
    """独立登录 - 仅用于扫码登录绑定平台账号，不触发发布流程

    1. 创建登录会话
    2. 后台启动浏览器 -> 访问平台创作者页面 -> 检测登录态
    3. 若未登录则获取二维码推送到前端
    4. 等待用户扫码完成 -> 保存 Cookie 绑定账号
    5. WebSocket 实时推送登录进度
    """
    # 验证平台
    if request.platform not in SUPPORTED_PLATFORMS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的平台: {request.platform}。支持: {', '.join(SUPPORTED_PLATFORMS.keys())}",
        )

    # 创建登录会话（使用与发布相同的 session manager）
    session_id = await session_manager.create(
        user_id=user.id,
        platform=request.platform,
    )

    # 后台执行独立登录流程
    from pixelle_video.services.publisher.browser_pool import browser_pool
    import asyncio

    async def _run_login():
        context = None
        try:
            # 确保浏览器池已启动
            if not browser_pool.is_running:
                await browser_pool.start()

            # 获取浏览器上下文
            context = await browser_pool.get_context()
            if not context:
                await session_manager.update_status(
                    session_id,
                    status="failed",
                    error="无法获取浏览器实例",
                    message="浏览器池资源不足",
                )
                return

            # 创建发布器实例（仅用于登录流程）
            publisher = await _create_publisher(request.platform, session_id, context)
            if not publisher:
                await session_manager.update_status(
                    session_id,
                    status="failed",
                    error=f"不支持的平台: {request.platform}",
                    message=f"发布器未实现: {request.platform}",
                )
                return

            # 仅执行登录流程（不使用 publisher.execute 的完整发布流程）
            # 1. 访问创作者页面检测登录态
            await session_manager.update_status(
                session_id,
                status="running",
                current_step="logging_in",
                progress=10,
                message=f"正在登录{SUPPORTED_PLATFORMS[request.platform]}...",
            )

            # 创建新页面
            page = await context.new_page()
            publisher.page = page

            # 2. 先尝试加载已保存 Cookie
            cookies = await cookie_manager.load(user.id, publisher.PLATFORM_NAME)
            if cookies:
                await context.add_cookies(cookies)
                logger.info(f"✅ Cookies added for {publisher.PLATFORM_NAME}")

            # 3. 访问创作者页面
            await page.goto(publisher.CREATOR_URL, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)

            # 4. 检测登录态
            logged_in = await publisher._is_logged_in()

            if logged_in:
                # 已登录，直接保存并返回成功
                await publisher._save_login_cookies()
                await session_manager.update_status(
                    session_id,
                    status="success",
                    current_step="complete",
                    progress=100,
                    message=f"✅ {SUPPORTED_PLATFORMS[request.platform]}账号已登录",
                )
                await session_manager.broadcast(session_id, {
                    "type": "login_success",
                    "message": f"{SUPPORTED_PLATFORMS[request.platform]}账号已登录",
                })
                return

            # 5. 未登录 -> 执行扫码登录流程
            await session_manager.update_status(
                session_id,
                status="running",
                current_step="need_login",
                progress=20,
                message=f"请使用{SUPPORTED_PLATFORMS[request.platform]}App扫码登录",
            )
            await session_manager.broadcast(session_id, {
                "type": "qrcode_waiting",
                "message": f"正在获取{SUPPORTED_PLATFORMS[request.platform]}登录二维码...",
            })

            # 调用发布器的 _need_login 方法处理扫码登录
            login_success = await publisher._need_login()

            if login_success:
                await session_manager.update_status(
                    session_id,
                    status="success",
                    current_step="complete",
                    progress=100,
                    message=f"✅ {SUPPORTED_PLATFORMS[request.platform]}账号绑定成功",
                )
            else:
                await session_manager.update_status(
                    session_id,
                    status="failed",
                    current_step="need_login",
                    error="用户未完成扫码登录",
                    message="登录超时或用户取消",
                )
                await session_manager.broadcast(session_id, {
                    "type": "error",
                    "message": "登录超时或已取消",
                })

        except Exception as e:
            logger.error(f"Login task failed: {e}")
            session = await session_manager.get(session_id)
            if session and session.status not in ("failed", "success"):
                await session_manager.update_status(
                    session_id,
                    status="failed",
                    error=str(e),
                    message=f"登录异常: {str(e)}",
                )
                await session_manager.broadcast(session_id, {
                    "type": "error",
                    "message": f"登录失败: {str(e)}",
                })
        finally:
            # 释放浏览器上下文
            try:
                if context:
                    await browser_pool.release_context(context)
            except Exception:
                pass

    # 后台执行登录任务
    asyncio.create_task(_run_login())

    return PublishLoginResponse(
        session_id=session_id,
        status="pending",
        message=f"正在准备{SUPPORTED_PLATFORMS[request.platform]}登录...",
    )


@router.post("/start", response_model=PublishStartResponse)
async def start_publish(
    request: PublishStartRequest,
    user: UserInfo = Depends(require_user),
):
    """启动视频发布任务

    创建发布会话并在后台启动浏览器自动化发布流程。

    - **platform**: 目标平台 (douyin/kuaishou/xiaohongshu/shipinhao)
    - **video_path**: 视频文件路径
    - **title**: 视频标题
    - **text**: 文案内容
    - **topics**: 话题标签列表
    - **portrait_cover**: 竖屏封面 (可选 base64)
    - **landscape_cover**: 横屏封面 (可选 base64)
    """
    # 验证平台
    if request.platform not in SUPPORTED_PLATFORMS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的平台: {request.platform}。支持: {', '.join(SUPPORTED_PLATFORMS.keys())}",
        )

    # 创建会话
    session_id = await session_manager.create(
        user_id=user.id,
        platform=request.platform,
    )

    # 将 video_path 解析为本地文件系统路径
    # 前端可能传递 HTTP URL (/api/files/... 或 http://localhost:8000/api/files/...)
    # Playwright 的 set_input_files() 只接受本地文件路径，不支持 HTTP URL
    resolved_video_path = _resolve_video_path(request.video_path)
    if not resolved_video_path:
        raise HTTPException(
            status_code=400,
            detail=f"视频文件不存在或无法访问: {request.video_path}",
        )

    # 异步启动发布任务
    params = PublishParams(
        video_path=str(resolved_video_path),
        title=request.title,
        text=request.text,
        topics=request.topics,
        portrait_cover=request.portrait_cover,
        landscape_cover=request.landscape_cover,
    )

    # 导入并异步执行发布器
    from pixelle_video.services.publisher.browser_pool import browser_pool
    import asyncio

    async def _run_publish():
        try:
            # 确保浏览器池已启动
            if not browser_pool.is_running:
                await browser_pool.start()

            # 获取浏览器上下文
            context = await browser_pool.get_context()
            if not context:
                await session_manager.update_status(
                    session_id,
                    status="failed",
                    error="无法获取浏览器实例",
                    message="浏览器池资源不足",
                )
                return

            # 创建发布器实例（根据平台选择）
            publisher = await _create_publisher(request.platform, session_id, context)
            if not publisher:
                await session_manager.update_status(
                    session_id,
                    status="failed",
                    error=f"不支持的平台: {request.platform}",
                    message=f"发布器未实现: {request.platform}",
                )
                return

            # 执行发布（publisher.execute 内部已处理 _on_error 回调）
            await publisher.execute(params)

        except Exception as e:
            # 只有在 publisher.execute 没有处理错误时才需要处理
            session = await session_manager.get(session_id)
            if session and session.status != "failed":
                logger.error(f"Publish task failed: {e}")
                await session_manager.update_status(
                    session_id,
                    status="failed",
                    error=str(e),
                    message=f"发布任务异常: {str(e)}",
                )
        finally:
            # 释放浏览器上下文
            try:
                if context:
                    await browser_pool.release_context(context)
            except Exception:
                pass

    # 后台执行发布任务
    asyncio.create_task(_run_publish())

    return PublishStartResponse(
        session_id=session_id,
        status="pending",
        message=f"发布会话已创建，正在发布到{SUPPORTED_PLATFORMS[request.platform]}",
    )


@router.get("/status/{session_id}", response_model=PublishStatusResponse)
async def get_publish_status(
    session_id: str,
    user: UserInfo = Depends(require_user),
):
    """查询发布会话状态

    返回当前发布进度、步骤和状态信息。
    """
    session = await session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="发布会话不存在")

    if session.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="无权查看此发布会话")

    return PublishStatusResponse(
        session_id=session.session_id,
        status=session.status,
        current_step=session.current_step,
        progress=session.progress,
        message=session.message,
        platform_url=session.platform_url,
        error=session.error,
        pending_qrcode=session.pending_qrcode,
    )


@router.websocket("/ws/{session_id}")
async def publish_websocket(
    websocket: WebSocket,
    session_id: str,
):
    """WebSocket 实时发布会话状态

    建立连接后立即推送当前会话状态，
    后续自动推送所有状态变更事件。
    """
    await websocket.accept()

    # 验证会话存在
    session = await session_manager.get(session_id)
    if not session:
        await websocket.send_json({
            "type": "error",
            "message": "发布会话不存在",
        })
        await websocket.close()
        return

    # 注册 WebSocket 连接
    await session_manager.register_ws(session_id, websocket)

    # 发送当前状态
    await websocket.send_json({
        "type": "progress",
        "step": session.current_step,
        "progress": session.progress,
        "message": session.message,
        "platform_url": session.platform_url,
    })

    # 如果有缓存的二维码，立即推送给前端
    if session.pending_qrcode:
        await websocket.send_json({
            "type": "qrcode",
            "platform": session.platform,
            "image": session.pending_qrcode,
            "message": f"请使用{session.platform}App扫码登录",
        })
        logger.info(f"📤 Pushed pending QR code for session {session_id}")

    try:
        # 保持连接，等待消息
        while True:
            data = await websocket.receive_text()
            # 可以处理客户端发来的消息（如取消发布）
            if data == "cancel":
                await session_manager.update_status(
                    session_id,
                    status="failed",
                    message="用户取消了发布",
                )
                await session_manager.broadcast(session_id, {
                    "type": "cancelled",
                    "message": "用户取消了发布",
                })
                break
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.warning(f"WebSocket error for session {session_id}: {e}")
    finally:
        await session_manager.unregister_ws(session_id, websocket)


@router.post("/cookie", response_model=CookieSaveResponse)
async def save_cookie(
    request: CookieSaveRequest,
    user: UserInfo = Depends(require_user),
):
    """保存平台登录 Cookie

    将 Playwright Cookie 加密存储到数据库，
    下次发布时无需重新扫码登录。

    - **platform**: 平台名称
    - **cookies**: Playwright Cookie 列表
    - **account_name**: 平台显示的用户名
    - **expires_at**: Cookie 过期时间 (ISO 8601)
    """
    import dateutil.parser

    expires_ts = None
    if request.expires_at:
        try:
            expires_dt = dateutil.parser.parse(request.expires_at)
            expires_ts = expires_dt.timestamp()
        except Exception:
            raise HTTPException(status_code=400, detail="无效的过期时间格式")

    success = await cookie_manager.save(
        user_id=user.id,
        platform=request.platform,
        cookies=request.cookies,
        account_name=request.account_name,
        expires_at=expires_ts,
    )

    if not success:
        raise HTTPException(status_code=500, detail="Cookie 保存失败，请稍后重试")

    return CookieSaveResponse(
        message="Cookie 保存成功，下次发布无需重新登录",
    )


@router.get("/accounts", response_model=AccountListResponse)
async def list_accounts(
    user: UserInfo = Depends(require_user),
):
    """列出当前用户已绑定的平台账号"""
    accounts = await cookie_manager.list_accounts(user_id=user.id)

    return AccountListResponse(
        accounts=[
            AccountInfo(**acc) for acc in accounts
        ]
    )


@router.delete("/account/{account_id}", response_model=dict)
async def delete_account(
    account_id: int,
    user: UserInfo = Depends(require_user),
):
    """解绑已绑定的平台账号"""
    success = await cookie_manager.delete_account_by_id(account_id)

    if not success:
        raise HTTPException(status_code=500, detail="解绑失败，请稍后重试")

    return {
        "success": True,
        "message": "已成功解绑该平台账号",
    }


def _resolve_video_path(video_path: str) -> Path | None:
    """将 video_path 解析为本地文件系统路径

    前端可能传入多种格式：
    - 本地路径: temp/uploads/xxx/xxx.mp4
    - 完整 URL:  http://localhost:8000/api/files/temp/uploads/xxx/xxx.mp4
    - API 路径: /api/files/temp/uploads/xxx/xxx.mp4
    - 绝对路径: f:/qukuailian/ai/shipin/.../temp/uploads/xxx/xxx.mp4

    统一转换为本地绝对路径返回，若文件不存在则返回 None。
    """
    path_str = video_path.strip()

    # 1. 如果是 HTTP URL，提取 path 部分
    if path_str.startswith('http://') or path_str.startswith('https://'):
        parsed = urlparse(path_str)
        path_str = parsed.path  # e.g. /api/files/temp/uploads/xxx/xxx.mp4

    # 2. 去掉 /api/files/ 前缀（API 文件服务前缀）
    API_FILES_PREFIX = '/api/files/'
    if path_str.startswith(API_FILES_PREFIX):
        path_str = path_str[len(API_FILES_PREFIX):]

    # 3. 如果已经是绝对路径，直接使用
    abs_path = Path(path_str)
    if abs_path.is_absolute():
        if abs_path.exists() and abs_path.is_file():
            return abs_path.absolute()
        return None

    # 4. 相对路径，基于项目根目录拼接
    project_root = Path(__file__).resolve().parent.parent.parent  # api/routers/ -> api/ -> project_root
    full_path = project_root / path_str
    if full_path.exists() and full_path.is_file():
        return full_path.absolute()

    # 5. 尝试在 output/ 下查找（兼容旧数据）
    fallback_path = project_root / 'output' / path_str
    if fallback_path.exists() and fallback_path.is_file():
        return fallback_path.absolute()

    logger.warning(f"Video path not found: {video_path} (resolved: {full_path})")
    return None


async def _create_publisher(platform: str, session_id: str, context) -> BasePublisher:
    """根据平台名称创建对应的发布器实例

    Args:
        platform: 平台名称
        session_id: 会话 ID
        context: Playwright BrowserContext

    Returns:
        BasePublisher: 发布器实例
    """
    session = await session_manager.get(session_id)
    if not session:
        logger.error(f"Session {session_id} not found")
        return None

    # 根据平台创建发布器
    if platform == "douyin":
        from pixelle_video.services.publisher.douyin_publisher import DouyinPublisher
        return DouyinPublisher(session, context)
    elif platform == "kuaishou":
        from pixelle_video.services.publisher.kuaishou_publisher import KuaishouPublisher
        return KuaishouPublisher(session, context)
    elif platform == "xiaohongshu":
        from pixelle_video.services.publisher.xiaohongshu_publisher import XiaohongshuPublisher
        return XiaohongshuPublisher(session, context)
    elif platform == "shipinhao":
        from pixelle_video.services.publisher.shipinhao_publisher import ShipinhaoPublisher
        return ShipinhaoPublisher(session, context)
    else:
        logger.error(f"Unknown platform: {platform}")
        return None