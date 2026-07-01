"""
抖音发布器

实现抖音创作者平台的视频自动发布流程。
"""

import asyncio
import math
from loguru import logger
from pixelle_video.services.publisher.publisher_base import BasePublisher
from pixelle_video.services.publisher.session_manager import session_manager
from pixelle_video.services.publisher.cookie_manager import cookie_manager


class DouyinPublisher(BasePublisher):
    """抖音发布器"""

    PLATFORM_NAME = "抖音"
    CREATOR_URL = "https://creator.douyin.com/creator-micro/content/upload"
    UPLOAD_URL = "https://creator.douyin.com/creator-micro/content/upload"

    async def _is_page_closed(self) -> bool:
        """检测页面/浏览器是否已被关闭

        Returns:
            bool: 是否已关闭
        """
        if not self.page:
            return True
        try:
            # 尝试最轻量的操作检测页面是否存活
            self.page.url
            return False
        except Exception:
            logger.info("🔌 Page/browser has been closed")
            return True

    async def _is_logged_in(self) -> bool:
        """检测抖音是否已登录

        抖音的创作者后台 URL 即使未登录也会包含 /creator/ 路径，
        但未登录时会显示登录二维码遮罩层。
        真正的登录态判断依据：
        1. 页面中没有登录二维码/登录按钮
        2. 页面中包含登录后才能看到的元素（如用户头像、上传区域）
        """
        if not self.page:
            return False

        # 快速检测页面是否已关闭
        if await self._is_page_closed():
            return False

        try:
            # 等待页面稳定
            await self.page.wait_for_timeout(2000)

            # 1. 检查是否存在登录相关元素 → 未登录
            login_elements = [
                '.qrcode-img',           # 登录二维码
                'div[class*="qrcode"]',  # 二维码容器
                '.login-container',      # 登录容器
                'div[class*="login"]',   # 登录弹窗
                'button:has-text("登录")',
            ]
            for selector in login_elements:
                el = self.page.locator(selector).first
                if await el.is_visible(timeout=1000):
                    logger.info(f"🔑 Found login element '{selector}', not logged in")
                    return False

            # 2. 检查登录成功后的特征元素
            logged_in_indicators = [
                '.upload-container',     # 上传区域
                '.avatar-container',     # 用户头像
                'img[class*="avatar"]',  # 头像图片
                '[class*="user-info"]',  # 用户信息区域
                '.creator-header',       # 创作者头部
            ]
            for selector in logged_in_indicators:
                el = self.page.locator(selector).first
                if await el.is_visible(timeout=1000):
                    logger.info(f"✅ Found logged-in indicator '{selector}'")
                    return True

            # 3. 关键：检查是否已经在创作者上传页面（无需登录即可访问的页面才会有重定向）
            current_url = self.page.url
            if "creator-micro/content/upload" in current_url or "creator-micro" in current_url:
                logger.info(f"✅ Already on creator upload page, logged in")
                return True

            # 4. 兜底：检查 URL 是否包含重定向到登录页的标识
            login_keywords = ["login", "passport", "signin", "oauth"]
            if any(k in current_url.lower() for k in login_keywords):
                logger.info("URL contains login redirect")
                return False

            # 5. 无法确定时，打印页面关键信息帮助调试
            page_title = await self.page.title()
            logger.info(f"⚠️ Login status uncertain, page title: {page_title}, url: {current_url}")
            return False

        except Exception as e:
            # 判断是否是页面已关闭导致的异常
            err_str = str(e).lower()
            if any(kw in err_str for kw in ["closed", "has been closed", "target page"]):
                logger.info("🔌 Page/browser was closed during login check, stopping")
                self.page = None  # 标记页面已无效
            else:
                logger.error(f"Login check error: {e}")
            return False

    async def _need_login(self) -> bool:
        """处理抖音扫码登录流程

        1. 已访问创作者页面发现未登录，定位二维码
        2. 截图二维码并推送到前端
        3. 等待用户扫码完成（轮询检测页面登录态）
        4. 保存 Cookie
        5. 返回 True/False

        Returns:
            bool: 是否成功登录
        """
        if not self.page:
            return False

        try:
            await self._step("need_login", 10, "请使用抖音App扫码登录")

            # 1. 页面已经在创作者页面(包含二维码)，查找二维码元素并截图
            qr_img_data = await self._capture_qrcode()

            if not qr_img_data:
                # 如果没找到二维码，尝试导航到登录页面
                logger.info("QR code not found on creator page, navigating to login...")
                await self._step("need_login", 10, "正在打开登录页面...")
                await self.page.goto(
                    "https://creator.douyin.com/creator-micro/content/upload",
                    wait_until="domcontentloaded",
                    timeout=30000,
                )
                await self.page.wait_for_timeout(3000)
                qr_img_data = await self._capture_qrcode()

            if not qr_img_data:
                logger.error("Cannot find QR code on login page")
                await self._step("need_login", 10, "未找到登录二维码")
                return False

            # 2. 先缓存二维码到 session（确保 WS 断连重连后仍能获取）
            await session_manager.update_status(
                self.session.session_id,
                pending_qrcode=qr_img_data,
                current_step="need_login",
            )

            # 3. 广播二维码图片到前端
            await session_manager.broadcast(self.session.session_id, {
                "type": "qrcode",
                "platform": self.PLATFORM_NAME,
                "image": qr_img_data,
                "message": f"请使用{self.PLATFORM_NAME}App扫码登录",
            })

            # 4. 等待用户扫码完成（最长等待 300 秒）
            await self._step("need_login", 10, "等待扫码...")
            logged_in = await self._wait_login_complete(timeout=300)

            # 清除缓存的二维码
            await session_manager.update_status(
                self.session.session_id,
                pending_qrcode=None,
            )

            if logged_in:
                logger.info(f"✅ User {self.session.user_id} logged in to {self.PLATFORM_NAME} via QR code")

                # 保存 Cookie
                await self._save_login_cookies()

                await self._step("need_login", 10, "登录成功，准备发布")
                await session_manager.broadcast(self.session.session_id, {
                    "type": "login_success",
                    "message": "扫码登录成功",
                })
                return True
            else:
                logger.warning("QR login timeout or failed")
                return False

        except Exception as e:
            logger.error(f"QR login failed: {e}")
            return False

    async def _capture_qrcode(self) -> str:
        """捕获登录二维码截图

        使用纯 JS 在浏览器中直接提取二维码图片 src 或截图。
        不依赖 Playwright 的 is_visible() 检测（可能因渲染时序返回 False），
        而是通过 JS 直接操作 DOM 查找。

        Returns:
            str: 二维码图片的 base64 data URL，未找到时返回 None
        """
        if not self.page:
            return None

        # 快速检测页面是否已关闭
        if await self._is_page_closed():
            return None

        try:
            # 等待页面稳定
            await self.page.wait_for_timeout(3000)

            import base64

            # ---------- 策略 1: JS 直接提取 class 含 qrcode 的 img 的 src ----------
            logger.info("Strategy 1: JS extract qrcode img src by class...")
            qr_src = await self.page.evaluate("""
                () => {
                    // 1. 查找所有 class 包含 qrcode 的 img
                    const allImgs = document.querySelectorAll('img');
                    for (const img of allImgs) {
                        const cls = (img.className || '').toLowerCase();
                        const src = img.src || '';
                        if (src.startsWith('data:image') && cls.includes('qrcode')) {
                            return src;
                        }
                    }
                    // 2. 查找 qrcode div 内的 img
                    const qrDivs = document.querySelectorAll('div[class*="qrcode"]');
                    for (const div of qrDivs) {
                        const img = div.querySelector('img');
                        if (img && img.src && img.src.startsWith('data:image')) {
                            return img.src;
                        }
                    }
                    return null;
                }
            """)

            if qr_src:
                logger.info(f"🟢 QR captured via class 'qrcode' img src ({len(qr_src)} chars)")
                return qr_src

            # ---------- 策略 2: JS 截图含 qrcode class 的 div ----------
            logger.info("Strategy 2: JS screenshot qrcode div...")
            qr_div_info = await self.page.evaluate("""
                () => {
                    const qrDivs = document.querySelectorAll('div[class*="qrcode"]');
                    for (const div of qrDivs) {
                        const rect = div.getBoundingClientRect();
                        if (rect.width > 100 && rect.height > 100 && rect.width < 500) {
                            return { x: rect.x, y: rect.y, w: rect.width, h: rect.height };
                        }
                    }
                    return null;
                }
            """)

            if qr_div_info:
                try:
                    screenshot = await self.page.screenshot(
                        type="jpeg", quality=85,
                        clip={
                            "x": qr_div_info["x"], "y": qr_div_info["y"],
                            "width": qr_div_info["w"], "height": qr_div_info["h"],
                        }
                    )
                    b64 = base64.b64encode(screenshot).decode()
                    if len(b64) > 5000:  # 截图即使小一点也能接受
                        data_url = f"data:image/jpeg;base64,{b64}"
                        logger.info(f"🟢 QR captured via qrcode div screenshot ({len(data_url)} chars)")
                        return data_url
                except Exception:
                    pass

            # ---------- 策略 3: JS 查找所有 data:image 图片，按数据体积排序取最大 ----------
            logger.info("Strategy 3: JS find largest data:image by size...")
            qr_src = await self.page.evaluate("""
                () => {
                    const allImgs = document.querySelectorAll('img');
                    let best = null;
                    let bestLen = 0;
                    for (const img of allImgs) {
                        const src = img.src || '';
                        if (!src.startsWith('data:image')) continue;
                        // 只取可见区域内的
                        const rect = img.getBoundingClientRect();
                        if (rect.width < 30 || rect.height < 30) continue;
                        if (rect.top > window.innerHeight || rect.left > window.innerWidth) continue;
                        if (src.length > bestLen) {
                            bestLen = src.length;
                            best = src;
                        }
                    }
                    // 放宽条件，只要比 3000 chars 大就接受（二维码 min 约 5K）
                    if (best && bestLen > 3000) return best;
                    return null;
                }
            """)

            if qr_src:
                logger.info(f"🟢 QR captured via JS data size scan ({len(qr_src)} chars)")
                return qr_src

            # ---------- 策略 4: JS 查找含"扫码"/"扫一扫"文本的 div，裁剪截图 ----------
            logger.info("Strategy 4: JS find div with '扫码' text...")
            scan_div = await self.page.evaluate("""
                () => {
                    const allDivs = document.querySelectorAll('div');
                    for (const div of allDivs) {
                        const rect = div.getBoundingClientRect();
                        if (rect.width < 200 || rect.height < 200) continue;
                        if (rect.width > 600 || rect.height > 700) continue;
                        if (rect.top > window.innerHeight || rect.left > window.innerWidth) continue;
                        const text = (div.textContent || '').toLowerCase();
                        if (text.includes('扫码') || text.includes('扫一扫')) {
                            return { x: rect.x, y: rect.y, w: rect.width, h: rect.height };
                        }
                    }
                    return null;
                }
            """)

            if scan_div:
                try:
                    screenshot = await self.page.screenshot(
                        type="jpeg", quality=85,
                        clip={
                            "x": scan_div["x"], "y": scan_div["y"],
                            "width": scan_div["w"], "height": scan_div["h"],
                        }
                    )
                    b64 = base64.b64encode(screenshot).decode()
                    if len(b64) > 5000:
                        data_url = f"data:image/jpeg;base64,{b64}"
                        logger.info(f"🟢 QR captured via '扫码' div screenshot ({len(data_url)} chars)")
                        return data_url
                except Exception:
                    pass

            # ---------- 策略 5: 中心区域截图 ----------
            logger.info("Strategy 5: Center area screenshot...")
            viewport = await self.page.viewport_size()
            if viewport:
                vw, vh = viewport['width'], viewport['height']
                clip_x = max(0, vw // 2 - 200)
                clip_y = max(0, vh // 2 - 250)
                clip_w = min(450, vw - clip_x)
                clip_h = min(550, vh - clip_y)
                try:
                    center_screenshot = await self.page.screenshot(
                        type="jpeg", quality=85,
                        clip={"x": clip_x, "y": clip_y, "width": clip_w, "height": clip_h}
                    )
                    b64 = base64.b64encode(center_screenshot).decode()
                    if len(b64) > 5000:
                        data_url = f"data:image/jpeg;base64,{b64}"
                        logger.info(f"🟢 Center area screenshot ({len(data_url)} chars)")
                        return data_url
                except Exception:
                    pass

            # ---------- 策略 6: 最终兜底 - 全页面截图 ----------
            logger.info("Strategy 6: Full page screenshot...")
            try:
                full_screenshot = await self.page.screenshot(type="jpeg", quality=70)
                b64 = base64.b64encode(full_screenshot).decode()
                data_url = f"data:image/jpeg;base64,{b64}"
                logger.info(f"📸 Full page screenshot ({len(data_url)} chars)")
                return data_url
            except Exception:
                logger.warning("Full page screenshot failed")
                return None

        except Exception as e:
            logger.warning(f"Capture QR code failed: {e}")
            return None

    async def _wait_login_complete(self, timeout: int = 300) -> bool:
        """等待用户扫码完成

        持续检测页面登录态，直到用户扫码登录成功或超时。

        Args:
            timeout: 超时秒数

        Returns:
            bool: 是否登录成功
        """
        if not self.page:
            return False

        check_interval = 2  # 每 2 秒检测一次
        waited = 0

        while waited < timeout:
            # 快速检测页面是否已关闭，关闭则立即退出
            if await self._is_page_closed():
                logger.info("🔌 Page was closed by user during login wait, stopping wait loop")
                await session_manager.broadcast(self.session.session_id, {
                    "type": "error",
                    "message": "登录已取消 - 页面已关闭",
                    "can_retry": True,
                })
                await self._step("need_login", 10, "登录已取消 - 页面已关闭")
                return False

            logged_in = await self._is_logged_in()
            if logged_in:
                return True

            # 更新状态通知前端
            remaining = timeout - waited
            if remaining > 0:
                await session_manager.broadcast(self.session.session_id, {
                    "type": "qrcode_waiting",
                    "message": f"等待扫码... ({remaining}秒)",
                    "remaining": remaining,
                })

            await asyncio.sleep(check_interval)
            waited += check_interval

            # 每 15 秒检查一次二维码是否过期，重新捕获
            if waited % 30 == 0 and waited < timeout - 30:
                # 再次检测页面是否存活，防止在过期检测时浏览器已关闭
                if await self._is_page_closed():
                    logger.info("🔌 Page was closed during QR refresh, stopping")
                    return False

                # 检查二维码是否仍然可见
                try:
                    qr_visible = False
                    for selector in ['.qrcode-img', 'div[class*="qrcode"] img', 'img[class*="qrcode"]']:
                        el = self.page.locator(selector).first
                        if await el.is_visible(timeout=1000):
                            qr_visible = True
                            break

                    if not qr_visible:
                        logger.info("QR code disappeared, re-capturing...")
                        await session_manager.broadcast(self.session.session_id, {
                            "type": "qrcode_expired",
                            "message": "二维码已过期，重新获取中...",
                        })
                        # 刷新页面重新获取二维码
                        await self.page.reload(wait_until="domcontentloaded", timeout=30000)
                        await self.page.wait_for_timeout(3000)
                        qr_img_data = await self._capture_qrcode()
                        if qr_img_data:
                            await session_manager.broadcast(self.session.session_id, {
                                "type": "qrcode",
                                "platform": self.PLATFORM_NAME,
                                "image": qr_img_data,
                                "message": "二维码已刷新",
                            })
                except Exception:
                    pass

        return False

    async def _save_login_cookies(self):
        """登录成功后保存 Cookie"""
        if not self.context:
            return
        try:
            cookies = await self.context.cookies()
            if cookies:
                # 尝试获取账户名称（通过多种方式强化提取）
                account_name = await self._extract_account_name()

                await cookie_manager.save(
                    user_id=self.session.user_id,
                    platform=self.PLATFORM_NAME,
                    cookies=cookies,
                    account_name=account_name or f"{self.PLATFORM_NAME}用户",
                )
                logger.info(f"✅ Cookies saved for {self.PLATFORM_NAME}, account_name={account_name}")
        except Exception as e:
            logger.warning(f"Save cookies failed: {e}")

    async def _extract_account_name(self) -> str | None:
        """从页面中提取真实账户昵称

        使用多种策略依次尝试：
        1. DOM 选择器提取（头像附近的用户名、用户信息区域）
        2. JS eval 从 document.title / meta / cookie 中提取
        3. 从 session cookie 中解析 nickname 等信息

        Returns:
            str | None: 提取到的账户昵称
        """
        if not self.page:
            return None

        try:
            # ---- 策略 1: DOM 选择器提取 ----
            for selector in [
                # 创作者头像旁边或右上角用户昵称
                '.user-name',
                '.creator-header .user-name',
                '.creator-header .name',
                '.avatar-container .name',
                '.avatar-container [class*="nickname"]',
                '[class*="user-info"] [class*="name"]',
                '[class*="user-info"] [class*="nickname"]',
                '[class*="header"] [class*="name"]',
                '[class*="header"] [class*="nickname"]',
                # 头像下方的昵称
                '.user-avatar + span',
                '.avatar-wrap + span',
                '[class*="avatar"] + [class*="name"]',
                # 通用
                '[class*="nickname"]',
                '[class*="user-name"]',
            ]:
                try:
                    el = self.page.locator(selector).first
                    if await el.is_visible(timeout=1000):
                        text = (await el.text_content() or '').strip()
                        if text and len(text) > 0 and len(text) < 50:
                            logger.info(f"✅ Account name found via selector '{selector}': {text}")
                            return text
                except Exception:
                    continue

            # ---- 策略 2: JS eval 深入提取 ----
            js_name = await self.page.evaluate("""
                () => {
                    function tryGet(sel) {
                        const el = document.querySelector(sel);
                        return el ? (el.textContent || '').trim() : null;
                    }

                    // 尝试常见选择器（JS 方式可以拿到隐藏元素）
                    const selectors = [
                        '.user-name',
                        '.creator-header .user-name',
                        '.avatar-container [class*="nickname"]',
                        '[class*="user-info"] [class*="name"]',
                        '[class*="user-info"] [class*="nickname"]',
                        '[class*="nickname"]',
                        '[class*="user-name"]',
                        // 有时昵称在 img alt 属性中
                        'img[class*="avatar"]',
                    ];
                    for (const s of selectors) {
                        const v = tryGet(s);
                        if (v && v.length > 0 && v.length < 50) return v;
                    }

                    // 从 img alt 中提取
                    const avatars = document.querySelectorAll('img[class*="avatar"], img[class*="user"]');
                    for (const img of avatars) {
                        if (img.alt && img.alt.length > 0 && img.alt.length < 50 && !img.alt.includes('avatar')) {
                            return img.alt;
                        }
                    }

                    // 从 document.title 中提取（某些页面标题包含昵称）
                    const title = document.title || '';
                    const titleMatch = title.match(/([\\u4e00-\\u9fa5\\w]+)\\s*的(?:创作|主页|抖音)/);
                    if (titleMatch) return titleMatch[1].trim();

                    return null;
                }
            """)
            if js_name:
                logger.info(f"✅ Account name found via JS: {js_name}")
                return js_name

            # ---- 策略 3: 从 cookie 中提取 ----
            # 抖音 Cookie sessionid 有时携带用户名信息
            try:
                for c in await self.context.cookies():
                    # 某些 session cookie 的 value 包含 nickname
                    if c.get('name') in ('sessionid', 'sid', 'uid', 'userid') and c.get('value'):
                        val = c['value']
                        # 尝试 decode
                        import urllib.parse
                        decoded = urllib.parse.unquote(val)
                        if len(decoded) < 50 and not decoded.startswith('_'):
                            return decoded
            except Exception:
                pass

        except Exception as e:
            logger.warning(f"Account name extraction failed: {e}")

        return None

    async def _upload_video(self, video_path: str):
        """上传视频到抖音

        Args:
            video_path: 视频文件路径
        """
        if not self.page:
            return

        try:
            # 查找 input[type="file"] 并设置视频文件
            file_inputs = self.page.locator('input[type="file"]')
            count = await file_inputs.count()
            if count > 0:
                await file_inputs.first.set_input_files(video_path)
                logger.info(f"📤 Video file set via input[type=file]: {video_path}")
            else:
                upload_trigger = self.page.locator(
                    '.upload-btn, .upload-trigger, [class*="upload"], '
                    'div:has-text("点击上传"), div:has-text("上传视频"), '
                    '[class*="container"] [class*="upload"]'
                ).first
                if await upload_trigger.is_visible(timeout=5000):
                    await upload_trigger.click()
                    logger.info("Clicked upload trigger area")
                    await self._random_delay(1000, 2000)
                    file_input = self.page.locator('input[type="file"]').first
                    if await file_input.is_visible(timeout=5000):
                        await file_input.set_input_files(video_path)
                        logger.info(f"📤 Video file set after trigger click: {video_path}")
                    else:
                        raise Exception("无法找到文件上传 input")

            # 等待页面跳转到 post 编辑页面（视频上传完成后抖音自动跳转）
            # https://creator.douyin.com/creator-micro/content/post/video?enter_from=publish_page
            await self._step("uploading", 40, "视频上传中...")
            for i in range(30):
                current_url = self.page.url
                if "/content/post/" in current_url:
                    logger.info(f"✅ Upload complete, redirected to post page: {current_url}")
                    await self._step("uploading", 70, "视频上传完成")
                    break
                await self.page.wait_for_timeout(1000)

            # 等待 post 页面加载稳定
            await self.page.wait_for_load_state("networkidle", timeout=15000)
            await self.page.wait_for_timeout(2000)
            logger.info("✅ Video upload wait complete")

        except Exception as e:
            logger.error(f"Upload failed: {e}")
            raise

    async def _fill_metadata(self, title: str, text: str, topics: list):
        """填写标题、文案和话题

        Args:
            title: 视频标题
            text: 文案内容
            topics: 话题标签列表
        """
        if not self.page:
            return

        try:
            # 先尝试在新版 post 页面查找输入框（优先）/content/post/xxx
            # 如果找不到再降级到旧版 upload 页面选择器
            title_input = None
            desc_input = None

            # 查找所有可见的输入框和可编辑区域
            # 标题通常是第一个大的输入框或 contenteditable 区域
            for selector in [
                # 新版 post 页面选择器
                '[class*="title"] [contenteditable="true"]',
                '[class*="title"] input',
                '[class*="title"] [contenteditable]',
                '[placeholder*="标题"]',
                '[class*="notranslate"]',  # 抖音 post 页面的输入框特征
                # 旧版 upload 页面选择器
                '.upload-input',
                '[placeholder*="标题"]',
                # 兜底
                'input[type="text"]',
            ]:
                el = self.page.locator(selector).first
                if await el.is_visible(timeout=1000):
                    title_input = el
                    logger.info(f"Found title input via selector: {selector}")
                    break

            if title_input:
                if title:
                    await title_input.click()
                    await self._random_delay()
                    # contenteditable 元素用 fill 可能无效，尝试逐字输入
                    try:
                        await title_input.fill(title)
                    except Exception:
                        await self._type_human_like(title_input, title)
                    logger.info(f"✅ Title filled: {title}")
                # 如果标题已存在（自动填入），尝试找到文案输入框并替换
                await self._random_delay(500, 1000)

            # 填写文案 + 话题
            # 注意：self.params.full_text 已经通过 BasePublisher 的 property 自动拼接了 topics
            # 如果直接用 self.params.full_text 后又在此追加 topics，会导致话题被填写两次
            if hasattr(self, "params") and getattr(self.params, "full_text", None):
                full_text = self.params.full_text
            else:
                # 兜底：手动拼接
                full_text = text or ""
                if topics:
                    topics_str = " ".join(topics)
                    full_text = f"{full_text}\n{topics_str}" if full_text else topics_str

            if full_text:

                # 查找文案输入框（通常是更大的编辑区域、textarea 或 contenteditable div）
                for selector in [
                    # 新版 post 页面 - 文案区域
                    '[class*="desc"] [contenteditable="true"]',
                    '[class*="desc"] textarea',
                    '[class*="content"] [contenteditable="true"]',
                    '[class*="content"] textarea',
                    'textarea',
                    '[placeholder*="文案"]',
                    '[placeholder*="描述"]',
                    '[placeholder*="说点什么"]',
                    '.desc-textarea textarea',
                    '[contenteditable="true"]',  # 兜底：任意可编辑区域
                ]:
                    el = self.page.locator(selector).first
                    if await el.is_visible(timeout=1000):
                        desc_input = el
                        logger.info(f"Found description input via selector: {selector}")
                        break

                if desc_input:
                    await desc_input.click()
                    await self._random_delay()
                    try:
                        # 先清空再填入
                        await desc_input.fill("")
                        await self._random_delay(200, 400)
                        await desc_input.fill(full_text)
                    except Exception:
                        await desc_input.click()
                        await self._type_human_like(desc_input, full_text)
                    logger.info(f"✅ Description filled ({len(full_text)} chars)")

        except Exception as e:
            logger.error(f"Fill metadata failed: {e}")
            raise

    async def _save_temp_image(
        self,
        base64_str: str,
        suffix: str = ".jpg",
        target_width: int = 1440,
        target_height: int = 1920,
        quality: int = 95,
    ) -> str:
        """将 base64 图片保存为临时文件，并精确匹配抖音要求的封面比例

        抖音封面推荐标准（实际生效比例）:
        - 竖屏封面: 3:4 比例，例如 1440x1920（抖音的"竖封面预览（3:4）"）
        - 横屏封面: 16:9 比例，例如 1920x1080（或 4:3 也可）

        为了避免抖音上传封面后弹出"设置封面/裁剪封面"弹窗，本方法会：
        1. 按目标比例把原图 letterbox（用黑色补边）到目标 target_width x target_height
           - 不会切掉原图的任何内容
           - 输出的图片精确等于目标宽高（即目标宽高比 == 目标比例）
        2. 保存为高质量 JPEG

        Args:
            base64_str: base64 图片数据（data:image/... 格式或裸 base64）
            suffix: 文件后缀
            target_width: 目标输出宽度（精确）
            target_height: 目标输出高度（精确）
            quality: JPEG 保存质量 (1-100)

        Returns:
            临时文件路径
        """
        import tempfile
        import base64
        import io
        from PIL import Image

        # 解码 base64
        if "," in base64_str:
            img_data = base64.b64decode(base64_str.split(",")[-1])
        else:
            img_data = base64.b64decode(base64_str)

        try:
            img = Image.open(io.BytesIO(img_data))
            if img.mode != "RGB":
                img = img.convert("RGB")
            width, height = img.size
            src_ratio = width / height if height > 0 else 1
            target_ratio = target_width / target_height if target_height > 0 else 1

            logger.info(
                f"Resizing cover image: src={width}x{height} "
                f"(ratio={src_ratio:.3f}) -> target={target_width}x{target_height} "
                f"(ratio={target_ratio:.3f})"
            )

            # 计算缩放比例 —— 让原图完整放入目标画布内（fit）
            scale = min(target_width / width, target_height / height)
            new_w = max(1, int(round(width * scale)))
            new_h = max(1, int(round(height * scale)))

            # 使用 Lanczos 重采样
            resized = img.resize((new_w, new_h), Image.LANCZOS)

            # 创建目标画布，将 resized 图片居中粘贴（其余部分黑色）
            canvas = Image.new("RGB", (target_width, target_height), (0, 0, 0))
            offset_x = (target_width - new_w) // 2
            offset_y = (target_height - new_h) // 2
            canvas.paste(resized, (offset_x, offset_y))

            logger.info(
                f"Image letterboxed to exact {target_width}x{target_height} "
                f"(inner {new_w}x{new_h} at offset {offset_x},{offset_y})"
            )

            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
                save_format = "JPEG" if suffix.lower() in (".jpg", ".jpeg") else "PNG"
                canvas.save(f, format=save_format, quality=quality)
                return f.name

        except Exception as e:
            logger.warning(f"Image resize failed, saving original: {e}")
            # 降级：直接保存原图
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
                f.write(img_data)
                return f.name


    async def _upload_cover_file(self, file_input_locator, image_path: str) -> bool:
        """上传封面文件到指定的 file input

        Args:
            file_input_locator: file input 的 locator
            image_path: 图片文件路径

        Returns:
            是否上传成功
        """
        try:
            await file_input_locator.set_input_files(image_path)
            await self._random_delay(2000, 3000)
            return True
        except Exception as e:
            logger.warning(f"Upload cover file failed: {e}")
            return False

    async def _click_by_text(self, texts: list[str], timeout: int = 3000) -> bool:
        """按文本查找并点击按钮

        Args:
            texts: 要查找的文本列表（按优先级排序）
            timeout: 每个选择器的超时时间(ms)

        Returns:
            是否成功点击
        """
        for text in texts:
            try:
                btn = self.page.locator(f'button:has-text("{text}")').first
                if await btn.is_visible(timeout=timeout):
                    await btn.click()
                    await self._random_delay(500, 1000)
                    logger.info(f"Clicked button with text: {text}")
                    return True
            except Exception:
                continue
        return False

    async def _confirm_crop_dialog(self, max_wait_ms: int = 6000) -> bool:
        """处理封面上传后弹出的裁剪弹窗

        抖音的实际交互（从截图分析）：
        - 上传封面后，会在"设置封面"外层弹窗之上再叠加一个中间弹窗
        - 这个中间裁剪弹窗标题也是"设置封面"（！），底部按钮是"取消"和"保存（红色主按钮）"
        - 用户必须点击这个中间弹窗里的红色"保存"按钮，图片才真正应用
        - 如果找错了按钮（比如点了外层弹窗底部的"完成"），会导致：
          - 裁剪弹窗依然显示
          - 外层"设置封面"弹窗被过早关闭
          - 最终封面未真正设置，且流程错乱

        本方法策略：
        1. 使用 JS 在浏览器端遍历 DOM，找出"最顶层可见的 dialog/modal"节点（即
           z-index 或 DOM 位置最靠后的弹窗，就是刚打开的裁剪弹窗）
        2. 在该弹窗内优先点击"保存"（这是裁剪弹窗真正的确认按钮）
        3. 若找不到"保存"再降级尝试"确定/确认/完成/应用"

        Args:
            max_wait_ms: 最长等待裁剪弹窗出现的时间(ms)

        Returns:
            是否检测到并成功关闭裁剪弹窗（未出现弹窗返回 False）
        """
        if not self.page:
            return False

        # 使用 JS 一体化处理：等待弹窗出现 → 找出最顶层弹窗 → 点击其中"保存"按钮
        # 这样最可靠，避免 Playwright 多层 locator 定位错弹窗
        js_result = await self.page.evaluate(
            """
            async ({ maxWaitMs }) => {
                function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

                function isVisible(el) {
                    if (!el) return false;
                    const rect = el.getBoundingClientRect();
                    if (rect.width < 50 || rect.height < 50) return false;
                    const style = window.getComputedStyle(el);
                    if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
                    return true;
                }

                function findTopmostCropDialog() {
                    // 查找所有可能的 dialog/modal 容器
                    const candidates = document.querySelectorAll(
                        '[role="dialog"], [class*="dialog"], [class*="Dialog"], ' +
                        '[class*="modal"], [class*="Modal"]'
                    );
                    const visibleDialogs = [];
                    for (const el of candidates) {
                        if (!isVisible(el)) continue;
                        // 必须包含"保存"或"确定"按钮才可能是要处理的确认弹窗
                        const btns = el.querySelectorAll('button');
                        let hasConfirmButton = false;
                        let hasCancelButton = false;
                        for (const b of btns) {
                            const t = (b.textContent || '').trim();
                            if (t === '保存' || t === '确定' || t === '确认') hasConfirmButton = true;
                            if (t === '取消') hasCancelButton = true;
                        }
                        // 裁剪弹窗的典型特征：同时有"取消"和"保存/确定"按钮
                        if (hasConfirmButton && hasCancelButton) {
                            const rect = el.getBoundingClientRect();
                            const z = parseInt(window.getComputedStyle(el).zIndex) || 0;
                            visibleDialogs.push({ el, rect, z });
                        }
                    }
                    if (visibleDialogs.length === 0) return null;
                    // 按 z-index 降序、然后按面积升序（越小越可能是"叠在最上层"的裁剪弹窗）
                    visibleDialogs.sort((a, b) => {
                        if (b.z !== a.z) return b.z - a.z;
                        const areaA = a.rect.width * a.rect.height;
                        const areaB = b.rect.width * b.rect.height;
                        return areaA - areaB;  // 面积小的优先（更居中的裁剪弹窗）
                    });
                    return visibleDialogs[0].el;
                }

                // 阶段 1：等待裁剪弹窗出现
                const start = Date.now();
                let dialog = null;
                while (Date.now() - start < maxWaitMs) {
                    dialog = findTopmostCropDialog();
                    if (dialog) break;
                    await sleep(300);
                }
                if (!dialog) return { found: false };

                // 阶段 2：等待弹窗内的图片加载完成
                await sleep(1500);

                // 阶段 3：在弹窗内查找并点击"保存"按钮（红色主按钮）
                // 优先级：保存 > 确定 > 确认 > 完成 > 应用
                const priorityTexts = ["保存", "确定", "确认", "完成", "应用"];
                let clickedText = null;
                for (const txt of priorityTexts) {
                    const btns = dialog.querySelectorAll('button');
                    for (const b of btns) {
                        const bt = (b.textContent || '').trim();
                        if (bt !== txt) continue;
                        // 检查按钮是否可用
                        if (b.disabled) continue;
                        const cls = (b.className || '').toLowerCase();
                        if (cls.includes('disabled')) continue;
                        // 直接触发 click
                        b.click();
                        clickedText = txt;
                        break;
                    }
                    if (clickedText) break;
                }

                if (!clickedText) return { found: true, clicked: false };

                // 阶段 4：等待弹窗关闭（DOM 消失或 opacity 变 0）
                await sleep(1500);
                const stillVisible = isVisible(dialog);
                return { found: true, clicked: true, clickedText, stillVisible };
            }
            """,
            {"maxWaitMs": max_wait_ms},
        )

        if not js_result or not js_result.get("found"):
            logger.info("No crop dialog detected (may not be required)")
            return False

        if not js_result.get("clicked"):
            logger.warning("⚠️  Crop dialog detected but no confirm button clicked")
            return False

        clicked_text = js_result.get("clickedText")
        still_visible = js_result.get("stillVisible")
        logger.info(f"✅ Crop dialog confirmed via '{clicked_text}' button")

        if still_visible:
            logger.warning("Crop dialog still visible after click, waiting extra 2s...")
            await self._random_delay(2000, 2500)
            # 再检查一次，如果仍在，尝试再次点击
            js_recheck = await self.page.evaluate(
                """
                () => {
                    const dialogs = document.querySelectorAll(
                        '[role="dialog"], [class*="dialog"], [class*="modal"]'
                    );
                    for (const el of dialogs) {
                        const rect = el.getBoundingClientRect();
                        if (rect.width < 50 || rect.height < 50) continue;
                        const style = window.getComputedStyle(el);
                        if (style.display === 'none' || style.visibility === 'hidden') continue;
                        const btns = el.querySelectorAll('button');
                        let hasSave = false, hasCancel = false;
                        for (const b of btns) {
                            const t = (b.textContent || '').trim();
                            if (t === '保存' || t === '确定') hasSave = true;
                            if (t === '取消') hasCancel = true;
                        }
                        if (hasSave && hasCancel) {
                            // 再次尝试点击"保存"
                            for (const b of btns) {
                                if ((b.textContent || '').trim() === '保存' && !b.disabled) {
                                    b.click();
                                    return true;
                                }
                            }
                        }
                    }
                    return false;
                }
                """
            )
            if js_recheck:
                logger.info("✅ Crop dialog re-clicked '保存'")
                await self._random_delay(1500, 2000)

        await self._random_delay(500, 1000)
        return True



    async def _set_cover(self, portrait: str, landscape: str):
        """设置封面（竖封面 + 横封面）

        完整流程:
        1. 点击"自定义封面"按钮打开封面对话框
        2. 上传竖封面文件
        3. 等待上传完成
        4. 点击"设置横封面"切换到横封面上传
        5. 上传横封面文件
        6. 等待上传完成
        7. 点击"完成"

        Args:
            portrait: 竖屏封面 base64
            landscape: 横屏封面 base64
        """
        if not self.page:
            return

        import os

        temp_files = []

        try:
            # Step 1: 查找并点击"自定义封面"按钮
            cover_btn = None
            for selector in [
                'button:has-text("自定义封面")',
                'button:has-text("选择封面")',
                'button:has-text("封")',
                '[class*="cover"] button',
                '[class*="封面"]',
                '[class*="cover"]',
            ]:
                btn = self.page.locator(selector).first
                if await btn.is_visible(timeout=2000):
                    cover_btn = btn
                    logger.info(f"Found cover button via selector: {selector}")
                    break

            if not cover_btn:
                logger.info("Cover button not found (non-critical)")
                return

            await cover_btn.click()
            await self._random_delay(1500, 2500)

            # Step 2: 上传竖封面（抖音竖封面预览标注 3:4，使用 1440x1920）
            if portrait:
                logger.info("Uploading vertical (portrait) cover...")
                portrait_path = await self._save_temp_image(
                    portrait, ".jpg",
                    target_width=1440, target_height=1920,
                )

                temp_files.append(portrait_path)

                # 查找竖封面上传区域 - 可能有多个 file input，第一个通常对应竖封面
                portrait_uploaded = False
                file_inputs = self.page.locator('input[type="file"]')
                count = await file_inputs.count()

                if count > 0:
                    # 尝试第一个 file input（竖封面）
                    first_input = file_inputs.first
                    portrait_uploaded = await self._upload_cover_file(first_input, portrait_path)
                    logger.info(f"Portrait cover uploaded: {portrait_uploaded}")
                else:
                    # 可能上传区域需要先点击激活
                    upload_area_selectors = [
                        '[class*="upload"]',
                        '[class*="add"]',
                        '[class*="封面"] input',
                        '.cover-upload-area',
                    ]
                    for sel in upload_area_selectors:
                        try:
                            area = self.page.locator(sel).first
                            if await area.is_visible(timeout=2000):
                                await area.click()
                                await self._random_delay(1000, 1500)
                                # 重新查找 file input
                                file_input = self.page.locator('input[type="file"]').first
                                if await file_input.is_visible(timeout=3000):
                                    portrait_uploaded = await self._upload_cover_file(
                                        file_input, portrait_path
                                    )
                                    break
                        except Exception:
                            continue

                    if not portrait_uploaded:
                        # 最后尝试直接查找所有隐藏的 file input
                        all_inputs = self.page.locator('input[type="file"]')
                        all_count = await all_inputs.count()
                        for i in range(all_count):
                            inp = all_inputs.nth(i)
                            try:
                                if await inp.is_visible(timeout=1000):
                                    portrait_uploaded = await self._upload_cover_file(
                                        inp, portrait_path
                                    )
                                    if portrait_uploaded:
                                        break
                            except Exception:
                                continue

                if portrait_uploaded:
                    logger.info("✅ Vertical cover uploaded successfully")
                    await self._random_delay(2000, 3000)
                    # 关键：抖音上传封面后会弹出裁剪对话框，必须先点击"确定"
                    # 关闭裁剪弹窗，否则后续所有操作（切换横封面、点击完成、
                    # 甚至最后的发布按钮）都会被裁剪弹窗遮挡或点击错位。
                    crop_confirmed = await self._confirm_crop_dialog(max_wait_ms=8000)
                    if crop_confirmed:
                        logger.info("✅ Portrait crop dialog confirmed")
                    await self._random_delay(1000, 1500)
                else:
                    logger.warning("Vertical cover upload may have failed")

            # Step 3: 点击"设置横封面"切换到横封面上传
            if landscape:
                logger.info("Switching to landscape cover upload...")

                landscape_clicked = await self._click_by_text(
                    ["设置横封面", "横版封面", "横封面", "横版", "landscape"],
                    timeout=3000,
                )
                if not landscape_clicked:
                    # 尝试查找其他可能有"横"字的元素
                    try:
                        hor_btn = self.page.locator('[class*="horizontal"]').first
                        if await hor_btn.is_visible(timeout=2000):
                            await hor_btn.click()
                            await self._random_delay(500, 1000)
                            landscape_clicked = True
                    except Exception:
                        pass

                if landscape_clicked:
                    await self._random_delay(1500, 2500)

                    # Step 4: 上传横封面（16:9 比例，1920x1080）
                    logger.info("Uploading horizontal (landscape) cover...")
                    landscape_path = await self._save_temp_image(
                        landscape, ".jpg",
                        target_width=1920, target_height=1080,
                    )
                    temp_files.append(landscape_path)

                    landscape_uploaded = False
                    # 切换横封面后，可能出现了新的 file input，取最后一个
                    file_inputs_after = self.page.locator('input[type="file"]')
                    count_after = await file_inputs_after.count()
                    if count_after > 0:
                        last_input = file_inputs_after.last
                        landscape_uploaded = await self._upload_cover_file(
                            last_input, landscape_path
                        )

                    if not landscape_uploaded:
                        # 尝试找到可见的 file input
                        all_inputs2 = self.page.locator('input[type="file"]')
                        all_count2 = await all_inputs2.count()
                        for i in range(all_count2):
                            inp = all_inputs2.nth(i)
                            try:
                                if await inp.is_visible(timeout=500):
                                    landscape_uploaded = await self._upload_cover_file(
                                        inp, landscape_path
                                    )
                                    if landscape_uploaded:
                                        break
                            except Exception:
                                continue

                    if landscape_uploaded:
                        logger.info("✅ Horizontal cover uploaded successfully")
                        await self._random_delay(2000, 3000)
                        # 同样：横封面上传后也可能弹出裁剪弹窗，需要点"确定"关闭
                        crop_confirmed_h = await self._confirm_crop_dialog(max_wait_ms=8000)
                        if crop_confirmed_h:
                            logger.info("✅ Landscape crop dialog confirmed")
                        await self._random_delay(1000, 1500)
                    else:
                        logger.warning("Horizontal cover upload may have failed")
                else:
                    logger.info("Landscape cover switch button not found, skipping")


            # Step 5: 点击"完成"或"确定"
            completed = await self._click_by_text(
                ["完成", "确定", "确认", "保存", "done", "confirm"],
                timeout=3000,
            )
            if completed:
                logger.info("✅ Cover settings confirmed")
                await self._random_delay(1000, 2000)
            else:
                # 尝试查找按钮类名
                try:
                    done_btn = self.page.locator(
                        '[class*="confirm"], [class*="done"], [class*="submit"]'
                    ).first
                    if await done_btn.is_visible(timeout=2000):
                        await done_btn.click()
                        await self._random_delay(1000, 1500)
                        logger.info("✅ Cover settings confirmed (by class)")
                except Exception:
                    logger.info("Cover done button not found, continuing")

            # Step 6: 强力关闭"设置封面"外层弹窗（关键步骤）
            # 裁剪弹窗关闭后，外层"设置封面"弹窗可能仍然存在，底部有"完成"按钮，
            # 必须点击"完成"关闭此弹窗，否则发布按钮会被遮挡无法点击
            await self._random_delay(1500, 2500)
            await self._close_cover_setting_dialog(max_wait_ms=8000)


        except Exception as e:
            logger.warning(f"Set cover failed (non-critical): {e}")
        finally:
            # 清理临时文件
            for f in temp_files:
                try:
                    if os.path.exists(f):
                        os.unlink(f)
                except Exception:
                    pass

    async def _close_cover_setting_dialog(self, max_wait_ms: int = 10000) -> bool:
        """关闭"设置封面"外层弹窗

        裁剪弹窗内的"保存"按钮关闭裁剪弹窗后，外层"设置封面"弹窗仍然显示在页面上，
        其底部有"完成"按钮。必须点击这个"完成"按钮关闭外层弹窗，
        否则发布按钮会被遮挡而无法点击。

        本方法使用 JS 在浏览器端强力处理：
        策略 A: 查找包含"封面"/"cover"且有"完成"按钮的 dialog/modal → 点击"完成"
        策略 B: 查找任意可见的、含"完成"按钮的顶层 dialog/modal（兜底）
        策略 C: 直接查找页面上任意"完成"按钮并点击

        Args:
            max_wait_ms: 最长等待时间(ms)

        Returns:
            是否成功关闭弹窗（未检测到弹窗也返回 True）
        """
        if not self.page:
            return True

        js_result = await self.page.evaluate(
            """
            async ({ maxWaitMs }) => {
                function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

                function isVisible(el) {
                    if (!el) return false;
                    try {
                        const rect = el.getBoundingClientRect();
                        if (rect.width < 30 || rect.height < 30) return false;
                        const style = window.getComputedStyle(el);
                        if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
                        return true;
                    } catch (e) { return false; }
                }

                // 查找所有弹窗容器（按 z-index 降序排列，取最顶层）
                function getAllDialogs() {
                    const selectors = [
                        '[role="dialog"]', '[role="presentation"]',
                        '[class*="dialog"]', '[class*="Dialog"]',
                        '[class*="modal"]', '[class*="Modal"]',
                        '[class*="popup"]', '[class*="Popup"]',
                        '[class*="overlay"]', '[class*="Overlay"]',
                        '.ant-modal', '.el-dialog', '.el-overlay',
                    ];
                    const result = [];
                    for (const sel of selectors) {
                        try {
                            const els = document.querySelectorAll(sel);
                            for (const el of els) {
                                if (!isVisible(el)) continue;
                                const z = parseInt(window.getComputedStyle(el).zIndex) || 0;
                                result.push({ el, z });
                            }
                        } catch (e) {}
                    }
                    // 去重
                    const seen = new Set();
                    const unique = [];
                    for (const item of result) {
                        const key = item.el.tagName + '-' + (item.el.className || '');
                        if (!seen.has(key)) { seen.add(key); unique.push(item); }
                    }
                    unique.sort((a, b) => b.z - a.z);  // z-index 降序
                    return unique.map(item => item.el);
                }

                // 查找弹窗中指定文本的按钮
                function findButtonInDialog(dialog, text) {
                    const btns = dialog.querySelectorAll('button, div[role="button"], a[role="button"]');
                    for (const b of btns) {
                        try {
                            const t = (b.textContent || '').trim();
                            if (t === text && !b.disabled) {
                                const cls = (b.className || '').toLowerCase();
                                if (!cls.includes('disabled')) return b;
                            }
                        } catch (e) {}
                    }
                    return null;
                }

                // ====== 策略 A: 查找包含"封面"文字且有"完成"按钮的弹窗 ======
                const start = Date.now();
                let clickedAny = false;

                while (Date.now() - start < maxWaitMs) {
                    const dialogs = getAllDialogs();
                    for (const dialog of dialogs) {
                        try {
                            const text = (dialog.textContent || '').toLowerCase();
                            // 策略 A1: 包含"封面"且包含"完成"按钮
                            if (text.includes('封面') || text.includes('cover')) {
                                const finishBtn = findButtonInDialog(dialog, '完成');
                                if (finishBtn) {
                                    finishBtn.click();
                                    clickedAny = true;
                                    await sleep(2000);
                                    // 检查是否关闭了
                                    if (!isVisible(dialog)) {
                                        return { success: true, strategy: 'A1', dialogText: text.substring(0, 50) };
                                    }
                                }
                            }
                        } catch (e) {}
                    }

                    // 策略 A2: 如果露出来的 dialog 不多，直接找"完成"按钮
                    if (dialogs.length > 0 && dialogs.length <= 3) {
                        for (const dialog of dialogs) {
                            const finishBtn = findButtonInDialog(dialog, '完成');
                            if (finishBtn) {
                                finishBtn.click();
                                clickedAny = true;
                                await sleep(2000);
                                if (!isVisible(dialog)) {
                                    return { success: true, strategy: 'A2' };
                                }
                            }
                        }
                    }

                    await sleep(300);
                }

                // ====== 策略 B: 兜底 - 直接点"完成"按钮 ======
                if (!clickedAny) {
                    const allButtons = document.querySelectorAll('button');
                    for (const b of allButtons) {
                        try {
                            if ((b.textContent || '').trim() === '完成' && !b.disabled && isVisible(b)) {
                                // 检查是否在弹窗内
                                let parent = b.parentElement;
                                let inDialog = false;
                                while (parent) {
                                    const pCls = (parent.className || '').toLowerCase();
                                    if (pCls.includes('dialog') || pCls.includes('modal') || pCls.includes('popup') || pCls.includes('overlay')) {
                                        inDialog = true; break;
                                    }
                                    parent = parent.parentElement;
                                }
                                if (inDialog) {
                                    b.click();
                                    await sleep(2000);
                                    return { success: true, strategy: 'B' };
                                }
                            }
                        } catch (e) {}
                    }
                }

                return { success: false, clickedAny };
            }
            """,
            {"maxWaitMs": max_wait_ms},
        )

        if not js_result:
            logger.info("No JS result from cover dialog close")
            return True

        if js_result.get("success"):
            strategy = js_result.get("strategy", "?")
            logger.info(f"✅ Cover setting dialog closed (strategy: {strategy})")
            await self._random_delay(1000, 1500)
            return True

        logger.info("No cover setting dialog detected, continuing")
        return True

    async def _click_publish(self):
        """点击发布按钮并等待成功

        改进版本：
        1. 点击发布前，先关闭任何遗留的裁剪/编辑弹窗，避免遮挡发布按钮
        2. 精确匹配"发布"文本按钮，避免误点"发"开头的其他按钮
        3. 检查发布按钮是否处于 disabled 状态（表单未通过校验），若是则报错
        4. 点击后必须检测到真正的成功信号（成功文案 / URL 跳转 / 落到管理页），
           否则报错，不再打"可能成功"的模糊信息
        """
        if not self.page:
            return

        try:
            # 点击发布前，兜底再清理一次可能残留的弹窗
            try:
                await self._confirm_crop_dialog(max_wait_ms=1500)
            except Exception:
                pass
            try:
                await self._close_cover_setting_dialog(max_wait_ms=3000)
            except Exception:
                pass

            # 记录点击前 URL，便于后续判断是否跳转
            url_before = self.page.url

            # 精确匹配"发布"按钮 —— 使用 name 精确匹配的 role 定位器，
            # 避免误匹配"发送"、"发起"等按钮
            publish_btn = None
            try:
                exact_btn = self.page.get_by_role("button", name="发布", exact=True).first
                if await exact_btn.is_visible(timeout=2000):
                    publish_btn = exact_btn
                    logger.info("Found publish button via role=button name='发布' (exact)")
            except Exception:
                pass

            if not publish_btn:
                # 兜底选择器（保持向后兼容）
                publish_selectors = [
                    'button:has-text("发布"):not(:has-text("发布视频"))',
                    'button:text-is("发布")',
                    'button:has-text("发布")',
                    '.publish-btn',
                    '[class*="publish"] button',
                    'button[class*="publish"]',
                    'div[class*="publish"] button',
                ]
                for selector in publish_selectors:
                    try:
                        btn = self.page.locator(selector).first
                        if await btn.is_visible(timeout=1500):
                            publish_btn = btn
                            logger.info(f"Found publish button with selector: {selector}")
                            break
                    except Exception:
                        continue

            if not publish_btn:
                logger.warning("Publish button not found with any selector")
                html_snippet = await self.page.content()
                logger.debug(f"Page HTML snippet (first 2000 chars): {html_snippet[:2000]}")
                raise Exception("未找到发布按钮")

            # 检查发布按钮是否可用（未被禁用）
            # 抖音在封面未确认、必填项未填时会把发布按钮设为 disabled
            try:
                is_disabled_attr = await publish_btn.get_attribute("disabled")
                aria_disabled = await publish_btn.get_attribute("aria-disabled")
                cls = (await publish_btn.get_attribute("class")) or ""
                disabled_by_class = any(
                    kw in cls.lower() for kw in ["disabled", "is-disabled", "disable"]
                )

                if (
                    is_disabled_attr is not None
                    or (aria_disabled and aria_disabled.lower() == "true")
                    or disabled_by_class
                ):
                    # 再等一下（可能是校验中），然后重试
                    logger.warning(
                        f"Publish button seems disabled "
                        f"(disabled={is_disabled_attr}, aria-disabled={aria_disabled}, "
                        f"class={cls}). Waiting 3s and retrying check..."
                    )
                    await self.page.wait_for_timeout(3000)
                    is_disabled_attr = await publish_btn.get_attribute("disabled")
                    aria_disabled = await publish_btn.get_attribute("aria-disabled")
                    cls = (await publish_btn.get_attribute("class")) or ""
                    disabled_by_class = any(
                        kw in cls.lower() for kw in ["disabled", "is-disabled", "disable"]
                    )
                    if (
                        is_disabled_attr is not None
                        or (aria_disabled and aria_disabled.lower() == "true")
                        or disabled_by_class
                    ):
                        raise Exception(
                            "发布按钮处于不可用状态，可能是封面未确认或必填项未通过校验"
                        )
            except Exception as check_err:
                # 如果是我们主动 raise 的，就直接抛出
                if "发布按钮处于不可用状态" in str(check_err):
                    raise

            # 点击发布
            await publish_btn.click()
            logger.info("🚀 Publish button clicked")

            # 等待发布结果 —— 检测以下任一信号即视为成功：
            # 1. 出现"发布成功"文案
            # 2. URL 跳转到作品管理页(/creator-micro/content/manage) 或 /video/ /work/
            # 3. 页面出现"作品发布成功"toast/dialog
            await self.page.wait_for_timeout(2000)

            success_signals_detected = False
            for i in range(60):  # 最多等 60 秒
                current_url = self.page.url

                # 信号 1: URL 已跳转到作品管理页面（抖音发布成功后的常见跳转）
                if current_url != url_before and any(
                    kw in current_url
                    for kw in ["/content/manage", "/video/", "/work/", "/manage"]
                ):
                    self._platform_url = current_url
                    logger.info(f"✅ Published! Redirected to: {current_url}")
                    success_signals_detected = True
                    return

                # 信号 2: 页面上出现成功文案
                try:
                    success_text = self.page.locator(
                        'text=发布成功, text=作品已发布, text=视频发布成功, '
                        'text=发布中, text=正在发布'
                    ).first
                    if await success_text.is_visible(timeout=500):
                        # 出现"发布中"也算发起了发布流程，继续等待跳转
                        content = (await success_text.text_content() or "").strip()
                        if any(kw in content for kw in ["成功", "已发布"]):
                            self._platform_url = self.page.url
                            logger.info(
                                f"✅ Published successfully! Text: {content}, "
                                f"URL: {self._platform_url}"
                            )
                            success_signals_detected = True
                            return
                except Exception:
                    pass

                await self.page.wait_for_timeout(1000)

            if not success_signals_detected:
                # 检查是否有错误/提示信息
                error_text = ""
                try:
                    err_locator = self.page.locator(
                        '[class*="error"], [class*="Error"], [class*="warning"], '
                        '[class*="Message"], [class*="toast"]'
                    ).first
                    if await err_locator.is_visible(timeout=500):
                        error_text = (await err_locator.text_content() or "").strip()
                except Exception:
                    pass
                raise Exception(
                    f"发布未确认成功：60秒内未检测到跳转或成功提示 "
                    f"(page url: {self.page.url}, error hint: {error_text or 'N/A'})"
                )

        except Exception as e:
            logger.error(f"Click publish failed: {e}")
            raise


