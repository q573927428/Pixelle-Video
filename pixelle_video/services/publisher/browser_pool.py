"""
浏览器池管理

管理 Playwright 浏览器实例的创建、复用和销毁。
支持多个浏览器上下文的隔离，以及并发限制。
"""

import asyncio
import time
from typing import Optional, Dict
from loguru import logger

try:
    from playwright.async_api import async_playwright, Browser, BrowserContext
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    logger.warning("playwright not installed, browser pool disabled")


class BrowserPool:
    """浏览器实例复用池

    管理 Playwright 浏览器实例，支持：
    - 浏览器实例的创建和复用
    - 并发任务限制
    - 闲置浏览器自动回收
    - 浏览器上下文隔离
    """

    def __init__(self, headless: bool = False, max_instances: int = 1,
                 idle_timeout: int = 600, chromium_path: str = "",
                 data_dir: str = "./browser_data"):
        """初始化 BrowserPool

        Args:
            headless: 是否无头模式
            max_instances: 最大浏览器实例数
            idle_timeout: 闲置超时（秒），超过时间自动关闭
            chromium_path: Chromium 可执行文件路径（留空自动查找）
            data_dir: 浏览器用户数据目录
        """
        self._headless = headless
        self._max_instances = max_instances
        self._idle_timeout = idle_timeout
        self._chromium_path = chromium_path
        self._data_dir = data_dir

        self._playwright = None
        self._browsers: Dict[str, Browser] = {}  # browser_id -> Browser
        self._browser_contexts: Dict[str, int] = {}  # browser_id -> context count
        self._browser_last_used: Dict[str, float] = {}  # browser_id -> last used timestamp
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        """启动浏览器池"""
        if not HAS_PLAYWRIGHT:
            logger.error("Playwright is not installed. Cannot start browser pool.")
            raise RuntimeError(
                "Playwright is not installed. "
                "Run: pip install playwright && playwright install chromium"
            )

        if self._running:
            logger.warning("BrowserPool is already running")
            return

        self._running = True
        self._playwright = await async_playwright().start()

        # Start background cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info(f"✅ BrowserPool started (max_instances={self._max_instances}, "
                    f"headless={self._headless})")

    async def stop(self):
        """停止浏览器池，关闭所有浏览器"""
        self._running = False

        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

        # Close all browsers
        async with self._lock:
            for browser_id, browser in list(self._browsers.items()):
                try:
                    await browser.close()
                    logger.info(f"Browser {browser_id} closed")
                except Exception as e:
                    logger.warning(f"Failed to close browser {browser_id}: {e}")
            self._browsers.clear()
            self._browser_contexts.clear()
            self._browser_last_used.clear()

        # Stop playwright
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

        logger.info("✅ BrowserPool stopped")

    async def get_context(self) -> Optional[object]:
        """获取一个隔离的浏览器上下文

        Returns:
            Optional[BrowserContext]: Playwright 浏览器上下文
        """
        if not self._running or not self._playwright:
            logger.error("BrowserPool is not running")
            return None

        async with self._lock:
            # 查找有空闲容量的浏览器
            target_browser_id = None
            for browser_id, count in self._browser_contexts.items():
                if count < 5:  # 每个浏览器最多 5 个上下文
                    target_browser_id = browser_id
                    break

            # 如果没有可用浏览器，创建新的
            if not target_browser_id:
                if len(self._browsers) >= self._max_instances:
                    logger.error("BrowserPool max instances reached, cannot create more")
                    return None

                target_browser_id = f"browser_{len(self._browsers)}_{int(time.time())}"
                browser = await self._playwright.chromium.launch(
                    headless=self._headless,
                    executable_path=self._chromium_path if self._chromium_path else None,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-infobars",
                        "--start-maximized",
                        "--window-size=1600,1000",
                    ],
                )
                self._browsers[target_browser_id] = browser
                self._browser_contexts[target_browser_id] = 0
                logger.info(f"🆕 Created browser {target_browser_id}")

            # 创建新上下文
            browser = self._browsers[target_browser_id]
            context = await browser.new_context(
                viewport={"width": 1600, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
                locale="zh-CN",
                timezone_id="Asia/Shanghai",
            )

            self._browser_contexts[target_browser_id] += 1
            self._browser_last_used[target_browser_id] = time.time()

            logger.info(f"✅ Created context on {target_browser_id} "
                        f"(contexts={self._browser_contexts[target_browser_id]})")
            return context

    async def release_context(self, context):
        """释放浏览器上下文

        Args:
            context: Playwright BrowserContext
        """
        if not context:
            return

        async with self._lock:
            # 找到这个 context 属于哪个浏览器
            for browser_id, browser in list(self._browsers.items()):
                try:
                    if context in browser.contexts:
                        await context.close()
                        self._browser_contexts[browser_id] -= 1
                        self._browser_last_used[browser_id] = time.time()
                        logger.info(f"✅ Released context on {browser_id} "
                                    f"(contexts={self._browser_contexts[browser_id]})")
                        return
                except Exception:
                    continue

    async def _cleanup_loop(self):
        """后台清理任务：关闭闲置浏览器"""
        while self._running:
            try:
                await asyncio.sleep(60)  # 每分钟检查一次
                await self._cleanup_idle_browsers()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Cleanup error: {e}")

    async def _cleanup_idle_browsers(self):
        """关闭闲置的浏览器实例"""
        now = time.time()
        async with self._lock:
            for browser_id in list(self._browser_contexts.keys()):
                # 跳过仍有上下文的浏览器
                if self._browser_contexts[browser_id] > 0:
                    continue

                last_used = self._browser_last_used.get(browser_id, 0)
                if now - last_used > self._idle_timeout:
                    try:
                        browser = self._browsers.pop(browser_id, None)
                        if browser:
                            await browser.close()
                            self._browser_contexts.pop(browser_id, None)
                            self._browser_last_used.pop(browser_id, None)
                            logger.info(f"♻️ Closed idle browser {browser_id}")
                    except Exception as e:
                        logger.warning(f"Failed to close idle browser {browser_id}: {e}")

    @property
    def is_running(self) -> bool:
        return self._running

    def stats(self) -> dict:
        """获取浏览器池状态统计"""
        return {
            "running": self._running,
            "browsers": len(self._browsers),
            "max_instances": self._max_instances,
            "contexts": sum(self._browser_contexts.values()),
            "browser_details": [
                {
                    "id": bid,
                    "contexts": self._browser_contexts.get(bid, 0),
                    "idle_seconds": int(time.time() - self._browser_last_used.get(bid, 0)),
                }
                for bid in self._browsers.keys()
            ],
        }


# 全局浏览器池实例
browser_pool = BrowserPool()