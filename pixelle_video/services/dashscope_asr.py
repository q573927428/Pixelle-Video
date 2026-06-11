"""
DashScope 短音频语音识别（ASR）服务。

用于把本地上传的参考音频识别为文本，供 VoxCPM 等语音克隆场景
自动回填 prompt_text。

当前实现使用 DashScope Recognition 短音频/一句话识别接口：
- 直接读取本地音频文件，不依赖公网 URL 或 OSS。
- 非 wav 文件会优先用 ffmpeg 转为 16k 单声道 wav，提高识别稳定性。
- 识别结果从 output.sentence / output.text 等常见结构中提取。

参考文档：https://help.aliyun.com/zh/model-studio/paraformer-real-time-speech-recognition-api
"""

import json
import os
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Any, Optional

from loguru import logger

try:
    import dashscope
    from dashscope.audio.asr import Recognition, RecognitionCallback

    HAS_DASHSCOPE_ASR = True
except ImportError:
    HAS_DASHSCOPE_ASR = False
    dashscope = None
    Recognition = None
    RecognitionCallback = None


class DashScopeASRService:
    """
    DashScope 短音频识别服务。

    Usage:
        asr = DashScopeASRService(api_key="your-key")
        text = asr.transcribe("path/to/audio.mp3")
    """

    SUPPORTED_FORMATS = {".wav", ".mp3", ".pcm", ".ogg", ".flac", ".m4a", ".aac"}

    def __init__(self, api_key: Optional[str] = None):
        if not HAS_DASHSCOPE_ASR:
            raise ImportError(
                "dashscope 未安装，无法使用语音识别。请运行: pip install dashscope"
            )

        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            logger.warning("DashScope ASR: 未设置 API Key，请通过参数或环境变量 DASHSCOPE_API_KEY 提供")
        else:
            dashscope.api_key = self.api_key

        logger.info("🎙️ DashScope ASR 服务已初始化")

    def _validate_audio(self, audio_path: str) -> str:
        if not audio_path:
            raise ValueError("音频文件路径不能为空")

        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")
        _, ext = os.path.splitext(audio_path)
        if ext.lower() not in self.SUPPORTED_FORMATS:
            logger.warning(f"音频格式 {ext} 可能不被支持，支持的格式: {self.SUPPORTED_FORMATS}")
        return audio_path

    def transcribe(self, audio_path: str, model: str = "paraformer-realtime-v2") -> str:
        """
        将本地音频文件识别为文本。

        Args:
            audio_path: 本地音频文件路径
            model: DashScope Recognition 模型，默认 paraformer-realtime-v2

        Returns:
            识别出的文本
        """
        audio_path = self._validate_audio(audio_path)
        if not self.api_key:
            raise RuntimeError("DashScope API Key 未配置，无法进行语音识别")

        logger.info(f"🎙️ 开始语音识别: {audio_path}")
        try:
            response = self._transcribe_short_audio(audio_path, model)
            status_code = getattr(response, "status_code", None)
            if status_code != 200:
                msg = getattr(response, "message", "未知错误")
                logger.error(f"语音识别失败 [{status_code}]: {msg}")
                raise RuntimeError(f"语音识别失败: {msg}")

            text = self._extract_text(response)
            if not text:
                logger.debug(f"DashScope ASR 原始响应: {self._safe_to_json(response)}")
                raise RuntimeError("语音识别返回空结果，未能从 DashScope 返回数据中提取文本")

            logger.info(f"✅ 语音识别完成: {text[:80]}...")
            return text

        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f"❌ 语音识别异常: {e}")
            raise RuntimeError(f"语音识别失败: {e}") from e

    def _transcribe_short_audio(self, audio_path: str, model: str):
        """调用 DashScope Recognition 同步识别本地短音频。"""
        recognition_model = model if "realtime" in model else "paraformer-realtime-v2"
        recognition_file, temp_dir = self._prepare_recognition_audio(audio_path)

        try:
            audio_format = self._get_audio_format(recognition_file)
            sample_rate = self._get_audio_sample_rate(recognition_file)
            logger.info(
                f"使用 DashScope 短音频识别: model={recognition_model}, "
                f"format={audio_format}, sample_rate={sample_rate}"
            )

            recognition = Recognition(
                model=recognition_model,
                callback=RecognitionCallback(),
                format=audio_format,
                sample_rate=sample_rate,
            )
            return recognition.call(recognition_file)
        finally:
            if temp_dir:
                shutil.rmtree(temp_dir, ignore_errors=True)

    def _prepare_recognition_audio(self, audio_path: str) -> tuple[str, str | None]:
        """
        准备给 Recognition 使用的音频文件。

        优先将非 wav 音频转为 16k 单声道 wav。转换后的临时目录会由调用方清理。
        如果系统没有 ffmpeg 或转换失败，则直接使用原始文件。
        """
        ext = Path(audio_path).suffix.lower().lstrip(".")
        if ext == "wav":
            return audio_path, None

        ffmpeg_path = shutil.which("ffmpeg")
        if not ffmpeg_path:
            logger.warning("未找到 ffmpeg，直接使用原始音频进行短音频识别")
            return audio_path, None

        temp_dir = tempfile.mkdtemp(prefix="dashscope_asr_")
        wav_path = os.path.join(temp_dir, f"{Path(audio_path).stem}_16k.wav")
        cmd = [
            ffmpeg_path,
            "-y",
            "-i",
            audio_path,
            "-ac",
            "1",
            "-ar",
            "16000",
            "-f",
            "wav",
            wav_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            logger.warning(f"音频转 16k wav 失败，退回原始音频: {result.stderr}")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return audio_path, None

        return wav_path, temp_dir

    @staticmethod
    def _get_audio_format(audio_path: str) -> str:
        ext = Path(audio_path).suffix.lower().lstrip(".")
        if ext == "m4a":
            return "mp4"
        return ext or "wav"

    @staticmethod
    def _get_audio_sample_rate(audio_path: str) -> int:
        if Path(audio_path).suffix.lower() == ".wav":
            try:
                with wave.open(audio_path, "rb") as wav_file:
                    return wav_file.getframerate()
            except Exception as e:
                logger.debug(f"读取 wav 采样率失败，使用默认 16000: {e}")
        return 16000

    @classmethod
    def _extract_text(cls, response: object) -> str:
        """
        从 Recognition 返回结果中提取文本。

        Recognition.call() 的同步返回通常在 output.sentence 中保存结果；
        sentence 可能是单个 dict，也可能是多个分句组成的 list。
        """
        data = cls._normalize_payload(response)
        text = cls._extract_text_from_payload(data)
        if text:
            return text

        logger.warning(f"无法从识别结果中提取文本，响应类型: {type(response).__name__}")
        logger.debug(f"DashScope ASR 响应详情: {cls._safe_to_json(response)}")
        return ""

    @classmethod
    def _extract_text_from_payload(cls, data: Any) -> str:
        """递归兼容 DashScope 常见转写结果结构。"""
        data = cls._normalize_payload(data)

        if isinstance(data, str):
            return data.strip()

        if isinstance(data, list):
            texts = [cls._extract_text_from_payload(item) for item in data]
            return "".join(text for text in texts if text)

        if not isinstance(data, dict):
            return ""

        direct_text = data.get("text")
        if isinstance(direct_text, str) and direct_text.strip():
            return direct_text.strip()

        for key in ("sentence", "sentences", "results", "transcripts"):
            value = data.get(key)
            if value:
                text = cls._extract_text_from_payload(value)
                if text:
                    return text

        for key in ("output", "result"):
            value = data.get(key)
            if value:
                text = cls._extract_text_from_payload(value)
                if text:
                    return text

        return ""

    @classmethod
    def _normalize_payload(cls, payload: Any) -> Any:
        """将 SDK 响应对象、dict/list 和 JSON 字符串转成普通 Python 数据。"""
        if payload is None:
            return None

        if isinstance(payload, (dict, list, str)):
            if isinstance(payload, str):
                stripped = payload.strip()
                if stripped.startswith(("{", "[")):
                    try:
                        return json.loads(stripped)
                    except json.JSONDecodeError:
                        return payload
            if isinstance(payload, dict):
                return {
                    key: cls._normalize_payload(value)
                    for key, value in dict(payload).items()
                }
            if isinstance(payload, list):
                return [cls._normalize_payload(item) for item in payload]
            return payload

        if hasattr(payload, "items"):
            try:
                return {
                    key: cls._normalize_payload(value)
                    for key, value in dict(payload).items()
                }
            except Exception:
                pass

        attrs = {}
        for attr in ("status_code", "request_id", "code", "message", "output", "usage", "usages"):
            value = getattr(payload, attr, None)
            if value is not None:
                attrs[attr] = cls._normalize_payload(value)
        if attrs:
            return attrs

        return payload

    @classmethod
    def _safe_to_json(cls, payload: Any) -> str:
        """安全序列化调试信息。"""
        try:
            normalized = cls._normalize_payload(payload)
            return json.dumps(normalized, ensure_ascii=False, default=str)
        except Exception:
            return repr(payload)


def get_asr_service() -> DashScopeASRService:
    """从项目配置获取 ASR 服务实例，复用 DashScope 的 API Key"""
    from pixelle_video.config import config_manager

    try:
        providers = config_manager.get_api_providers_config()
        dashscope_cfg = providers.get("dashscope", {}) if providers else {}
        api_key = dashscope_cfg.get("api_key", "")
    except Exception:
        api_key = os.getenv("DASHSCOPE_API_KEY", "")

    return DashScopeASRService(api_key=api_key)