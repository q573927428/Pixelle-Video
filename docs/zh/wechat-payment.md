# 微信支付接入实施方案

> 文档版本：v1.0  
> 适用项目：Pixelle-Video  
> 对接目标：将现有手动VIP购买流程（扫码加微信 �?人工转账 �?管理员后台开通）改造为**微信支付Native模式自动开通VIP**

---

## 目录

1. [当前现状分析](#1-当前现状分析)
2. [整体架构](#2-整体架构)
3. [数据库设计](#3-数据库设�?
4. [后端实现](#4-后端实现)
5. [前端改造](#5-前端改�?
6. [配置文件](#6-配置文件)
7. [部署与测试](#7-部署与测�?
8. [附录：微信支付商户平台配置](#8-附录微信支付商户平台配置)

---

## 1. 当前现状分析

### 1.1 现有流程（纯人工�?

```
用户点击"购买VIP"
  �?弹窗显示微信�?+ 微信收款码图�?
  �?用户手动加微�?�?转账 ¥688
  �?管理员收到转�?�?登录后台 �?手动设置用户VIP
  �?用户等待开�?
```

### 1.2 存在的问�?

| 问题 | 影响 |
|------|------|
| 全人工操作，无法7×24自动处理 | 用户流失 |
| 无订单记录，对账困难 | 财务风险 |
| 无支付回调，无法自动开�?| 用户体验�?|
| 微信收款码过期需手动更换 | 维护成本�?|

### 1.3 目标流程（自动支付）

```
用户点击"购买VIP"
  �?前端调后端创建订�?API
  �?后端调用微信支付 Native下单 �?返回 code_url
  �?前端展示微信支付二维码弹�?
  �?用户扫码支付
  �?微信服务器异步通知后端回调地址
  �?后端验证签名 �?更新订单状�?�?自动开通VIP
  �?前端轮询订单状�?�?显示支付成功
```

---

## 2. 整体架构

### 2.1 模块划分

```
┌─────────────────────────────────────────────────────────────�?
�?                      前端 (Vue 3)                          �?
�? UserMenu.vue �?改造VIP购买弹窗                              �?
�? - 调用创建订单 API �?展示支付二维�?                         �?
�? - 轮询订单状�?�?支付成功刷新用户信息                         �?
└───────────────────────┬─────────────────────────────────────�?
                        �?HTTP / JSON
┌───────────────────────▼─────────────────────────────────────�?
�?                  后端 (FastAPI + Python)                    �?
�?                                                            �?
�? api/payment/              # 支付模块 (新增)                  �?
�? ├── __init__.py           # 模块初始�?                      �?
�? ├── router.py             # 支付API路由                      �?
�? ├── wechat.py             # 微信支付SDK封装                  �?
�? ├── models.py             # 订单数据模型                     �?
�? └── config.py             # 支付配置                         �?
�?                                                            �?
�? api/auth/database.py      # 新增 orders �?                 �?
�? api/app.py                # 注册支付路由                     �?
└───────────────────────┬─────────────────────────────────────�?
                        �?XML / HTTP
┌───────────────────────▼─────────────────────────────────────�?
�?             微信支付商户平台 (Native模式)                     �?
�? - 统一下单 API                                              �?
�? - 支付结果通知 (回调)                                        �?
�? - 订单查询 API (可�?                                        �?
└─────────────────────────────────────────────────────────────�?
```

### 2.2 技术选型

| 组件 | 选择 | 说明 |
|------|------|------|
| 支付方式 | 微信支付 Native 模式 | 适合PC Web，生成二维码供用户扫�?|
| SDK | 自行封装 (requests) | 无需额外依赖，微信支付API基于XML |
| 回调 | FastAPI POST接口 | 微信服务器异步通知 |
| 轮询 | 前端 setInterval | 支付完成后刷新用户状�?|

---

## 3. 数据库设�?

### 3.1 新增 `payment_orders` �?

�?`api/auth/database.py` �?`CREATE_TABLES_SQL` 中添加：

```sql
CREATE TABLE IF NOT EXISTS `payment_orders` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `order_no` VARCHAR(64) NOT NULL UNIQUE COMMENT '商户订单号（业务唯一�?,
    `user_id` INT NOT NULL COMMENT '用户ID',
    `username` VARCHAR(50) NOT NULL COMMENT '用户名（冗余，方便对账）',
    `plan_type` VARCHAR(16) NOT NULL DEFAULT 'vip' COMMENT '套餐类型: vip/svip',
    `plan_name` VARCHAR(64) NOT NULL DEFAULT 'VIP会员年卡' COMMENT '套餐名称',
    `amount` DECIMAL(10,2) NOT NULL COMMENT '支付金额（元�?,
    `duration_days` INT NOT NULL DEFAULT 365 COMMENT '开通天�?,
    `status` VARCHAR(20) NOT NULL DEFAULT 'pending'
        COMMENT '订单状�? pending=待支�? paid=已支�? expired=已过�? cancelled=已取�? refunded=已退�?,
    `wechat_transaction_id` VARCHAR(64) DEFAULT NULL COMMENT '微信支付订单�?,
    `code_url` VARCHAR(255) DEFAULT NULL COMMENT '微信支付二维码链�?,
    `paid_at` DATETIME DEFAULT NULL COMMENT '支付完成时间',
    `vip_expires_at` DATETIME DEFAULT NULL COMMENT '本次开通后的会员到期时�?,
    `notify_raw` TEXT DEFAULT NULL COMMENT '微信回调原始数据（JSON�?,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_order_no` (`order_no`),
    INDEX `idx_status` (`status`),
    INDEX `idx_created_at` (`created_at`),
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### 3.2 商品套餐配置（代码常量，或存入数据库�?

建议先在后端代码中定义为常量，后续可扩展为后台可配置�?

```python
# api/payment/config.py

PLANS = {
    "vip": {
        "name": "VIP会员年卡",
        "price": 688.00,          # �?
        "duration_days": 365,      # 开通天�?
        "role": "vip",             # 用户角色
        "daily_limit": 10,         # 每日生成次数
    },
    "svip": {
        "name": "SVIP会员年卡",
        "price": 1588.00,
        "duration_days": 365,
        "role": "svip",
        "daily_limit": -1,         # 无限�?
    },
}
```

---

## 4. 后端实现

### 4.1 目录结构

```
api/
├── payment/                    # 新建支付模块
�?  ├── __init__.py
�?  ├── router.py               # 支付API路由
�?  ├── wechat.py               # 微信支付核心逻辑
�?  └── config.py               # 套餐配置 + 商户配置
├── auth/
�?  └── database.py             # 新增 payment_orders �?
└── app.py                      # 注册 payment_router
```

### 4.2 微信支付配置�?env新增变量�?

```ini
# ==================== 微信支付 ====================
# 微信支付商户号（MCHID�?
WECHAT_MCHID=你的商户�?
# 微信支付API密钥（v2密钥�?2位，在商户平台设置）
WECHAT_API_KEY=你的APIv2密钥
# 微信支付APPID（公众号/小程�?企业微信corpid�?
WECHAT_APPID=你的APPID
# 支付回调地址（公网可访问，微信服务器会POST到这里）
WECHAT_NOTIFY_URL=https://yourdomain.com/api/payment/notify
# 支付结果前端跳转地址（可选）
WECHAT_FRONTEND_URL=https://yourdomain.com
# 商户证书路径（APIv3证书，如果后续升级v3用）
# WECHAT_CERT_PATH=/app/certs/apiclient_cert.p12
```

�?`api/config.py` �?`APIConfig` 类中增加�?

```python
# 微信支付配置
wechat_payment: dict = {
    "mchid": os.getenv("WECHAT_MCHID", ""),
    "api_key": os.getenv("WECHAT_API_KEY", ""),
    "appid": os.getenv("WECHAT_APPID", ""),
    "notify_url": os.getenv("WECHAT_NOTIFY_URL", ""),
}
```

### 4.3 api/payment/config.py  —�?套餐 + 商户配置

```python
"""
支付配置：套餐定�?+ 微信商户信息
"""
from api.config import api_config

# 套餐定义
PLANS = {
    "vip": {
        "name": "VIP会员年卡",
        "price": 688.00,
        "duration_days": 365,
        "role": "vip",
        "daily_limit": 10,
    },
    "svip": {
        "name": "SVIP会员年卡",
        "price": 1588.00,
        "duration_days": 365,
        "role": "svip",
        "daily_limit": -1,
    },
}

# 微信商户配置
WECHAT_MCHID = api_config.wechat_payment["mchid"]
WECHAT_API_KEY = api_config.wechat_payment["api_key"]
WECHAT_APPID = api_config.wechat_payment["appid"]
WECHAT_NOTIFY_URL = api_config.wechat_payment["notify_url"]

# 统一下单API地址（微信支付v2 Native�?
UNIFIED_ORDER_URL = "https://api.mch.weixin.qq.com/pay/unifiedorder"
# 订单查询API
ORDER_QUERY_URL = "https://api.mch.weixin.qq.com/pay/orderquery"
```

### 4.4 api/payment/wechat.py  —�?微信支付核心

```python
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
    """生成随机字符�?""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def _gen_order_no() -> str:
    """生成商户订单�? 时间�?+ 8位随机数"""
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    rand = ''.join(random.choices(string.digits, k=8))
    return f"PX{ts}{rand}"


def _md5(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest().upper()


def _dict_to_xml(d: dict) -> str:
    """字典转XML"""
    root = ET.Element("xml")
    for k, v in d.items():
        child = ET.SubElement(root, k)
        child.text = str(v)
    return ET.tostring(root, encoding="utf-8").decode("utf-8")


def _xml_to_dict(xml_str: str) -> dict:
    """XML转字�?""
    root = ET.fromstring(xml_str)
    return {child.tag: child.text for child in root}


def _sign(params: dict) -> str:
    """微信支付MD5签名"""
    # 1. 按key字典序排�?
    keys = sorted(params.keys())
    # 2. 拼接 key=value&key=value
    raw = "&".join(f"{k}={params[k]}" for k in keys)
    # 3. 末尾加上API密钥
    raw += f"&key={WECHAT_API_KEY}"
    # 4. MD5转大�?
    return _md5(raw)


def _verify_sign(xml_data: str) -> bool:
    """验证微信回调签名"""
    params = _xml_to_dict(xml_data)
    sign = params.pop("sign", "")
    if not sign:
        return False
    expected = _sign(params)
    return sign == expected


def create_native_order(
    order_no: str,
    amount_fen: int,
    description: str,
    spbill_create_ip: str = "127.0.0.1",
) -> Optional[str]:
    """
    微信支付Native统一下单
    :param order_no: 商户订单�?
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
        "product_id": order_no,
    }
    params["sign"] = _sign(params)

    xml_data = _dict_to_xml(params)
    logger.info(f"[微信支付] 统一下单: {order_no}, 金额={amount_fen}�?)

    try:
        resp = requests.post(
            UNIFIED_ORDER_URL,
            data=xml_data.encode("utf-8"),
            headers={"Content-Type": "text/xml"},
            timeout=10,
        )
        result = _xml_to_dict(resp.text)
        logger.info(f"[微信支付] 下单响应: {result}")

        if result.get("return_code") == "SUCCESS" and result.get("result_code") == "SUCCESS":
            return result.get("code_url")
        else:
            logger.error(f"[微信支付] 下单失败: {result.get('return_msg', result.get('err_code_des', '未知错误'))}")
            return None
    except Exception as e:
        logger.error(f"[微信支付] 下单异常: {e}")
        return None


def query_order(order_no: str) -> Optional[dict]:
    """
    查询订单状�?
    :param order_no: 商户订单�?
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
```

### 4.5 api/payment/router.py  —�?支付API路由

```python
"""
支付相关 API 路由
"""
import json
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, status
from loguru import logger

from api.auth.database import Database
from api.auth.schemas import UserInfo
from api.auth.dependencies import require_user
from api.payment.config import PLANS
from api.payment.wechat import (
    create_native_order,
    verify_notify,
    success_xml,
    fail_xml,
    _gen_order_no,
    query_order,
)
from api.auth.utils import (
    has_role_or_expired,
)

router = APIRouter(prefix="/payment", tags=["Payment"])


# ========== 订单相关 ==========


class CreateOrderRequest(BaseModel):
    """创建订单请求"""
    plan_type: str = "vip"  # vip / svip


class OrderInfo(BaseModel):
    """订单信息"""
    order_no: str
    plan_type: str
    plan_name: str
    amount: float
    status: str
    code_url: Optional[str] = None
    created_at: datetime


class OrderStatusResponse(BaseModel):
    """订单状态响�?""
    order_no: str
    status: str
    paid_at: Optional[datetime] = None
    vip_expires_at: Optional[datetime] = None


@router.post("/create", response_model=OrderInfo)
async def create_order(
    body: CreateOrderRequest,
    user: UserInfo = Depends(require_user),
):
    """
    创建支付订单（微信支付Native模式�?
    1. 检查套餐是否有�?
    2. 生成商户订单�?
    3. 检查是否有未支付的同类型订�?
    4. 调用微信统一下单
    5. 保存订单到数据库
    """
    # 1. 校验套餐
    plan = PLANS.get(body.plan_type)
    if not plan:
        raise HTTPException(status_code=400, detail=f"无效的套餐类�? {body.plan_type}")

    # 2. 检查是否已有未支付的同类型订单（防止重复下单）
    existing = await Database.fetchone(
        "SELECT order_no, code_url FROM payment_orders "
        "WHERE user_id = %s AND plan_type = %s AND status = 'pending' "
        "ORDER BY created_at DESC LIMIT 1",
        (user.id, body.plan_type),
    )
    if existing:
        # 有未支付订单，直接返回已有的二维�?
        row = await Database.fetchone(
            "SELECT * FROM payment_orders WHERE order_no = %s",
            (existing["order_no"],),
        )
        return OrderInfo(
            order_no=row["order_no"],
            plan_type=row["plan_type"],
            plan_name=row["plan_name"],
            amount=float(row["amount"]),
            status=row["status"],
            code_url=row["code_url"],
            created_at=row["created_at"],
        )

    # 3. 生成订单�?
    order_no = _gen_order_no()
    amount_fen = int(plan["price"] * 100)  # 元转�?

    # 4. 调用微信统一下单
    code_url = create_native_order(
        order_no=order_no,
        amount_fen=amount_fen,
        description=plan["name"],
        spbill_create_ip="127.0.0.1",
    )
    if not code_url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="微信支付下单失败，请稍后重试",
        )

    # 5. 计算本次开通后的到期时�?
    now = datetime.now()
    # 如果用户当前已是VIP且在有效期内，则在原到期日基础上叠�?
    current_expiry = None
    if user.role in ("vip", "svip") and user.vip_expires_at:
        if user.vip_expires_at > now:
            current_expiry = user.vip_expires_at

    base_date = current_expiry if current_expiry else now
    new_expiry = base_date + timedelta(days=plan["duration_days"])

    # 6. 保存订单到数据库
    await Database.execute(
        """INSERT INTO payment_orders 
           (order_no, user_id, username, plan_type, plan_name, amount, duration_days, 
            code_url, vip_expires_at, status)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending')""",
        (
            order_no,
            user.id,
            user.username,
            body.plan_type,
            plan["name"],
            plan["price"],
            plan["duration_days"],
            code_url,
            new_expiry,
        ),
    )

    logger.info(f"[支付] 用户 {user.username}({user.id}) 创建订单 {order_no}, 金额={plan['price']}�?)
    return OrderInfo(
        order_no=order_no,
        plan_type=body.plan_type,
        plan_name=plan["name"],
        amount=plan["price"],
        status="pending",
        code_url=code_url,
        created_at=datetime.now(),
    )


@router.get("/order/{order_no}", response_model=OrderStatusResponse)
async def get_order_status(
    order_no: str,
    user: UserInfo = Depends(require_user),
):
    """
    查询订单状态（供前端轮询）
    """
    row = await Database.fetchone(
        "SELECT * FROM payment_orders WHERE order_no = %s AND user_id = %s",
        (order_no, user.id),
    )
    if not row:
        raise HTTPException(status_code=404, detail="订单不存�?)

    # 如果状态仍�?pending，主动查询微信侧状态（防止回调延迟�?
    if row["status"] == "pending":
        wx_result = query_order(order_no)
        if wx_result and wx_result.get("trade_state") == "SUCCESS":
            # 用户已付款但回调未到，手动处�?
            await _process_paid_order(row, wx_result)
            row = await Database.fetchone(
                "SELECT * FROM payment_orders WHERE order_no = %s",
                (order_no,),
            )

    return OrderStatusResponse(
        order_no=row["order_no"],
        status=row["status"],
        paid_at=row["paid_at"],
        vip_expires_at=row["vip_expires_at"],
    )


# ========== 微信支付回调 ==========


@router.post("/notify")
async def wechat_pay_notify(request: Request):
    """
    微信支付异步通知回调
    微信服务器以POST方式发送XML数据到此地址
    """
    xml_data = (await request.body()).decode("utf-8")
    logger.info(f"[支付回调] 收到微信通知: {xml_data[:200]}...")

    # 1. 验证签名
    result = verify_notify(xml_data)
    if not result:
        return Response(content=fail_xml(), media_type="application/xml")

    # 2. 获取订单�?
    order_no = result.get("out_trade_no")
    transaction_id = result.get("transaction_id")

    # 3. 查询订单
    row = await Database.fetchone(
        "SELECT * FROM payment_orders WHERE order_no = %s",
        (order_no,),
    )
    if not row:
        logger.error(f"[支付回调] 订单不存�? {order_no}")
        return Response(content=fail_xml(), media_type="application/xml")

    # 4. 防止重复处理
    if row["status"] == "paid":
        logger.info(f"[支付回调] 订单已处理，跳过: {order_no}")
        return Response(content=success_xml(), media_type="application/xml")

    # 5. 处理支付成功逻辑
    await _process_paid_order(row, result, transaction_id)

    return Response(content=success_xml(), media_type="application/xml")


async def _process_paid_order(order_row: dict, wx_result: dict, transaction_id: str = None):
    """
    处理支付成功订单：更新订单状�?+ 自动开通VIP
    """
    order_no = order_row["order_no"]
    user_id = order_row["user_id"]
    plan_type = order_row["plan_type"]
    vip_expires_at = order_row["vip_expires_at"]

    if not transaction_id:
        transaction_id = wx_result.get("transaction_id", "")

    now = datetime.now()

    # 5.1 更新订单状�?
    await Database.execute(
        """UPDATE payment_orders 
           SET status = 'paid', wechat_transaction_id = %s, paid_at = %s, 
               notify_raw = %s, updated_at = %s
           WHERE order_no = %s""",
        (
            transaction_id,
            now,
            json.dumps(wx_result, ensure_ascii=False, default=str),
            now,
            order_no,
        ),
    )

    # 5.2 获取套餐配置
    plan = PLANS.get(plan_type, PLANS["vip"])

    # 5.3 开�?续费VIP
    # 先查询用户当前信�?
    user_row = await Database.fetchone(
        "SELECT role, vip_expires_at FROM users WHERE id = %s",
        (user_id,),
    )
    if not user_row:
        logger.error(f"[支付] 用户不存�? user_id={user_id}")
        return

    await Database.execute(
        "UPDATE users SET role = %s, daily_limit = %s, vip_expires_at = %s, updated_at = %s WHERE id = %s",
        (plan["role"], plan["daily_limit"], vip_expires_at, now, user_id),
    )

    logger.info(
        f"[支付] �?订单 {order_no} 处理完成！用�?{order_row['username']}({user_id}) "
        f"已开�?{plan_type.upper()} �?{vip_expires_at}"
    )


# ========== 商品列表（前端可选） ==========


class PlanInfo(BaseModel):
    """套餐信息"""
    plan_type: str
    name: str
    price: float
    duration_days: int
    features: list[str]


@router.get("/plans", response_model=list[PlanInfo])
async def get_plans():
    """
    获取套餐列表（前端可用来动态渲染价格）
    """
    return [
        PlanInfo(
            plan_type="vip",
            name="VIP会员年卡",
            price=688.00,
            duration_days=365,
            features=["每日10次生�?, "1080P超清画质", "全部模板", "优先队列"],
        ),
        PlanInfo(
            plan_type="svip",
            name="SVIP会员年卡",
            price=1588.00,
            duration_days=365,
            features=["无限制生�?, "1080P超清画质", "全部模板", "专属客服"],
        ),
    ]
```

### 4.6 注册路由 (api/app.py)

�?`api/app.py` 中添加：

```python
# 引入支付路由
from api.payment.router import router as payment_router

# 注册支付路由
app.include_router(payment_router, prefix=api_config.api_prefix)
```

### 4.7 迁移：创�?payment_orders �?

�?`api/auth/database.py` �?`_run_migrations_sync` 方法中添加：

```python
# 创建 payment_orders �?
try:
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS `payment_orders` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `order_no` VARCHAR(64) NOT NULL UNIQUE,
            `user_id` INT NOT NULL,
            `username` VARCHAR(50) NOT NULL,
            `plan_type` VARCHAR(16) NOT NULL DEFAULT 'vip',
            `plan_name` VARCHAR(64) NOT NULL DEFAULT 'VIP会员年卡',
            `amount` DECIMAL(10,2) NOT NULL,
            `duration_days` INT NOT NULL DEFAULT 365,
            `status` VARCHAR(20) NOT NULL DEFAULT 'pending',
            `wechat_transaction_id` VARCHAR(64) DEFAULT NULL,
            `code_url` VARCHAR(255) DEFAULT NULL,
            `paid_at` DATETIME DEFAULT NULL,
            `vip_expires_at` DATETIME DEFAULT NULL,
            `notify_raw` TEXT DEFAULT NULL,
            `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX `idx_user_id` (`user_id`),
            INDEX `idx_order_no` (`order_no`),
            INDEX `idx_status` (`status`),
            FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    logger.info("�?payment_orders table initialized")
except Exception as e:
    logger.warning(f"⚠️ Failed to create payment_orders table: {e}")
```

---

## 5. 前端改�?

### 5.1 改�?UserMenu.vue

将原来的「扫码加微信」手动支付弹窗，替换为「微信支付二维码」自动支付弹窗�?

#### 5.1.1 修改模板部分

**原模�?(vip-dialog)** �?**新模�?(支付二维码弹�?**

核心变化�?

```diff
- <!-- 旧：显示微信�?+ 微信收款码图�?-->
- <div class="vip-qr-section">
-   <img src="/wechat.png" alt="微信二维�? class="vip-qr-img" />
-   <div class="vip-wechat-info">
-     <el-icon style="margin-right:4px; color:#07c160;"><ChatLineSquare /></el-icon>
-     <span>微信号：</span>
-     <span class="vip-wechat-id" @click="copyWechatId">zhuxixy</span>
-     ...
-   </div>
- </div>

+ <!-- 新：显示微信支付二维�?-->
+ <div class="vip-qr-section" v-if="paymentQrUrl">
+   <div class="vip-pay-title">微信扫码支付</div>
+   <img :src="paymentQrUrl" alt="微信支付二维�? class="vip-qr-img" />
+   <div class="vip-pay-hint">
+     <el-icon style="margin-right:4px"><WarningFilled /></el-icon>
+     请使用微信扫描二维码完成支付
+   </div>
+   <div class="vip-pay-amount">
+     支付金额�?strong style="color:#e6a23c; font-size:22px;">¥{{ currentPlanPrice }}</strong>
+   </div>
+   <!-- 倒计�?/ 状态提�?-->
+   <div class="vip-pay-status" v-if="paymentStatus === 'pending'">
+     <el-icon class="is-loading"><Loading /></el-icon>
+     等待支付...
+   </div>
+   <div class="vip-pay-status success" v-else-if="paymentStatus === 'paid'">
+     <el-icon><CircleCheck /></el-icon>
+     支付成功！VIP 已开�?
+   </div>
+ </div>
```

#### 5.1.2 新增支付逻辑 (script)

```typescript
// 新增 import
import { WarningFilled, Loading, CircleCheck } from '@element-plus/icons-vue'
import { request } from '../api'

// 新增状态变�?
const paymentQrUrl = ref('')          // 支付二维码（data:image/... �?code_url转二维码�?
const paymentStatus = ref('')         // pending / paid / expired
const currentPlanType = ref('vip')    // 当前选择的套�?
const currentPlanPrice = ref(688)     // 价格展示
const orderNo = ref('')               // 订单�?
let paymentTimer: ReturnType<typeof setInterval> | null = null

// 显示VIP购买弹窗（重写）
async function showVipDialog() {
  vipDialogVisible.value = true
  paymentStatus.value = ''
  paymentQrUrl.value = ''
  await createAndShowPayment()
}

// 创建订单并展示二维码
async function createAndShowPayment() {
  try {
    // 调用后端创建订单
    const order = await request<{
      order_no: string
      code_url: string
      amount: number
      plan_type: string
      plan_name: string
    }>('/api/payment/create', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuth()._authHeaders(),
      },
      body: JSON.stringify({ plan_type: currentPlanType.value }),
    })
    
    orderNo.value = order.order_no
    currentPlanPrice.value = order.amount
    paymentStatus.value = 'pending'
    
    // �?code_url 转为二维码图片（使用在线API�?
    // 方式1：使�?https://api.qrserver.com/v1/create-qr-code/
    paymentQrUrl.value = `https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=${encodeURIComponent(order.code_url)}`
    // 方式2：如果项目内有二维码生成库，优先使用本地生成
    
    // 开始轮询订单状�?
    startPolling(order.order_no)
  } catch (e: any) {
    ElMessage.error(e.message || '创建订单失败')
  }
}

// 轮询订单状�?
function startPolling(orderNo: string) {
  stopPolling()
  paymentTimer = setInterval(async () => {
    try {
      const res = await request<{
        status: string
        paid_at?: string
        vip_expires_at?: string
      }>(`/api/payment/order/${orderNo}`, {
        headers: {
          ...getAuth()._authHeaders(),
        },
      })
      
      if (res.status === 'paid') {
        paymentStatus.value = 'paid'
        stopPolling()
        ElMessage.success('🎉 支付成功！VIP 已自动开�?)
        
        // 刷新用户信息
        await getAuth().fetchMe()
        await refreshUsage()
        
        // 3秒后关闭弹窗
        setTimeout(() => {
          vipDialogVisible.value = false
        }, 3000)
      }
    } catch {
      // 忽略轮询错误
    }
  }, 3000) // �?秒轮询一�?
}

function stopPolling() {
  if (paymentTimer) {
    clearInterval(paymentTimer)
    paymentTimer = null
  }
}

// 弹窗关闭时停止轮�?
watch(vipDialogVisible, (visible) => {
  if (!visible) {
    stopPolling()
    paymentQrUrl.value = ''
    paymentStatus.value = ''
  }
})

// 可以去掉旧的 copyWechatId 方法
```

#### 5.1.3 新样式补�?

```css
/* 支付二维码样�?*/
.vip-pay-title {
  font-size: 16px;
  font-weight: 700;
  color: #07c160;
  margin-bottom: 12px;
}

.vip-pay-hint {
  display: flex;
  align-items: center;
  font-size: 13px;
  color: #999;
  margin-top: 10px;
}

.vip-pay-amount {
  font-size: 14px;
  color: #ccc;
  margin-top: 8px;
}

.vip-pay-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: #e6a23c;
  margin-top: 12px;
  padding: 8px 16px;
  background: rgba(230, 162, 60, 0.08);
  border-radius: 8px;
}

.vip-pay-status.success {
  color: #22c55e;
  background: rgba(34, 197, 94, 0.08);
}
```

### 5.2 改动文件清单

| 文件 | 改动类型 | 说明 |
|------|----------|------|
| `modern_ui/src/components/UserMenu.vue` | 修改 | 支付弹窗改为微信支付二维�?+ 状态轮�?|
| `api/payment/__init__.py` | 新建 | 空文�?|
| `api/payment/config.py` | 新建 | 套餐配置 + 微信商户信息 |
| `api/payment/wechat.py` | 新建 | 微信支付v2 Native SDK |
| `api/payment/router.py` | 新建 | 支付API路由 |
| `api/auth/database.py` | 修改 | 新增 payment_orders 表迁�?|
| `api/app.py` | 修改 | 注册 payment_router |
| `api/config.py` | 修改 | 增加 wechat_payment 配置字段 |
| `.env.example` | 修改 | 增加微信支付配置�?|

---

## 6. 配置文件

### 6.1 .env 新增�?

```ini
# ==================== 微信支付 ====================
# 微信支付商户号（MCHID�?
WECHAT_MCHID=你的商户�?
# 微信支付API密钥（v2密钥�?2位，在商户平台设置）
WECHAT_API_KEY=你的APIv2密钥
# 微信支付APPID（公众号/小程�?企业微信corpid�?
WECHAT_APPID=你的APPID
# 支付回调地址（公网可访问，微信服务器会POST到这里）
WECHAT_NOTIFY_URL=https://yourdomain.com/api/payment/notify
```

### 6.2 Nginx 配置（如果启用HTTPS�?

确保回调地址能被微信服务器公网访问：

```nginx
location /api/payment/notify {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # 微信回调可能较大，放宽限�?
    client_max_body_size 64k;
    proxy_read_timeout 30s;
}
```

---

## 7. 部署与测�?

### 7.1 部署步骤

1. **在微信商户平台配置回调地址**
   - 登录 [pay.weixin.qq.com](https://pay.weixin.qq.com)
   - 产品中心 �?Native支付 �?开发配�?�?设置回调地址
   - 填写：`https://yourdomain.com/api/payment/notify`

2. **配置 .env**
   - 填写 `WECHAT_MCHID`、`WECHAT_API_KEY`、`WECHAT_APPID`
   - 填写 `WECHAT_NOTIFY_URL`

3. **重启后端服务**
   ```bash
   # 如果使用docker-compose
   docker-compose restart api
   
   # 如果直接运行
   uv run python api/app.py
   ```

4. **前端重新构建**
   ```bash
   cd modern_ui
   pnpm build
   ```

### 7.2 测试用例

| 测试场景 | 预期结果 | 验证方式 |
|----------|----------|----------|
| 未登录用户点击购买VIP | 跳转到登录页 | 已有逻辑 |
| 已登录用户点击购买VIP | 弹出支付二维�?| 前端展示 |
| 用微信扫�?| 显示支付金额 ¥688 | 微信支付�?|
| 支付成功 | 前端显示"支付成功"，VIP自动开�?| 查看用户角色变为vip |
| 重复点击购买（未支付订单�?| 返回同一二维码，不重复下�?| 查看数据库订单数=1 |
| 支付后刷新页�?| 用户状态变为VIP，显示到期时�?| UserMenu更新 |
| 回调失败（网络问题） | 前端轮询补单，最终状态更�?| 等待 �?秒轮询周�?|

### 7.3 常见问题处理

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| 下单返回 `APPID和MCHID不匹配` | APPID未关联商户号 | 登录商户平台 �?产品中心 �?APPID授权管理，关联APPID |
| 回调收不�?| NAT/防火墙未开�?| 确保回调地址公网可达，检查Nginx日志 |
| 回调签名验证失败 | API_KEY配置错误 | 核对商户平台设置的API密钥 |
| `code_url` 为nil | 网络问题/参数错误 | 查看后端日志 `err_code_des` |
| 二维码无法扫�?| 二维码生成服务不可用 | 检�?`api.qrserver.com` 是否可访问，或改用本地二维码�?|

---

## 8. 附录：微信支付商户平台配�?

### 8.1 前置条件

1. 已注�?*微信支付商户�?*（[pay.weixin.qq.com](https://pay.weixin.qq.com)�?
2. 已获�?*APPID**（公众号/小程�?网站应用的APPID�?
3. 已完�?*商户号与APPID绑定**
   - 登录商户平台 �?产品中心 �?APPID授权管理 �?新增授权APPID
4. 已开�?*Native支付**产品
   - 产品中心 �?我的产品 �?Native支付 �?申请开�?

### 8.2 获取配置信息

```
商户�?(MCHID):         登录商户平台 �?账户中心 �?商户信息
API密钥 (API_KEY):      登录商户平台 �?账户中心 �?API安全 �?设置APIv2密钥
APPID:                  微信开放平�?/ 公众号后�?
```

### 8.3 设置支付回调

```
商户平台 �?产品中心 �?Native支付 �?开发配�?
�?支付回调域名: yourdomain.com
```

### 8.4 安全建议

- API密钥请使�?*32位随机字符串**，定期更�?
- 回调地址务必使用 **HTTPS**
- 服务器出口IP加入**白名�?*（商户平�?�?账户中心 �?API安全 �?IP白名单）
- 生产环境请升级到**APIv3**（本方案使用v2，适合快速对接。v3支持证书认证，更安全�?
- 建议对接**微信支付分账**功能，便于后续多商户场景

---

## 附：快速命令清�?

```bash
# 1. 创建支付模块目录
mkdir api\payment
type nul > api\payment\__init__.py

# 2. 安装依赖（如无）
pip install requests

# 3. 修改配置文件
# 编辑 .env 添加微信支付配置�?
# 编辑 api/config.py 添加 wechat_payment 配置
# 编辑 api/auth/database.py 添加 payment_orders 表迁�?
# 编辑 api/app.py 注册 payment_router

# 4. 重新构建前端
cd modern_ui
pnpm build

# 5. 重启服务
uv run python api/app.py
```

---

> **文档结束**  
> 如有疑问请参�?[微信支付官方文档](https://pay.weixin.qq.com/wiki/doc/api/native.php?chapter=6_1)  
> 建议开发时开启微信支付沙箱环境测�
