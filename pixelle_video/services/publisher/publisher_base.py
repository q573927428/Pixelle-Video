"""
发布器基类

所有短视频平台发布器的抽象基类。
定义统一的发布流程接口。
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Optional
from dataclasses import dataclass, field
from loguru import logger

from pixelle_video.services.publisher.session_manager import (
    PublishSession,
    session_manager,
)
from pixelle_video.services.publisher.cookie_manager import cookie_manager
from pixelle_video.services.publisher.stealth import create_stealth_context


@dataclass
class PublishParams:
    """发布参数"""
    video_path: str
    title: str = ""
    text: str = ""
    topics: list = field(default_factory=list)
    portrait_cover: str = ""  # base64 竖屏封面
    landscape_cover: str = ""  # base64 横屏封面

    @property
    def full_text(self) -> str:
        """获取完整文案（文案内容 + 话题标签）"""
        if self.topics:
            topics_str = " ".join(self.topics)
            if self.text:
                return f"{self.text}\n{topics_str}"
            return topics_str
        return self.text


class BasePublisher(ABC):
    """所有平台发布器的抽象基类

    子类必须覆盖以下常量和方法：
    - PLATFORM_NAME: 平台名称
    - CREATOR_URL: 创作者后台 URL
    - UPLOAD_URL: 上传页面 URL（可选）

    - _upload_video(): 上传视频
    - _fill_metadata(): 填写标题、文案、话题
    - _set_cover(): 设置封面
    - _click_publish(): 点击发布按钮
    """

    # 子类覆盖常量
    PLATFORM_NAME: str = ""
    CREATOR_URL: str = ""
    UPLOAD_URL: str = ""

    def __init__(self, session: PublishSession, browser_context=None):
        """初始化发布器

        Args:
            session: 发布会话对象
            browser_context: Playwright BrowserContext 实例
        """
        self.session = session
        self.context = browser_context
        self.page = None

    async def execute(self, params: PublishParams):
        """执行发布主流程

        Args:
            params: 发布参数
        """
        self.params = params

        try:
            await self._on_start()

            # 1. 确保登录态（登录失败时子类实现扫码，等待用户扫码完成后继续）
            await self._step("logging_in", 10, "登录检测中...")
            logged_in = await self._ensure_login()
            if not logged_in:
                # 子类 _need_login 会：
                # 1. 打开登录页面
                # 2. 截图二维码推送到前端
                # 3. 阻塞等待用户扫码完成
                # 4. 保存 Cookie
                # 5. 返回 True/False
                logged_in = await self._need_login()
                if not logged_in:
                    await self._on_error("用户未完成扫码登录")
                    return

            # 2. 打开发布页面
            await self._step("launching", 15, "正在打开发布页面...")
            await self._open_upload_page()

            # 3. 上传视频
            await self._step("uploading", 25, "视频上传中 (25%)...")
            await self._upload_video(params.video_path)

            # 4. 填写元数据
            await self._step("filling", 55, "正在填写信息...")
            await self._fill_metadata(params.title, params.text, params.topics)

            # 5. 设置封面
            await self._step("cover", 75, "正在设置封面...")
            await self._set_cover(params.portrait_cover, params.landscape_cover)

            # 6. 点击发布
            await self._step("publishing", 90, "正在发布...")
            await self._click_publish()

            # 7. 完成
            await self._on_success()

        except Exception as e:
            await self._on_error(str(e))
            raise
        finally:
            # 释放浏览器上下文
            try:
                from pixelle_video.services.publisher.browser_pool import browser_pool
                # 注意：context 的释放由调用方处理
            except Exception:
                pass

    async def _ensure_login(self) -> bool:
        """确保登录态有效

        尝试从数据库加载已保存的 Cookie 并设置到浏览器上下文。
        如果 Cookie 有效（能访问创作者页面），直接返回 True。
        否则返回 False，表示需要重新扫码登录。

        Returns:
            bool: 是否已登录
        """
        if not self.context:
            logger.error("Browser context not available")
            return False

        cookies_loaded = False
        try:
            # 1. 加载已保存的 Cookie
            cookies = await cookie_manager.load(self.session.user_id, self.PLATFORM_NAME)
            if cookies:
                cookies_loaded = True
                await self.context.add_cookies(cookies)
                logger.info(f"✅ Cookies added for {self.PLATFORM_NAME}")

            # 2. 访问创作者页面检查登录态
            page = await self.context.new_page()
            self.page = page
            await page.goto(self.CREATOR_URL, wait_until="domcontentloaded", timeout=30000)

            # 等待页面加载，检测是否已登录
            logged_in = await self._is_logged_in()

            if logged_in:
                logger.info(f"✅ User {self.session.user_id} is logged in to {self.PLATFORM_NAME}")
                return True
            else:
                logger.info(f"🔑 User {self.session.user_id} needs login to {self.PLATFORM_NAME}")
                # Cookie 已加载但登录失效 → 标记为过期
                if cookies_loaded:
                    await cookie_manager.mark_expired(self.session.user_id, self.PLATFORM_NAME)
                    logger.info(f"⏳ Cookie marked expired for user {self.session.user_id} / {self.PLATFORM_NAME}")
                return False

        except Exception as e:
            logger.error(f"Login check failed: {e}")
            return False

    async def _is_logged_in(self) -> bool:
        """检测当前页面是否已登录

        子类可覆盖此方法实现各平台特定的登录检测逻辑。

        Returns:
            bool: 是否已登录
        """
        if not self.page:
            return False
        try:
            # 默认检测：检查 URL 是否包含登录重定向标识
            current_url = self.page.url
            login_indicators = ["login", "passport", "signin", "oauth", "m.weixin"]
            for indicator in login_indicators:
                if indicator in current_url.lower():
                    return False
            return True
        except Exception:
            return False

    async def _need_login(self) -> bool:
        """处理需要登录的情况

        子类应覆盖此方法实现各平台特有的登录流程：
        1. 跳转到登录页面
        2. 获取二维码截图
        3. 通过 WebSocket 推送到前端
        4. 等待扫码完成
        5. 保存 Cookie 并返回 True

        Returns:
            bool: 是否成功登录
        """
        await self._step("need_login", 10, f"请使用{self.PLATFORM_NAME}App扫码登录")

        # 子类应实现具体的登录流程
        logger.warning(
            f"Login flow not implemented for {self.PLATFORM_NAME}. "
            "Override _need_login() in the publisher subclass."
        )
        return False

    async def _open_upload_page(self):
        """打开发布/上传页面"""
        if not self.page:
            return

        target_url = self.UPLOAD_URL or self.CREATOR_URL
        await self.page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
        # 等待页面稳定
        await self.page.wait_for_load_state("networkidle", timeout=15000)
        logger.info(f"📄 Opened upload page: {target_url}")

    async def _step(self, step_name: str, progress: float, message: str = ""):
        """更新进度并广播到前端

        Args:
            step_name: 步骤名称
            progress: 进度百分比 (0-100)
            message: 状态消息
        """
        await session_manager.update_status(
            self.session.session_id,
            current_step=step_name,
            progress=progress,
            message=message or step_name,
        )
        await session_manager.broadcast(self.session.session_id, {
            "type": "progress",
            "step": step_name,
            "progress": progress,
            "message": message or step_name,
        })

    async def _on_start(self):
        """发布开始时的回调"""
        await session_manager.update_status(
            self.session.session_id,
            status="running",
            current_step="launching",
            progress=0,
            message=f"开始发布到{self.PLATFORM_NAME}",
        )
        await session_manager.broadcast(self.session.session_id, {
            "type": "progress",
            "step": "launching",
            "progress": 0,
            "message": f"开始发布到{self.PLATFORM_NAME}",
        })

    async def _on_success(self):
        """发布成功时的回调"""
        platform_url = getattr(self, '_platform_url', '')
        await session_manager.update_status(
            self.session.session_id,
            status="success",
            current_step="complete",
            progress=100,
            message=f"✅ 视频已成功发布到{self.PLATFORM_NAME}！",
            platform_url=platform_url,
        )
        await session_manager.broadcast(self.session.session_id, {
            "type": "complete",
            "success": True,
            "platform_url": platform_url,
            "message": f"✅ 视频已成功发布到{self.PLATFORM_NAME}！",
        })

    async def _on_error(self, error: str):
        """发布失败时的回调

        Args:
            error: 错误信息
        """
        await session_manager.update_status(
            self.session.session_id,
            status="failed",
            error=error,
            message=f"❌ 发布失败：{error}",
        )
        await session_manager.broadcast(self.session.session_id, {
            "type": "error",
            "message": f"发布失败：{error}",
            "can_retry": True,
        })

    # ====== 抽象方法：各平台需要实现 ======

    @abstractmethod
    async def _upload_video(self, video_path: str):
        """上传视频

        Args:
            video_path: 视频文件路径
        """
        ...

    @abstractmethod
    async def _fill_metadata(self, title: str, text: str, topics: list):
        """填写标题、文案、话题

        Args:
            title: 视频标题
            text: 文案内容
            topics: 话题标签列表
        """
        ...

    @abstractmethod
    async def _set_cover(self, portrait: str, landscape: str):
        """设置竖屏、横屏封面

        Args:
            portrait: 竖屏封面 base64
            landscape: 横屏封面 base64
        """
        ...

    @abstractmethod
    async def _click_publish(self):
        """点击发布按钮并等待成功"""
        ...

    async def _random_delay(self, min_ms: int = 500, max_ms: int = 2000):
        """随机延迟，模拟人类操作

        Args:
            min_ms: 最小延迟（毫秒）
            max_ms: 最大延迟（毫秒）
        """
        import random
        delay = random.randint(min_ms, max_ms) / 1000
        await asyncio.sleep(delay)

    async def _type_human_like(self, element, text: str, delay_ms: int = 100):
        """像人类一样输入文字（带随机间隔）

        Args:
            element: Playwright 元素
            text: 要输入的文字
            delay_ms: 每次按键间隔（毫秒）
        """
        import random
        for char in text:
            await element.type(char, delay=random.randint(50, delay_ms))

    async def _find_and_fill_input(self, placeholder_pattern: str, text: str):
        """查找输入框并填写内容

        Args:
            placeholder_pattern: placeholder 文本匹配模式
            text: 要填写的内容
        """
        if not self.page or not text:
            return

        try:
            input_el = self.page.locator(f'[placeholder*="{placeholder_pattern}"]').first
            if await input_el.is_visible(timeout=5000):
                await input_el.click()
                await self._random_delay(200, 500)
                await input_el.fill(text)
                logger.info(f"✅ Filled input matching '{placeholder_pattern}'")
        except Exception:
            logger.warning(f"Could not find input matching '{placeholder_pattern}'")