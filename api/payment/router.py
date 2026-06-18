"""
支付相关 API 路由
"""

import json
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from loguru import logger
from pydantic import BaseModel

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

router = APIRouter(prefix="/payment", tags=["Payment"])


# ========== Pydantic models ==========


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
    """订单状态响应"""
    order_no: str
    status: str
    paid_at: Optional[datetime] = None
    vip_expires_at: Optional[datetime] = None


class UpgradeQuoteRequest(BaseModel):
    """升级报价请求"""
    target_plan: str = "svip"


class UpgradeQuoteResponse(BaseModel):
    """升级报价响应"""
    need_pay: float                  # 需补金额
    mode: str                        # "upgrade" 或 "full"
    vip_remaining_days: int = 0      # VIP 剩余天数
    original_price: float            # SVIP 原价
    new_expiry: Optional[str] = None # 升级后到期时间（原VIP到期日 + SVIP购买天数）


class PlanInfo(BaseModel):
    """套餐信息"""
    plan_type: str
    name: str
    price: float
    duration_days: int
    features: list[str]


# ========== 升级补差价 API ==========


@router.post("/upgrade-quote", response_model=UpgradeQuoteResponse)
async def get_upgrade_quote(
    body: UpgradeQuoteRequest,
    user: UserInfo = Depends(require_user),
):
    """
    计算 VIP → SVIP 升级需补差价
    方案 A：按剩余天数补差价
    公式：需补金额 = (SVIP日均价 - VIP日均价) × VIP剩余天数
    """
    # 1. 仅 VIP 可升级
    if user.role != "vip":
        raise HTTPException(status_code=400, detail="仅 VIP 会员可升级到 SVIP")

    # 2. 校验目标套餐
    target_plan = PLANS.get(body.target_plan)
    if not target_plan:
        raise HTTPException(status_code=400, detail=f"无效的套餐: {body.target_plan}")

    # 3. 计算 VIP 剩余天数
    now = datetime.now()
    expires = user.vip_expires_at
    if not expires:
        raise HTTPException(status_code=400, detail="VIP 已过期或未开通 VIP")

    if isinstance(expires, str):
        expires = datetime.fromisoformat(expires)

    remaining_days = max(0, (expires - now).days)
    vip_plan = PLANS["vip"]

    # 4. 如果 VIP 已过期，直接按全价
    if remaining_days <= 0:
        return UpgradeQuoteResponse(
            need_pay=target_plan["price"],
            mode="full",
            original_price=target_plan["price"],
            vip_remaining_days=0,
        )

    # 5. 计算日均价
    vip_daily = vip_plan["price"] / vip_plan["duration_days"]
    svip_daily = target_plan["price"] / target_plan["duration_days"]

    # 日均差价（SVIP更贵则为正）
    diff_daily = max(0, svip_daily - vip_daily)
    need_pay = round(diff_daily * remaining_days, 2)

    # 6. 升级后的到期日 = VIP原到期日 + SVIP购买天数（直接在原到期日基础上叠加）
    new_expiry = expires + timedelta(days=target_plan["duration_days"])

    return UpgradeQuoteResponse(
        need_pay=need_pay,
        mode="upgrade",
        vip_remaining_days=remaining_days,
        original_price=target_plan["price"],
        new_expiry=new_expiry.isoformat(),
    )


# ========== 订单相关 API ==========


@router.post("/create", response_model=OrderInfo)
async def create_order(
    body: CreateOrderRequest,
    user: UserInfo = Depends(require_user),
):
    """
    创建支付订单（微信支付Native模式）
    1. 检查套餐是否有效
    2. 生成商户订单号
    3. 检查是否有未支付的同类型订单
    4. 调用微信统一下单
    5. 保存订单到数据库
    """
    # 1. 校验套餐
    plan = PLANS.get(body.plan_type)
    if not plan:
        raise HTTPException(status_code=400, detail=f"无效的套餐类型: {body.plan_type}")

    # 1.5 如果是 VIP 升级到 SVIP，按补差价下单
    if body.plan_type == "svip" and user.role == "vip" and user.vip_expires_at:
        try:
            expires = user.vip_expires_at
            if isinstance(expires, str):
                expires = datetime.fromisoformat(expires)
            now = datetime.now()
            if expires > now:
                # VIP 仍在有效期内，计算补差价
                remaining_days = (expires - now).days
                vip_plan = PLANS["vip"]
                vip_daily = vip_plan["price"] / vip_plan["duration_days"]
                svip_daily = plan["price"] / plan["duration_days"]
                diff_daily = max(0, svip_daily - vip_daily)
                need_pay = round(diff_daily * remaining_days, 2)
                
                if need_pay > 0:
                    plan = {**plan}  # copy
                    plan["price"] = need_pay  # 使用补差价作为订单金额
                    plan["name"] = f"VIP→SVIP升级补差价"
                    # 到期日直接用原到期日 + 365天（由下面的第5步计算）
        except Exception:
            pass

    # 2. 先过期所有超过30分钟未支付的订单
    expire_cutoff = datetime.now() - timedelta(minutes=30)
    await Database.execute(
        "UPDATE payment_orders SET status = 'expired', updated_at = %s "
        "WHERE user_id = %s AND status = 'pending' AND created_at < %s",
        (datetime.now(), user.id, expire_cutoff),
    )

    # 3. 检查是否已有未支付且未过期的同类型订单（防止重复下单）
    # 注：第2步已自动过期超过30分钟仍未支付的订单
    existing = await Database.fetchone(
        "SELECT order_no, code_url, created_at FROM payment_orders "
        "WHERE user_id = %s AND plan_type = %s AND status = 'pending' "
        "ORDER BY created_at DESC LIMIT 1",
        (user.id, body.plan_type),
    )
    if existing:
        # 有未支付订单，检查是否创建超过30分钟（理论上已过期，但以防未清理）
        created = existing["created_at"]
        if created and (datetime.now() - created).total_seconds() < 1800:
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
        else:
            # 已超30分钟，自动标记为过期
            await Database.execute(
                "UPDATE payment_orders SET status = 'expired', updated_at = %s WHERE order_no = %s",
                (datetime.now(), existing["order_no"]),
            )

    # 5. 生成订单号
    order_no = _gen_order_no()
    amount_fen = int(plan["price"] * 100)  # 元转分

    # 6. 调用微信统一下单
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

    # 7. 计算本次开通后的到期时间
    now = datetime.now()
    # 如果用户当前已是VIP且在有效期内，则在原到期日基础上叠加
    current_expiry = None
    if user.role in ("vip", "svip") and user.vip_expires_at:
        try:
            expires = user.vip_expires_at
            if isinstance(expires, str):
                expires = datetime.fromisoformat(expires)
            if expires > now:
                current_expiry = expires
        except Exception:
            pass

    base_date = current_expiry if current_expiry else now
    new_expiry = base_date + timedelta(days=plan["duration_days"])

    # 8. 保存订单到数据库
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

    logger.info(f"[支付] 用户 {user.username}({user.id}) 创建订单 {order_no}, 金额={plan['price']}元")
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
        raise HTTPException(status_code=404, detail="订单不存在")

    # 如果状态仍是 pending，主动查询微信侧状态（防止回调延迟）
    if row["status"] == "pending":
        wx_result = query_order(order_no)
        if wx_result and wx_result.get("trade_state") == "SUCCESS":
            # 用户已付款但回调未到，手动处理
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

    # 2. 获取订单号
    order_no = result.get("out_trade_no")
    transaction_id = result.get("transaction_id")

    # 3. 查询订单
    row = await Database.fetchone(
        "SELECT * FROM payment_orders WHERE order_no = %s",
        (order_no,),
    )
    if not row:
        logger.error(f"[支付回调] 订单不存在: {order_no}")
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
    处理支付成功订单：更新订单状态 + 自动开通VIP
    """
    order_no = order_row["order_no"]
    user_id = order_row["user_id"]
    plan_type = order_row["plan_type"]
    vip_expires_at = order_row["vip_expires_at"]

    if not transaction_id:
        transaction_id = wx_result.get("transaction_id", "")

    now = datetime.now()

    # 5.1 更新订单状态
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

    # 5.3 开通/续费VIP
    # 先查询用户当前信息
    user_row = await Database.fetchone(
        "SELECT role, vip_expires_at FROM users WHERE id = %s",
        (user_id,),
    )
    if not user_row:
        logger.error(f"[支付] 用户不存在: user_id={user_id}")
        return

    await Database.execute(
        "UPDATE users SET role = %s, daily_limit = %s, vip_expires_at = %s, updated_at = %s WHERE id = %s",
        (plan["role"], plan["daily_limit"], vip_expires_at, now, user_id),
    )

    logger.info(
        f"[支付] ✅ 订单 {order_no} 处理完成！用户 {order_row['username']}({user_id}) "
        f"已开通 {plan_type.upper()} 至 {vip_expires_at}"
    )


# ========== 商品列表（前端可选） ==========


@router.get("/plans", response_model=list[PlanInfo])
async def get_plans():
    """
    获取套餐列表（前端可用来动态渲染价格）
    """
    return [
        PlanInfo(
            plan_type="vip",
            name="VIP会员年卡(测试)",
            price=688,
            duration_days=365,
            features=["每日10次生成", "1080P超清画质", "全部模板", "优先队列"],
        ),
        PlanInfo(
            plan_type="svip",
            name="SVIP会员年卡(测试)",
            price=1588,
            duration_days=365,
            features=["无限制生成", "1080P超清画质", "全部模板", "专属客服"],
        ),
    ]