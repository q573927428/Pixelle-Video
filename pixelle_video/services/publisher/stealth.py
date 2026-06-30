"""
Playwright 反检测脚本

用于绕过短视频平台对浏览器自动化的检测。
"""

STEALTH_SCRIPT = """
// 覆盖 webdriver 属性
Object.defineProperty(navigator, 'webdriver', { get: () => false });

// 覆盖 plugins 和 mimeTypes
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5],
});

// 覆盖 languages
Object.defineProperty(navigator, 'languages', {
    get: () => ['zh-CN', 'zh'],
});

// 覆盖 chrome 对象
window.chrome = { runtime: {} };

// 覆盖 permissions
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
        Promise.resolve({ state: Notification.permission }) :
        originalQuery(parameters)
);
"""


async def create_stealth_context(browser):
    """创建带有反检测配置的浏览器上下文

    Args:
        browser: Playwright Browser 实例

    Returns:
        BrowserContext: 配置了反检测脚本的浏览器上下文
    """
    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        locale="zh-CN",
        timezone_id="Asia/Shanghai",
        geolocation={"longitude": 116.4, "latitude": 39.9},
        permissions=["geolocation"],
    )
    await context.add_init_script(STEALTH_SCRIPT)
    return context