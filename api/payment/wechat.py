"""
微信支付 v2 Native 模式封装
依赖：requests, hashlib, xml.etree.ElementTree, random, time
"""

import hashlib
import random
import string
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Optional

import requests
from loguru import logger

from api.payment.config import (
    WECHAT_MCHID,
    WECHAT_API_KEY,
    WECHAT_APPID,
    WECHAT_NOTIFY_URL,
    UNIFIED_ORDER_URL,
    ORDER_QUERY_URL,
)


def _gen_nonce_str(length: int = 32) -> str:
    """生成随机字符串"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def _gen_order_no() -> str:
    """生成商户订单号: 时间戳 + 8位随机数"""
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    rand = ''.join(random.choices(string.digits, k=8))
    return f"PX{ts}{rand}"


def _md5(s: str) -> str:
    """MD5加密并转大写"""
    return hashlib.md5(s.encode("utf-8")).hexdigest().upper()


def _dict_to_xml(d: dict) -> str:
    """
    字典转XML（微信支付v2格式）
    注意：不使用CDATA，ElementTree自动处理UTF-8编码
    """
    root = ET.Element("xml")
    for k, v in d.items():
        child = ET.SubElement(root, k)
        child.text = str(v)
    return ET.tostring(root, encoding="utf-8").decode("utf-8")


def _xml_to_dict(xml_str: str) -> dict:
    """XML转字典"""
    root = ET.fromstring(xml_str)
    return {child.tag: child.text for child in root}


def _sign(params: dict) -> str:
    """
    微信支付MD5签名（v2标准）

    签名步骤：
    1. 参数名ASCII字典序排序
    2. 拼接成 key1=value1&key2=value2 格式
    3. 末尾拼接 &key=商户API密钥
    4. MD5哈希后转大写

    注意：params中不能含sign字段（sign本身不参与签名计算）
    """
    # 1. 按key字典序排序
    keys = sorted(params.keys())
    # 2. 拼接 key=value&key=value
    raw = "&".join(f"{k}={params[k]}" for k in keys)
    # 3. 末尾加上API密钥
    raw += f"&key={WECHAT_API_KEY}"
    # 4. MD5转大写
    return _md5(raw)


def _verify_sign(xml_data: str) -> bool:
    """验证微信回调签名"""
    params = _xml_to_dict(xml_data)
    sign = params.pop("sign", "")
    if not sign:
        return False
    expected = _sign(params)
    if sign != expected:
        logger.warning(f"[微信支付] 签名验证失败: expected={expected}, got={sign}")
        return False
    return True


def create_native_order(
    order_no: str,
    amount_fen: int,
    description: str,
    spbill_create_ip: str = "127.0.0.1",
) -> Optional[str]:
    """
    微信支付Native统一下单
    :param order_no: 商户订单号
    :param amount_fen: 金额（单位：分）
    :param description: 商品描述
    :param spbill_create_ip: 终端IP
    :return: code_url（支付二维码链接），失败返回None
    """
    params = {
        "appid": WECHAT_APPID,
        "mch_id": WECHAT_MCHID,
        "nonce_str": _gen_nonce_str(),
        "body": description,
        "out_trade_no": order_no,
        "total_fee": str(amount_fen),
        "spbill_create_ip": spbill_create_ip,
        "notify_url": WECHAT_NOTIFY_URL,
        "trade_type": "NATIVE",
    }
    # 计算签名（注意：params此时不含sign字段）
    params["sign"] = _sign(params)

    xml_data = _dict_to_xml(params)
    logger.info(f"[微信支付] 统一下单: {order_no}, 金额={amount_fen}分")

    try:
        resp = requests.post(
            UNIFIED_ORDER_URL,
            data=xml_data.encode("utf-8"),
            headers={"Content-Type": "text/xml"},
            timeout=10,
        )
        # 微信返回XML，需要正确解码
        resp.encoding = "utf-8"
        result = _xml_to_dict(resp.text)
        logger.info(f"[微信支付] 下单响应: {result}")

        if result.get("return_code") == "SUCCESS" and result.get("result_code") == "SUCCESS":
            return result.get("code_url")
        else:
            err_msg = result.get("return_msg", "")
            err_desc = result.get("err_code_des", "")
            err_code = result.get("err_code", "")
            logger.error(f"[微信支付] 下单失败: return_msg={err_msg}, err_code={err_code}, err_desc={err_desc}")
            return None
    except Exception as e:
        logger.error(f"[微信支付] 下单异常: {e}")
        return None


def query_order(order_no: str) -> Optional[dict]:
    """
    查询订单状态
    :param order_no: 商户订单号
    :return: 订单信息dict，失败返回None
    """
    params = {
        "appid": WECHAT_APPID,
        "mch_id": WECHAT_MCHID,
        "out_trade_no": order_no,
        "nonce_str": _gen_nonce_str(),
    }
    params["sign"] = _sign(params)

    xml_data = _dict_to_xml(params)
    try:
        resp = requests.post(
            ORDER_QUERY_URL,
            data=xml_data.encode("utf-8"),
            headers={"Content-Type": "text/xml"},
            timeout=10,
        )
        resp.encoding = "utf-8"
        result = _xml_to_dict(resp.text)
        if result.get("return_code") == "SUCCESS" and result.get("result_code") == "SUCCESS":
            return result
        return None
    except Exception as e:
        logger.error(f"[微信支付] 查询订单异常: {e}")
        return None


def verify_notify(xml_data: str) -> Optional[dict]:
    """
    验证微信支付回调通知
    :param xml_data: 微信POST的原始XML数据
    :return: 验证通过返回解析后的dict，失败返回None
    """
    if not _verify_sign(xml_data):
        logger.warning("[微信支付] 回调签名验证失败")
        return None

    params = _xml_to_dict(xml_data)
    if params.get("return_code") != "SUCCESS":
        logger.warning(f"[微信支付] 回调业务失败: {params.get('return_msg')}")
        return None

    if params.get("result_code") != "SUCCESS":
        logger.warning(f"[微信支付] 支付结果失败: {params.get('err_code_des')}")
        return None

    return params


def success_xml() -> str:
    """回调成功响应XML"""
    return _dict_to_xml({"return_code": "SUCCESS", "return_msg": "OK"})


def fail_xml() -> str:
    """回调失败响应XML"""
    return _dict_to_xml({"return_code": "FAIL", "return_msg": "SIGN_ERROR"})