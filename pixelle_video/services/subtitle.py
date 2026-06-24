"""
字幕生成服务 (Subtitle Generation Service)

根据文案文本和音频时长生成字幕，支持 SRT 格式和 Pillow 字幕帧图像模式。

最终推荐方案（方案 C）：Python (Pillow) 生成字幕帧图像 + FFmpeg overlay 叠加。
此方案能完全支持：
  - 背景颜色、透明度、内边距、圆角
  - 文字大小/颜色、X/Y 轴位置、最大宽度
  - 文字间距 (letter_spacing)
  - 像素级精确控制，预览与实际完全一致
"""

from __future__ import annotations

import math
import os
import re
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from loguru import logger

# 如果 Pillow 不可用，在 import 时给出友好提示
if TYPE_CHECKING:
    from PIL import Image, ImageDraw, ImageFont
else:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        Image = ImageDraw = ImageFont = None  # type: ignore


class SubtitleConfigModel:
    """字幕配置数据类（与前端 SubtitleConfig 接口对应）"""

    def __init__(
        self,
        enabled: bool = False,
        font_size: int = 48,
        font_color: str = "#FFFFFF",
        font_family: str = "PingFang SC",
        position_x: int = 0,
        position_y: int = 0,
        max_width: int = 900,
        letter_spacing: int = 0,
        background_color: str = "#000000",
        background_opacity: float = 0.6,
        background_padding: str = "10 20",
        background_radius: int = 8,
        font_border_width: int = 0,
        font_border_color: str = "#000000",
    ):
        self.enabled = enabled
        self.font_size = font_size
        self.font_color = font_color
        self.font_family = font_family
        self.position_x = position_x
        self.position_y = position_y
        self.max_width = max_width
        self.letter_spacing = letter_spacing
        self.background_color = background_color
        self.background_opacity = background_opacity
        self.background_padding = background_padding
        self.background_radius = background_radius
        self.font_border_width = font_border_width
        self.font_border_color = font_border_color

    @classmethod
    def from_dict(cls, d: dict) -> "SubtitleConfigModel":
        """从字典（通常来自 API 请求）创建配置对象"""
        return cls(
            enabled=d.get("enabled", False),
            font_size=d.get("font_size", 48),
            font_color=d.get("font_color", "#FFFFFF"),
            font_family=d.get("font_family", "PingFang SC"),
            position_x=d.get("position_x", 0),
            position_y=d.get("position_y", 0),
            max_width=d.get("max_width", 900),
            letter_spacing=d.get("letter_spacing", 0),
            background_color=d.get("background_color", "#000000"),
            background_opacity=d.get("background_opacity", 0.6),
            background_padding=d.get("background_padding", "10 20"),
            background_radius=d.get("background_radius", 8),
            font_border_width=d.get("font_border_width", 0),
            font_border_color=d.get("font_border_color", "#000000"),
        )


class SubtitleService:
    """
    字幕服务：生成 SRT 时间轴、Pillow 字幕帧图像
    """

    # 默认字体路径（按优先级搜索）
    DEFAULT_FONT_PATHS = [
        # ===== 最高优先级：思源黑体 / 思源宋体 (安装脚本 install_chinese_fonts.sh 安装到 /usr/share/fonts/chinese/) =====
        "/usr/share/fonts/chinese/NotoSansSC-Regular.otf",
        "/usr/share/fonts/chinese/NotoSansSC-Bold.otf",
        "/usr/share/fonts/chinese/NotoSerifSC-Regular.otf",
        "/usr/share/fonts/chinese/NotoSerifSC-Bold.otf",
        # Ubuntu / Debian (apt install fonts-noto-cjk)
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansSC-Regular.otf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSerifCJK-Regular.ttc",
        # CentOS / RHEL / Fedora (yum install google-noto-cjk-fonts)
        "/usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/google-noto-cjk/NotoSerifCJK-Regular.ttc",
        # Alpine Linux (apk add font-noto-cjk)
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSerifCJK-Regular.ttc",
        # Windows
        "C:/Windows/Fonts/msyh.ttc",  # 微软雅黑
        "C:/Windows/Fonts/simhei.ttf",  # 黑体
        "C:/Windows/Fonts/msyhbd.ttc",  # 微软雅黑粗体
        # macOS
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/STSongti.ttc",
        # Ubuntu / Debian 系统包 (apt install fonts-wqy-microhei)
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        # CentOS / RHEL / Fedora 系统包 (yum install wqy-microhei-fonts)
        "/usr/share/fonts/wqy-microhei/wqy-microhei.ttc",
        "/usr/share/fonts/wqy-zenhei/wqy-zenhei.ttc",
        # 其他阿里/霞鹜字体安装位置
        "/usr/share/fonts/chinese/AlibabaPuHuiTi-3-55-Regular.otf",
        "/usr/share/fonts/chinese/LXGWWenKai-Regular.ttf",
        "/usr/share/fonts/chinese/LXGWWenKai-Bold.ttf",
        # 通用后备
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    def __init__(self, font_path: Optional[str] = None):
        if Image is None:
            raise ImportError(
                "Pillow (PIL) is required for subtitle service. "
                "Install it with: pip install Pillow"
            )
        self._font_path = font_path or self._find_font()

    def _find_font(self) -> str:
        """查找系统可用的中文字体"""
        # 1. 按优先级检查默认路径
        for path in self.DEFAULT_FONT_PATHS:
            if os.path.exists(path):
                logger.info(f"Using Chinese font: {path}")
                return path

        # 2. 扩展递归搜索常见字体目录
        search_dirs = [
            "C:/Windows/Fonts",
            "/System/Library/Fonts",
            "/usr/share/fonts",
            "/usr/local/share/fonts",
            "/usr/X11R6/lib/X11/fonts",
            "~/.fonts",
            "~/.local/share/fonts",
        ]
        candidates = []
        for root_dir in search_dirs:
            expanded = os.path.expanduser(root_dir)
            if not os.path.isdir(expanded):
                continue
            for root, _dirs, files in os.walk(expanded):
                for f in files:
                    if f.lower().endswith((".ttf", ".ttc", ".otf")):
                        candidates.append(os.path.join(root, f))

        # 3. 优先选择包含中文关键词的字体
        cjk_keywords = ["chinese", "cjk", "sc", "cn", "zh", "wqy", "noto", "han", "songti", "heiti", "ming", "fang", "kai", "yahei", "simhei", "simsun", "msyh", "deng"]
        cjk_candidates = [c for c in candidates if any(kw in c.lower() for kw in cjk_keywords)]
        if cjk_candidates:
            logger.info(f"Using CJK font (auto-detected): {cjk_candidates[0]}")
            return cjk_candidates[0]
        if candidates:
            logger.warning(f"No Chinese font found, using first available: {candidates[0]}")
            return candidates[0]

        # 4. 使用 fc-match / fc-list 作为最后手段
        try:
            import subprocess
            result = subprocess.run(
                ["fc-match", "-f", "%{file}", "sans-serif"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                font_path = result.stdout.strip()
                if os.path.exists(font_path):
                    logger.info(f"Using system font via fc-match: {font_path}")
                    return font_path
        except Exception:
            pass

        raise FileNotFoundError(
            "No Chinese font found. Please install a Chinese font or specify font_path. "
            "On CentOS/RHEL: yum install wqy-microhei-fonts\n"
            "On Ubuntu/Debian: apt install fonts-wqy-microhei\n"
            "On Alpine: apk add font-noto-cjk"
        )

    def _hex_to_rgba(self, hex_color: str, opacity: float) -> tuple[int, int, int, int]:
        """将颜色值和透明度转换为 RGBA 元组
        支持:
        - #RRGGBB (6位十六进制)
        - #RRGGBBAA (8位十六进制)
        - rgba(r,g,b,a) 格式
        """
        hex_color = hex_color.strip()
        # 处理 rgba(r, g, b, a) 格式
        if hex_color.lower().startswith("rgba"):
            import re
            match = re.match(r"rgba?\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+))?\s*\)", hex_color)
            if match:
                r, g, b = int(match.group(1)), int(match.group(2)), int(match.group(3))
                a = int(round(opacity * 255))
                return (r, g, b, a)
        # 处理 rgb(r, g, b) 格式
        if hex_color.lower().startswith("rgb"):
            import re
            match = re.match(r"rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", hex_color)
            if match:
                r, g, b = int(match.group(1)), int(match.group(2)), int(match.group(3))
                a = int(round(opacity * 255))
                return (r, g, b, a)
        # 处理十六进制格式
        hex_color = hex_color.lstrip("#")
        if len(hex_color) >= 8:
            # 8位十六进制: RRGGBBAA
            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
            a = int(round(opacity * 255))
            return (r, g, b, a)
        elif len(hex_color) >= 6:
            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
            a = int(round(opacity * 255))
            return (r, g, b, a)
        # 默认返回黑色
        return (0, 0, 0, int(round(opacity * 255)))

    def _parse_padding(self, padding_str: str) -> tuple[int, int, int, int]:
        """
        解析 padding 字符串为 (top, right, bottom, left)
        "10 20" -> (10, 20, 10, 20)
        "10 20 30 40" -> (10, 20, 30, 40)
        """
        parts = padding_str.strip().split()
        if len(parts) == 1:
            v = int(parts[0])
            return (v, v, v, v)
        elif len(parts) == 2:
            tb, lr = int(parts[0]), int(parts[1])
            return (tb, lr, tb, lr)
        elif len(parts) == 4:
            return (int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3]))
        else:
            return (10, 20, 10, 20)  # 默认

    def _split_text_into_lines(
        self, text: str, font: ImageFont.FreeTypeFont, max_width: int, letter_spacing: int = 0
    ) -> list[str]:
        """
        将文本按最大宽度分割成多行
        - 优先按标点符号换行
        - 超出宽度则强制截断
        - 考虑文字间距对宽度的影响
        """
        # 先按标点分割成短句
        sentences = re.split(r"([。！？；，、，.!?;,\s])", text)
        # 将标点重新附加到前一句
        chunks: list[str] = []
        i = 0
        while i < len(sentences):
            if i + 1 < len(sentences) and re.match(r"^[。！？；，、，.!?;,]$", sentences[i + 1]):
                chunks.append(sentences[i] + sentences[i + 1])
                i += 2
            else:
                if sentences[i]:
                    chunks.append(sentences[i])
                i += 1

        lines: list[str] = []
        for chunk in chunks:
            # 计算带有 letter_spacing 的宽度
            def get_text_width(txt: str) -> float:
                if letter_spacing > 0 and len(txt) > 1:
                    return font.getlength(txt) + letter_spacing * (len(txt) - 1)
                return font.getlength(txt)

            # 如果单个 chunk 已经超过最大宽度，需要进一步拆分
            if get_text_width(chunk) > max_width:
                # 按字符拆分
                current_line = ""
                for char in chunk:
                    test_line = current_line + char
                    if get_text_width(test_line) > max_width and current_line:
                        lines.append(current_line)
                        current_line = char
                    else:
                        current_line = test_line
                if current_line:
                    lines.append(current_line)
            else:
                # 尝试合并到当前行
                if lines:
                    test_line = lines[-1] + chunk
                    if get_text_width(test_line) <= max_width:
                        lines[-1] = test_line
                    else:
                        lines.append(chunk)
                else:
                    lines.append(chunk)
        return lines

    def _draw_rounded_rect(
        self,
        draw: ImageDraw.ImageDraw,
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

    @staticmethod
    def _clean_punctuation(text: str) -> str:
        """去除字幕文本中的标点符号"""
        return re.sub(r"[。！？；，、：；“”‘’—…（）【】《》〈〉.!?,;:()\[\]{}<>\"\'\-]", "", text)

    def _draw_text_with_letter_spacing(
        self,
        draw: ImageDraw.ImageDraw,
        xy: tuple[int, int],
        text: str,
        font: ImageFont.FreeTypeFont,
        fill: tuple[int, int, int, int],
        letter_spacing: int = 0,
        anchor: str = 'lt',
        stroke_width: int = 0,
        stroke_fill: Optional[tuple[int, int, int, int]] = None,
    ):
        """
        绘制支持文字间距的文本
        如果 letter_spacing <= 0，使用标准 draw.text 绘制
        否则逐字符绘制，每个字符之间增加 letter_spacing 像素间距
        """
        x, y = xy
        if letter_spacing <= 0:
            if stroke_width > 0 and stroke_fill:
                draw.text((x, y), text, fill=fill, font=font, stroke_width=stroke_width, stroke_fill=stroke_fill, anchor=anchor)
            else:
                draw.text((x, y), text, fill=fill, font=font, anchor=anchor)
            return

        current_x = x
        for char in text:
            if stroke_width > 0 and stroke_fill:
                draw.text((current_x, y), char, fill=fill, font=font, stroke_width=stroke_width, stroke_fill=stroke_fill, anchor='lt')
            else:
                draw.text((current_x, y), char, fill=fill, font=font, anchor='lt')
            char_width = font.getlength(char)
            current_x += char_width + letter_spacing

    def generate_srt(
        self, text: str, audio_duration: float, max_chars_per_line: int = 20
    ) -> str:
        """
        根据文案文本和音频时长生成 SRT 格式字幕

        策略:
        - 按标点符号分句 (。！？；)
        - 每句按时长等比分配
        - 长句按 max_chars_per_line 换行
        """
        # 按分隔符分句
        sentences = re.split(r"(?<=[。！？；，.!?;\s])", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return ""

        # 处理长句：超过 max_chars_per_line 的句子进一步拆分
        final_segments: list[str] = []
        for sent in sentences:
            # 去除标点符号
            sent = self._clean_punctuation(sent)
            if not sent:
                continue
            if len(sent) > max_chars_per_line:
                # 按字数拆分
                for i in range(0, len(sent), max_chars_per_line):
                    final_segments.append(sent[i : i + max_chars_per_line])
            else:
                final_segments.append(sent)

        # 每段时长
        seg_count = len(final_segments)
        seg_duration = audio_duration / seg_count if seg_count > 0 else 1.0

        def to_srt_time(seconds: float) -> str:
            h = int(seconds // 3600)
            m = int((seconds % 3600) // 60)
            s = seconds % 60
            return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")

        lines: list[str] = []
        current_time = 0.0
        for i, seg in enumerate(final_segments):
            start = current_time
            end = current_time + seg_duration
            lines.append(str(i + 1))
            lines.append(f"{to_srt_time(start)} --> {to_srt_time(end)}")
            lines.append(seg)
            lines.append("")
            current_time = end

        return "\n".join(lines)

    def generate_subtitle_frames(
        self,
        text: str,
        audio_duration: float,
        config: SubtitleConfigModel,
        output_dir: str,
        video_width: int = 1080,
        video_height: int = 1920,
        fps: int = 30,
    ) -> str:
        """
        使用 Pillow 生成字幕帧图像（PNG 序列），保存到 output_dir/subtitle_frames/
        返回字幕帧目录路径

        每段字幕生成一张 PNG 图像（带透明通道），然后通过 FFmpeg overlay 叠加到视频对应时间段。
        """
        srt_content = self.generate_srt(text, audio_duration)
        segments = self._parse_srt_segments(srt_content)

        if not segments:
            logger.warning("No subtitle segments generated")
            return ""

        # 创建字幕帧输出目录
        frames_dir = os.path.join(output_dir, "subtitle_frames")
        os.makedirs(frames_dir, exist_ok=True)

        # 字体
        font_size = config.font_size
        try:
            font = ImageFont.truetype(self._font_path, font_size)
        except Exception as e:
            logger.warning(f"Failed to load font '{self._font_path}', using default: {e}")
            font = ImageFont.load_default()

        # 解析 padding
        pad_top, pad_right, pad_bottom, pad_left = self._parse_padding(config.background_padding)
        bg_color = self._hex_to_rgba(config.background_color, config.background_opacity)
        fg_color = self._hex_to_rgba(config.font_color, 1.0)
        border_color = self._hex_to_rgba(config.font_border_color, 1.0) if config.font_border_width > 0 else None
        border_width = config.font_border_width
        letter_spacing = config.letter_spacing

        # 计算 X/Y 位置
        # position_x: 0 = 居中, 负数 = 偏左, 正数 = 偏右
        # position_y: 0 = 底部(距底边100px), 负数 = 偏上, 正数 = 偏下
        base_x = video_width // 2
        offset_x = config.position_x
        base_y = video_height - 50 + config.position_y  # 默认距底边 150px，与前端预览完全对齐

        # 计算带 letter_spacing 的文本宽度
        def get_text_width(txt: str) -> int:
            if not txt:
                return 0
            if letter_spacing > 0 and len(txt) > 1:
                return int(font.getlength(txt)) + letter_spacing * (len(txt) - 1)
            return int(font.getlength(txt))

        frame_files: list[dict] = []  # [{path, start_frame, end_frame}]

        for seg in segments:
            seg_text = seg["text"]
            start_time = seg["start"]
            end_time = seg["end"]

            # 将文本按 max_width 分割成多行
            lines = self._split_text_into_lines(seg_text, font, config.max_width, letter_spacing)

            # 计算每行高度：与前端保持一致
            line_height = font_size

            text_height = len(lines) * line_height

            # 计算背景尺寸
            # 每行宽度取最大行宽（考虑 letter_spacing）
            line_widths = [get_text_width(line) for line in lines]
            max_line_width = max(line_widths) if line_widths else 0
            bg_width = max_line_width + pad_left + pad_right
            bg_height = text_height + pad_top + pad_bottom

            # 背景左上角坐标
            bg_x1 = base_x - bg_width // 2 + offset_x
            bg_y1 = base_y - bg_height

            # 创建透明背景的图像
            img = Image.new("RGBA", (video_width, video_height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            # 绘制圆角背景
            if bg_color[3] > 0:
                radius = min(config.background_radius, bg_height // 2, bg_width // 2)
                self._draw_rounded_rect(
                    draw,
                    (bg_x1, bg_y1, bg_x1 + bg_width, bg_y1 + bg_height),
                    radius,
                    bg_color,
                )

            # 逐行绘制文字（支持 letter_spacing）
            for j, line in enumerate(lines):
                line_x = base_x + offset_x - get_text_width(line) // 2
                line_y = bg_y1 + pad_top + j * line_height
                if border_width > 0 and border_color:
                    self._draw_text_with_letter_spacing(
                        draw,
                        (line_x, line_y), line,
                        font=font, fill=fg_color,
                        letter_spacing=letter_spacing,
                        anchor='lt',
                        stroke_width=border_width,
                        stroke_fill=border_color,
                    )
                else:
                    self._draw_text_with_letter_spacing(
                        draw,
                        (line_x, line_y), line,
                        font=font, fill=fg_color,
                        letter_spacing=letter_spacing,
                        anchor='lt',
                    )

            # 生成帧图像文件名（使用 uuid 避免并发冲突）
            frame_filename = f"subtitle_{uuid.uuid4().hex[:8]}_{seg['index']:04d}.png"
            frame_path = os.path.join(frames_dir, frame_filename)
            img.save(frame_path, "PNG")

            # 计算帧范围
            start_frame = int(start_time * fps)
            end_frame = int(end_time * fps)
            frame_files.append({
                "path": frame_path,
                "start_frame": start_frame,
                "end_frame": end_frame,
                "start_time": start_time,
                "end_time": end_time,
            })

        # 保存帧元数据供 burn_subtitle_frames 使用
        import json

        metadata_path = os.path.join(frames_dir, "metadata.json")
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "video_width": video_width,
                    "video_height": video_height,
                    "fps": fps,
                    "frames": frame_files,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        logger.info(f"Generated {len(frame_files)} subtitle frame images in {frames_dir}")
        return frames_dir

    def _parse_srt_segments(self, srt_content: str) -> list[dict]:
        """解析 SRT 内容为段列表"""
        if not srt_content.strip():
            return []

        segments: list[dict] = []
        blocks = re.split(r"\n\s*\n", srt_content.strip())

        for block in blocks:
            lines = block.strip().split("\n")
            if len(lines) < 3:
                continue
            try:
                index = int(lines[0].strip())
                time_match = re.match(
                    r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})",
                    lines[1].strip(),
                )
                if not time_match:
                    continue
                start = (
                    int(time_match.group(1)) * 3600
                    + int(time_match.group(2)) * 60
                    + int(time_match.group(3))
                    + int(time_match.group(4)) / 1000
                )
                end = (
                    int(time_match.group(5)) * 3600
                    + int(time_match.group(6)) * 60
                    + int(time_match.group(7))
                    + int(time_match.group(8)) / 1000
                )
                text = "\n".join(lines[2:])
                segments.append({
                    "index": index,
                    "start": start,
                    "end": end,
                    "text": text,
                })
            except (ValueError, IndexError):
                continue

        return segments

    def generate_srt_file(
        self,
        text: str,
        audio_duration: float,
        output_dir: str,
        max_chars_per_line: int = 20,
    ) -> str:
        """生成 SRT 文件并返回路径"""
        srt_content = self.generate_srt(text, audio_duration, max_chars_per_line)
        srt_path = os.path.join(output_dir, "preview.srt")
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(srt_content)
        logger.info(f"SRT subtitle file saved: {srt_path}")
        return srt_path