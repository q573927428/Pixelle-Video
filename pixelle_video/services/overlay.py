"""
视频叠加层服务 (Video Overlay Service)

为数字口播视频添加标题叠加、个人名片等视觉元素。
使用 Pillow 生成 PNG 帧图像，通过 FFmpeg overlay 叠加到视频上。
"""

from __future__ import annotations

import json
import math
import os
import uuid
from typing import TYPE_CHECKING, Any, Optional, List, Tuple

from loguru import logger

if TYPE_CHECKING:
    from PIL import Image, ImageDraw, ImageFont
else:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        Image = ImageDraw = ImageFont = None  # type: ignore


class TitleOverlayConfig:
    """标题叠加配置"""
    def __init__(
        self,
        enabled: bool = False,
        text: str = "",
        font_size: int = 56,
        font_color: str = "#FFFFFF",
        font_weight: int = 700,
        position_x: int = 0,
        position_y: int = -800,
        max_width: int = 900,
        font_border_width: int = 2,
        font_border_color: str = "#000000",
        text_align: str = "center",
        display_mode: str = "full",
        duration_seconds: int = 5,
    ):
        self.enabled = enabled
        self.text = text
        self.font_size = font_size
        self.font_color = font_color
        self.font_weight = font_weight
        self.position_x = position_x
        self.position_y = position_y
        self.max_width = max_width
        self.font_border_width = font_border_width
        self.font_border_color = font_border_color
        self.text_align = text_align
        self.display_mode = display_mode
        self.duration_seconds = duration_seconds

    @classmethod
    def from_dict(cls, d: dict) -> "TitleOverlayConfig":
        return cls(
            enabled=d.get("enabled", False),
            text=d.get("text", ""),
            font_size=d.get("font_size", 56),
            font_color=d.get("font_color", "#FFFFFF"),
            font_weight=d.get("font_weight", 700),
            position_x=d.get("position_x", 0),
            position_y=d.get("position_y", -800),
            max_width=d.get("max_width", 900),
            font_border_width=d.get("font_border_width", 1),
            font_border_color=d.get("font_border_color", "#000000"),
            text_align=d.get("text_align", "center"),
            display_mode=d.get("display_mode", "full"),
            duration_seconds=d.get("duration_seconds", 5),
        )


class BusinessCardConfig:
    """个人名片配置"""
    def __init__(
        self,
        enabled: bool = False,
        title: str = "",
        subtitle: str = "",
        display_mode: str = "full",
        duration_seconds: int = 5,
    ):
        self.enabled = enabled
        self.title = title
        self.subtitle = subtitle
        self.display_mode = display_mode
        self.duration_seconds = duration_seconds

    @classmethod
    def from_dict(cls, d: dict) -> "BusinessCardConfig":
        return cls(
            enabled=d.get("enabled", False),
            title=d.get("title", ""),
            subtitle=d.get("subtitle", ""),
            display_mode=d.get("display_mode", "full"),
            duration_seconds=d.get("duration_seconds", 5),
        )


class BgmOverlayConfig:
    """背景音乐配置"""
    def __init__(
        self,
        enabled: bool = False,
        selected_bgm: Optional[str] = None,
        volume: int = 50,
        custom_bgm: Optional[str] = None,
    ):
        self.enabled = enabled
        self.selected_bgm = selected_bgm
        self.volume = volume
        self.custom_bgm = custom_bgm

    @classmethod
    def from_dict(cls, d: dict) -> "BgmOverlayConfig":
        return cls(
            enabled=d.get("enabled", False),
            selected_bgm=d.get("selected_bgm"),
            volume=d.get("volume", 50),
            custom_bgm=d.get("custom_bgm"),
        )


class OverlayService:
    """
    视频叠加层服务
    使用 Pillow 生成标题/名片叠加帧，通过 FFmpeg overlay 叠加到视频
    """

    # 共享字体搜索路径（与 SubtitleService 保持一致）
    DEFAULT_FONT_PATHS = [
        "/usr/share/fonts/chinese/NotoSansSC-Bold.otf",
        "/usr/share/fonts/chinese/NotoSansSC-Regular.otf",
        "C:/Windows/Fonts/NotoSansSC-Bold.otf",
        "C:/Windows/Fonts/NotoSansSC-Regular.otf",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/msyhbd.ttc",
        "C:/Windows/Fonts/msyh.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc",
    ]

    def __init__(self):
        if Image is None:
            raise ImportError("Pillow (PIL) is required for overlay service. pip install Pillow")
        self._font_path = self._find_font()

    def _find_font(self) -> str:
        for path in self.DEFAULT_FONT_PATHS:
            if os.path.exists(path):
                logger.info(f"[Overlay] Using font: {path}")
                return path
        # fallback fc-match
        try:
            import subprocess
            result = subprocess.run(
                ["fc-match", "-f", "%{file}", "sans-serif"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                font_path = result.stdout.strip()
                if os.path.exists(font_path):
                    return font_path
        except Exception:
            pass
        raise FileNotFoundError("No Chinese font found for OverlayService")

    def _hex_to_rgba(self, hex_color: str, alpha: int = 255) -> tuple[int, int, int, int]:
        h = hex_color.lstrip("#")
        if len(h) >= 6:
            return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha)
        return (255, 255, 255, alpha)

    def _draw_rounded_rect(
        self,
        draw: Any,
        xy: tuple[int, int, int, int],
        radius: int,
        fill: tuple[int, int, int, int],
    ):
        """绘制圆角矩形"""
        x1, y1, x2, y2 = xy
        diameter = radius * 2
        draw.rectangle((x1 + radius, y1, x2 - radius, y2), fill=fill)
        draw.rectangle((x1, y1 + radius, x2, y2 - radius), fill=fill)
        draw.ellipse((x1, y1, x1 + diameter, y1 + diameter), fill=fill)
        draw.ellipse((x2 - diameter, y1, x2, y1 + diameter), fill=fill)
        draw.ellipse((x1, y2 - diameter, x1 + diameter, y2), fill=fill)
        draw.ellipse((x2 - diameter, y2 - diameter, x2, y2), fill=fill)

    def _split_text_into_lines(
        self, text: str, font: Any, max_width: int
    ) -> List[str]:
        """
        将文本按最大宽度分割成多行
        - 优先按换行符分割
        - 超出宽度则强制截断
        """
        # 先按换行符分割
        raw_lines = text.split('\n')
        result_lines: List[str] = []
        for line in raw_lines:
            if not line.strip():
                if line == '':
                    continue
                result_lines.append(line)
                continue
            # 如果单行宽度不超过 max_width，直接添加
            if font.getlength(line) <= max_width:
                result_lines.append(line)
            else:
                # 按字符拆分
                current_line = ""
                for char in line:
                    test_line = current_line + char
                    if font.getlength(test_line) > max_width and current_line:
                        result_lines.append(current_line)
                        current_line = char
                    else:
                        current_line = test_line
                if current_line:
                    result_lines.append(current_line)
        return result_lines

    def generate_title_overlay_frames(
        self,
        config: TitleOverlayConfig,
        video_width: int,
        video_height: int,
        output_dir: str,
        fps: int = 30,
        video_duration: float = 10.0,
    ) -> Optional[str]:
        """
        生成标题叠加帧图像（PNG 序列）
        支持：多行文字（\\n 分割）、文字边框（粗细+颜色）、最大宽度自动换行
        返回帧目录路径，或 None（配置禁用/文字为空）
        """
        if not config.enabled or not config.text:
            return None

        frames_dir = os.path.join(output_dir, "title_overlay_frames")
        os.makedirs(frames_dir, exist_ok=True)

        font_size = int(config.font_size * video_width / 1080)
        try:
            font = ImageFont.truetype(self._font_path, font_size)
        except Exception:
            font = ImageFont.load_default()

        fg_color = self._hex_to_rgba(config.font_color)
        border_color = self._hex_to_rgba(config.font_border_color) if config.font_border_width > 0 else None
        border_width = max(0, config.font_border_width)

        # 计算缩放比例
        scale = video_width / 1080

        # 将文本分割为行（支持多行 + 自动换行）
        max_width_px = int(config.max_width * scale)
        lines = self._split_text_into_lines(config.text, font, max_width_px)

        if not lines:
            return None

        # 获取字体 metrics
        ascent, descent = font.getmetrics()
        line_height = ascent + descent

        # 计算最大行宽
        line_widths = [int(font.getlength(line)) for line in lines]
        max_line_width = max(line_widths) if line_widths else 0

        # 背景内边距
        pad = int(15 * scale)
        bg_width = max_line_width + pad * 2
        bg_height = len(lines) * line_height + pad * 2

        # 位置
        offset_x = int(config.position_x * scale)
        offset_y = int(config.position_y * scale)
        center_x = video_width // 2 + offset_x
        center_y = video_height + offset_y if offset_y < 0 else offset_y

        # 背景区域
        bg_x = center_x - bg_width // 2
        bg_y = center_y - bg_height // 2

        # 显示时长
        effective_duration = max(video_duration, 0.1)
        if config.display_mode == "duration":
            display_frames = int(config.duration_seconds * fps)
            logger.info(f"[Overlay - 标题] display_mode=duration, duration_seconds={config.duration_seconds}s")
        else:
            display_frames = int(effective_duration * fps)
            logger.info(f"[Overlay - 标题] display_mode=full, video_duration={effective_duration:.2f}s")
        display_frames = max(display_frames, 1)

        # 生成单帧图像
        img = Image.new("RGBA", (video_width, video_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # 绘制半透明背景
        radius = min(int(8 * scale), bg_height // 2, bg_width // 2)
        self._draw_rounded_rect(
            draw,
            (bg_x, bg_y, bg_x + bg_width, bg_y + bg_height),
            radius,
            (0, 0, 0, 128),  # 半透明黑色
        )

        # 逐行绘制文字（带边框，支持对齐方式）
        text_align = getattr(config, 'text_align', 'center')
        y_correction = (ascent + descent - config.font_size) / 2
        for i, line in enumerate(lines):
            line_width = int(font.getlength(line))
            if text_align == 'left':
                text_x = bg_x + pad
            elif text_align == 'right':
                text_x = bg_x + bg_width - line_width - pad
            else:
                text_x = bg_x + (bg_width - line_width) // 2
            text_y = bg_y + pad + line_height // 2 + i * line_height + y_correction

            if border_color and border_width > 0:
                draw.text(
                    (text_x, text_y), line, fill=fg_color, font=font,
                    anchor='lm', stroke_width=border_width, stroke_fill=border_color,
                )
            else:
                draw.text(
                    (text_x, text_y), line, fill=fg_color, font=font,
                    anchor='lm',
                )

        # 保存单帧
        frame_filename = f"title_{uuid.uuid4().hex[:8]}_000000.png"
        frame_path = os.path.join(frames_dir, frame_filename)
        img.save(frame_path, "PNG")

        display_seconds = display_frames / fps

        # 保存元数据
        metadata = {
            "video_width": video_width,
            "video_height": video_height,
            "fps": fps,
            "frames": [
                {
                    "path": os.path.join(frames_dir, frame_filename),
                    "frame": 0,
                    "start_frame": 0,
                    "end_frame": display_frames,
                    "start_time": 0.0,
                    "end_time": display_seconds,
                }
            ],
        }
        with open(os.path.join(frames_dir, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        logger.info(f"[Overlay] Generated 1 title overlay frame (duration={display_seconds:.1f}s) in {frames_dir}")
        return frames_dir

    def generate_business_card_frames(
        self,
        config: BusinessCardConfig,
        video_width: int,
        video_height: int,
        output_dir: str,
        fps: int = 30,
        video_duration: float = 10.0,
    ) -> Optional[str]:
        """
        生成个人名片叠加帧图像（PNG 序列）
        返回帧目录路径，或 None
        """
        if not config.enabled or not config.title:
            return None

        frames_dir = os.path.join(output_dir, "business_card_frames")
        os.makedirs(frames_dir, exist_ok=True)

        scale = video_width / 1080

        # 卡片尺寸
        card_w = int(380 * scale)
        card_h = int(160 * scale) if config.subtitle else int(100 * scale)

        # 位置：左侧中间靠下（与前端保持一致）
        card_x = int(20 * scale)
        card_y = int(video_height * 0.65 - card_h / 2)

        # 字体
        title_font_size = int(24 * scale)
        sub_font_size = int(18 * scale)
        avatar_size = int(70 * scale)

        try:
            title_font = ImageFont.truetype(self._font_path, title_font_size)
            sub_font = ImageFont.truetype(self._font_path, sub_font_size)
        except Exception:
            title_font = ImageFont.load_default()
            sub_font = ImageFont.load_default()

        # 显示时长
        effective_duration = max(video_duration, 0.1)
        if config.display_mode == "duration":
            display_frames = int(config.duration_seconds * fps)
            logger.info(f"[Overlay - 名片] display_mode=duration, duration_seconds={config.duration_seconds}s")
        else:
            display_frames = int(effective_duration * fps)
            logger.info(f"[Overlay - 名片] display_mode=full, video_duration={effective_duration:.2f}s")
        display_frames = max(display_frames, 1)

        # 生成帧
        img = Image.new("RGBA", (video_width, video_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # 半透明圆角背景
        radius = int(16 * scale)
        draw.rounded_rectangle(
            (card_x, card_y, card_x + card_w, card_y + card_h),
            radius=radius,
            fill=(0, 0, 0, 178),
        )

        # 头像占位（蓝色圆形）
        avatar_x = card_x + int(20 * scale)
        avatar_y = card_y + (card_h - avatar_size) // 2
        draw.ellipse(
            (avatar_x, avatar_y, avatar_x + avatar_size, avatar_y + avatar_size),
            fill=(64, 158, 255, 255),
        )
        # 头像 emoji
        emoji_font_size = int(30 * scale)
        try:
            emoji_font = ImageFont.truetype("segoeui.ttf", emoji_font_size) if os.path.exists("segoeui.ttf") else ImageFont.load_default()
        except Exception:
            emoji_font = ImageFont.load_default()
        draw.text(
            (avatar_x + avatar_size // 2, avatar_y + avatar_size // 2),
            "👤", fill=(255, 255, 255, 255), font=emoji_font, anchor='mm'
        )

        # 头衔文字
        text_x = avatar_x + avatar_size + int(16 * scale)
        if config.subtitle:
            title_y = card_y + int(card_h * 0.32)
        else:
            title_y = card_y + card_h // 2

        draw.text((text_x, title_y), config.title, fill=(255, 255, 255, 255),
                  font=title_font, anchor='lm')

        # 辅语
        if config.subtitle:
            sub_y = card_y + int(card_h * 0.68)
            draw.text((text_x, sub_y), config.subtitle, fill=(204, 204, 204, 255),
                      font=sub_font, anchor='lm')

        # 保存单帧
        frame_filename = f"card_{uuid.uuid4().hex[:8]}_000000.png"
        frame_path = os.path.join(frames_dir, frame_filename)
        img.save(frame_path, "PNG")

        display_seconds = display_frames / fps

        # 保存元数据
        metadata = {
            "video_width": video_width,
            "video_height": video_height,
            "fps": fps,
            "frames": [
                {
                    "path": os.path.join(frames_dir, frame_filename),
                    "frame": 0,
                    "start_frame": 0,
                    "end_frame": display_frames,
                    "start_time": 0.0,
                    "end_time": display_seconds,
                }
            ],
        }
        with open(os.path.join(frames_dir, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        logger.info(f"[Overlay] Generated 1 business card frame (duration={display_seconds:.1f}s) in {frames_dir}")
        return frames_dir