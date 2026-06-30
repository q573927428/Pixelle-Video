"""
抖音发布器

实现抖音创作者平台的视频自动发布流程。
"""

import asyncio
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
                # 尝试获取账户名称
                account_name = None
                try:
                    name_el = self.page.locator(
                        '.user-name, [class*="nickname"], [class*="user-name"], '
                        '.creator-header .name, .avatar-container .name'
                    ).first
                    if await name_el.is_visible(timeout=3000):
                        account_name = await name_el.text_content()
                except Exception:
                    pass

                await cookie_manager.save(
                    user_id=self.session.user_id,
                    platform=self.PLATFORM_NAME,
                    cookies=cookies,
                    account_name=account_name or f"{self.PLATFORM_NAME}用户",
                )
                logger.info(f"✅ Cookies saved for {self.PLATFORM_NAME}")
        except Exception as e:
            logger.warning(f"Save cookies failed: {e}")

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
            full_text = self.params.full_text if hasattr(self, 'params') else text
            if topics:
                topics_str = " ".join(topics)
                if full_text:
                    full_text = f"{full_text}\n{topics_str}"
                else:
                    full_text = topics_str

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
        min_width: int = 1080,
        min_height: int = 1920,
        quality: int = 95,
    ) -> str:
        """将 base64 图片保存为临时文件，确保分辨率满足最低要求

        抖音封面推荐标准:
        - 竖屏封面: 9:16 比例，至少 1080x1920
        - 横屏封面: 16:9 比例，至少 1920x1080

        图片处理策略:
        1. 如果原始分辨率已满足最低要求，直接保存（不破坏画质）
        2. 如果分辨率不足，按原始宽高比缩放至满足最低要求
        3. 不裁剪图片，保持完整内容

        Args:
            base64_str: base64 图片数据（data:image/... 格式或裸 base64）
            suffix: 文件后缀
            min_width: 最小宽度
            min_height: 最小高度
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

        # 打开图片检查分辨率
        try:
            img = Image.open(io.BytesIO(img_data))
            width, height = img.size

            if width >= min_width and height >= min_height:
                # 尺寸已满足要求，直接保存
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
                    f.write(img_data)
                    return f.name

            logger.info(
                f"Image too small: {width}x{height}, "
                f"upscaling to at least {min_width}x{min_height} "
                f"(preserving original aspect ratio {width/height:.2f})..."
            )

            # 计算保持原始宽高比的最小缩放比例
            ratio = max(min_width / width, min_height / height)
            new_width = int(width * ratio) + 1  # +1 确保严格大于最小值
            new_height = int(height * ratio) + 1

            # 使用高质量的 Lanczos 重采样
            img = img.resize((new_width, new_height), Image.LANCZOS)

            logger.info(f"Image upscaled from {width}x{height} to {new_width}x{new_height}")

            # 保存到临时文件
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
                save_format = "JPEG" if suffix.lower() in (".jpg", ".jpeg") else "PNG"
                img.save(f, format=save_format, quality=quality)
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

            # Step 2: 上传竖封面（9:16 比例，至少 1080x1920）
            if portrait:
                logger.info("Uploading vertical (portrait) cover...")
                portrait_path = await self._save_temp_image(
                    portrait, ".jpg",
                    min_width=1080, min_height=1920,
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

                    # Step 4: 上传横封面（16:9 比例，至少 1920x1080）
                    logger.info("Uploading horizontal (landscape) cover...")
                    landscape_path = await self._save_temp_image(
                        landscape, ".jpg",
                        min_width=1920, min_height=1080,
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

            # Step 6: 处理可能再次弹出的"设置封面"弹窗，需要点击"完成"关闭
            await self._random_delay(1500, 2500)
            try:
                # 检测是否又有设置封面弹窗弹出
                cover_popup_selectors = [
                    '[class*="cover"] [class*="dialog"]',
                    '[class*="cover"] [class*="modal"]',
                    '[class*="cover"] [class*="popup"]',
                    'div[class*="cover"]:has(button:has-text("完成"))',
                    'div[class*="cover"]:has(button:has-text("保存"))',
                ]
                has_cover_popup = False
                for selector in cover_popup_selectors:
                    popup = self.page.locator(selector).first
                    if await popup.is_visible(timeout=1500):
                        has_cover_popup = True
                        logger.info(f"Detected secondary cover popup via selector: {selector}")
                        break

                if not has_cover_popup:
                    # 更通用的检测：查找可见的"完成"或"保存"按钮，但排除页面上已有的主操作区
                    finish_btn = self.page.locator(
                        'button:has-text("完成"), button:has-text("保存")'
                    ).first
                    if await finish_btn.is_visible(timeout=1000):
                        # 检查是否在弹窗/对话框上下文中
                        parent_dialog = finish_btn.locator(
                            'xpath=ancestor::div[contains(@class, "dialog") or contains(@class, "modal") or contains(@class, "popup") or contains(@class, "cover")]'
                        )
                        if await parent_dialog.count() > 0:
                            has_cover_popup = True
                            logger.info("Detected secondary cover popup via finish button in dialog context")

                if has_cover_popup:
                    # 点击弹窗中的"完成"按钮
                    second_completed = await self._click_by_text(
                        ["完成", "保存", "确定", "确认"],
                        timeout=3000,
                    )
                    if second_completed:
                        logger.info("✅ Secondary cover popup dismissed")
                        await self._random_delay(1000, 2000)
                    else:
                        # 尝试直接点击弹窗中的按钮
                        try:
                            btn = self.page.locator(
                                '[class*="dialog"] button:has-text("完成"), '
                                '[class*="modal"] button:has-text("完成"), '
                                '[class*="popup"] button:has-text("完成"), '
                                '[class*="dialog"] button:has-text("保存"), '
                                '[class*="modal"] button:has-text("保存")'
                            ).first
                            if await btn.is_visible(timeout=2000):
                                await btn.click()
                                await self._random_delay(1000, 1500)
                                logger.info("✅ Secondary cover popup dismissed (by class)")
                        except Exception:
                            logger.info("Secondary cover popup finish button not found, continuing")
            except Exception as e:
                logger.info(f"Secondary cover popup handling (non-critical): {e}")

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

    async def _click_publish(self):
        """点击发布按钮并等待成功"""
        if not self.page:
            return

        try:
            # 抖音的发布按钮有多种可能的选择器
            publish_selectors = [
                'button:has-text("发布")',
                '.publish-btn',
                '[class*="publish"] button',
                'button[class*="publish"]',
                'div[class*="publish"] button',
                # 包含"发"字的按钮
                'button:has-text("发")',
            ]

            publish_btn = None
            for selector in publish_selectors:
                btn = self.page.locator(selector).first
                if await btn.is_visible(timeout=2000):
                    publish_btn = btn
                    logger.info(f"Found publish button with selector: {selector}")
                    break

            if publish_btn:
                await publish_btn.click()
                logger.info("🚀 Publish button clicked")

                # 等待发布完成（检测成功提示或跳转）
                await self.page.wait_for_timeout(5000)
                for _ in range(60):
                    success_text = self.page.locator(
                        'text=发布成功, text=作品已发布, text=视频发布成功'
                    ).first
                    if await success_text.is_visible(timeout=1000):
                        self._platform_url = self.page.url
                        logger.info(f"✅ Published successfully! URL: {self._platform_url}")
                        return
                    current_url = self.page.url
                    if "/video/" in current_url or "/work/" in current_url:
                        self._platform_url = current_url
                        logger.info(f"✅ Published! Redirected to: {current_url}")
                        return
                    await self.page.wait_for_timeout(1000)
                logger.warning("Publish confirmation not detected, but may have succeeded")
            else:
                logger.warning("Publish button not found with any selector")
                # 打印页面内容帮助调试
                html_snippet = await self.page.content()
                logger.debug(f"Page HTML snippet (first 2000 chars): {html_snippet[:2000]}")
                raise Exception("未找到发布按钮")
        except Exception as e:
            logger.error(f"Click publish failed: {e}")
            raise