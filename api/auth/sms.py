"""
Aliyun SMS Client

Handles SMS verification code sending via Aliyun SMS service.
Supports both real API calls and mock mode for development.
"""

import random
import json
from datetime import datetime, timedelta
from loguru import logger

from api.config import api_config


class SmsClient:
    """Aliyun SMS client for sending verification codes"""

    _mock_mode: bool = False

    @classmethod
    def is_mock_mode(cls) -> bool:
        """Check if running in mock mode (no valid Aliyun credentials)"""
        cfg = api_config.aliyun_sms
        return not (cfg.get("access_key_id") and cfg.get("access_key_secret")
                    and cfg.get("sign_name") and cfg.get("template_code"))

    @classmethod
    def generate_code(cls) -> str:
        """Generate a 6-digit verification code"""
        return f"{random.randint(100000, 999999)}"

    @classmethod
    async def send_sms(cls, phone: str, code: str) -> bool:
        """
        Send SMS verification code

        Args:
            phone: Phone number
            code: 6-digit verification code

        Returns:
            True if sent successfully
        """
        if cls.is_mock_mode():
            logger.info(f"[SMS Mock] 验证码 {code} 发送到手机 {phone}")
            return True

        try:
            from aliyunsdkcore.client import AcsClient
            from aliyunsdkdysmsapi.request.v20170525 import SendSmsRequest

            cfg = api_config.aliyun_sms
            client = AcsClient(
                cfg["access_key_id"],
                cfg["access_key_secret"],
                "cn-hangzhou"
            )

            request = SendSmsRequest.SendSmsRequest()
            request.set_PhoneNumbers(phone)
            request.set_SignName(cfg["sign_name"])
            request.set_TemplateCode(cfg["template_code"])
            request.set_TemplateParam(json.dumps({"code": code}))

            response = client.do_action_with_exception(request)
            response_data = json.loads(response)

            if response_data.get("Code") == "OK":
                logger.info(f"[SMS] 验证码已发送到手机 {phone}")
                return True
            else:
                logger.error(f"[SMS] 发送失败: {response_data.get('Message', '未知错误')}")
                return False

        except ImportError:
            logger.warning("aliyunsdkdysmsapi 未安装，使用模拟模式发送验证码")
            logger.info(f"[SMS Mock] 验证码 {code} 发送到手机 {phone}")
            return True
        except Exception as e:
            logger.error(f"[SMS] 发送异常: {e}")
            return False