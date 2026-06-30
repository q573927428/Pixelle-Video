"""
快手发布器

实现快手创作者平台的视频自动发布流程。
"""

from loguru import logger
from pixelle_video.services.publisher.publisher_base import BasePublisher


class KuaishouPublisher(BasePublisher):
    """快手发布器"""

    PLATFORM_NAME = "快手"
    CREATOR_URL = "https://creator.kuaishou.com/publish"
    UPLOAD_URL = "https://creator.kuaishou.com/publish"

    async def _upload_video(self, video_path: str):
        """上传视频到快手"""
        if not self.page:
            return
        try:
            file_input = self.page.locator('input[type="file"]').first
            if await file_input.is_visible(timeout=10000):
                await file_input.set_input_files(video_path)
                logger.info(f"📤 Video file selected: {video_path}")
                # 等待上传完成
                await self.page.wait_for_timeout(5000)
                for _ in range(180):
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
        """填写标题、文案和话题"""
        if not self.page:
            return
        try:
            if title:
                title_input = self.page.locator('.title-input input, [placeholder*="标题"]').first
                if await title_input.is_visible(timeout=5000):
                    await title_input.click()
                    await self._random_delay()
                    await title_input.fill(title)

            full_text = text
            if topics:
                topics_str = " ".join([f"#{t.replace('#', '')}" for t in topics])
                full_text = f"{text}\n{topics_str}" if text else topics_str

            if full_text:
                desc_input = self.page.locator('.desc-textarea textarea, [placeholder*="文案"]').first
                if await desc_input.is_visible(timeout=5000):
                    await desc_input.click()
                    await self._random_delay()
                    await desc_input.fill(full_text)
                    logger.info("✅ Description filled")
        except Exception as e:
            logger.error(f"Fill metadata failed: {e}")
            raise

    async def _set_cover(self, portrait: str, landscape: str):
        """设置封面

        快手支持从视频中选帧，暂不实现自定义封面上传。
        Args:
            portrait: 竖屏封面 base64
            landscape: 横屏封面 base64
        """
        logger.info("ℹ️ Kuaishou: auto frame selection, custom cover not implemented")

    async def _click_publish(self):
        """点击发布按钮"""
        if not self.page:
            return
        try:
            publish_btn = self.page.locator('button:has-text("发布")').first
            if await publish_btn.is_visible(timeout=5000):
                await publish_btn.click()
                logger.info("🚀 Publish button clicked")
                await self.page.wait_for_timeout(5000)
                # 等待成功确认
                for _ in range(60):
                    if await self.page.locator('text=发布成功').first.is_visible(timeout=1000):
                        self._platform_url = self.page.url
                        logger.info(f"✅ Published successfully!")
                        return
                    await self.page.wait_for_timeout(1000)
            else:
                raise Exception("未找到发布按钮")
        except Exception as e:
            logger.error(f"Click publish failed: {e}")
            raise
