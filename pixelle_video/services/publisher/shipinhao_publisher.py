"""
视频号发布器

实现微信视频号（微信创作者平台）的视频自动发布流程。
"""

from loguru import logger
from pixelle_video.services.publisher.publisher_base import BasePublisher


class ShipinhaoPublisher(BasePublisher):
    """视频号发布器"""

    PLATFORM_NAME = "视频号"
    CREATOR_URL = "https://channels.weixin.qq.com/platform/post"
    UPLOAD_URL = "https://channels.weixin.qq.com/platform/post"

    async def _upload_video(self, video_path: str):
        """上传视频到视频号"""
        if not self.page:
            return
        try:
            file_input = self.page.locator('input[type="file"]').first
            if await file_input.is_visible(timeout=10000):
                await file_input.set_input_files(video_path)
                logger.info(f"📤 Video file selected: {video_path}")
                await self.page.wait_for_timeout(5000)
                for _ in range(300):  # 视频号上传可能较慢，等待 5 分钟
                    progress = self.page.locator(".upload-progress, .progress-bar").first
                    if not await progress.is_visible(timeout=1000):
                        break
                    await self.page.wait_for_timeout(1000)
                logger.info("✅ Video upload complete")
            else:
                raise Exception("未找到文件上传入口")
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            raise

    async def _fill_metadata(self, title: str, text: str, topics: list):
        """填写标题和话题

        视频号只有标题，无独立文案区。
        话题在标题末尾追加 #话题 格式。
        """
        if not self.page:
            return
        try:
            # 视频号标题
            full_title = title
            if topics:
                topics_str = " ".join([f"#{t.replace('#', '')}" for t in topics])
                full_title = f"{title} {topics_str}" if title else topics_str

            if full_title:
                title_input = self.page.locator('[placeholder*="标题"], .title-input input').first
                if await title_input.is_visible(timeout=5000):
                    await title_input.click()
                    await self._random_delay()
                    await title_input.fill(full_title)
                    logger.info(f"✅ Title filled: {full_title}")
        except Exception as e:
            logger.error(f"Fill metadata failed: {e}")
            raise

    async def _set_cover(self, portrait: str, landscape: str):
        """设置封面

        视频号支持从视频中选帧或上传自定义封面，暂不实现。
        Args:
            portrait: 竖屏封面 base64
            landscape: 横屏封面 base64
        """
        logger.info("ℹ️ Shipinhao: auto frame selection, custom cover not implemented")

    async def _click_publish(self):
        """点击发表按钮"""
        if not self.page:
            return
        try:
            publish_btn = self.page.locator('button:has-text("发表")').first
            if await publish_btn.is_visible(timeout=5000):
                await publish_btn.click()
                logger.info("🚀 Publish button clicked")
                await self.page.wait_for_timeout(5000)
                for _ in range(60):
                    if await self.page.locator('text=发表成功').first.is_visible(timeout=1000):
                        self._platform_url = self.page.url
                        logger.info(f"✅ Published successfully!")
                        return
                    await self.page.wait_for_timeout(1000)
            else:
                raise Exception("未找到发表按钮")
        except Exception as e:
            logger.error(f"Click publish failed: {e}")
            raise
