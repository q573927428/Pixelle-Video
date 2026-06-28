"""
支付相关 API 路由 - 充值（人民币→ZS币）+ 会员套餐购买（VIP/SVIP）
"""

import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from loguru import logger
from pydantic import BaseModel
from api.auth.database import Database
from api.auth.schemas import UserInfo, RechargeCreateRequest, RechargeCreateResponse, BalanceResponse
from api.auth.dependencies import require_user, get_sys_config
from api.payment.wechat import (
    create_native_order,
    verify_notify,
    success_xml,
    fail_xml,
    _gen_order_no,
    query_order,
)

router = APIRouter(prefix="/payment", tags=["Payment"])


# ========== 会员套餐购买 API（VIP/SVIP）==========


class VipCreateRequest(BaseModel):
    """VIP/SVIP购买请求"""
    plan_type: str = "vip"  # vip / svip


class VipCreateResponse(BaseModel):
    """VIP/SVIP购买响应"""
    order_no: str
    plan_type: str
    amount_rmb: float
    bonus_zs: int
    code_url: Optional[str] = None
    status: str = "pending"


async def _activate_vip_membership(user_id: int, username: str, plan_type: str, months: int = 1):
    """
    激活VIP/SVIP会员：
    1. 设置 role 和过期时间
    2. 赠送ZS币
    3. 设置 daily_limit = -1（无限）
    """
    from datetime import timedelta
    
    bonus_zs = int(await get_sys_config(f"{plan_type}_bonus_zs", "3900" if plan_type == "vip" else "10000"))
    now = datetime.now()
    
    # 查询用户当前VIP到期时间（用于续费累加）
    user_row = await Database.fetchone(
        "SELECT vip_expires_at, role FROM users WHERE id = %s",
        (user_id,)
    )
    
    # 计算新的到期时间
    new_expires = now + timedelta(days=30 * months)
    if user_row and user_row["vip_expires_at"]:
        current_expires = user_row["vip_expires_at"]
        if isinstance(current_expires, str):
            current_expires = datetime.fromisoformat(current_expires)
        # 如果当前VIP还未过期，累加时长
        if current_expires > now:
            new_expires = current_expires + timedelta(days=30 * months)
    
    # 设置 role 和到期时间
    await Database.execute(
        "UPDATE users SET role = %s, vip_expires_at = %s, daily_limit = -1, "
        "zs_balance = zs_balance + %s WHERE id = %s",
        (plan_type, new_expires, bonus_zs, user_id)
    )
    
    logger.info(
        f"[会员激活] 用户 {username}({user_id}) 开通 {plan_type}，"
        f"到期 {new_expires}，赠送 {bonus_zs} ZS币"
    )
    return bonus_zs


@router.post("/vip/create", response_model=VipCreateResponse)
async def create_vip_order(
    body: VipCreateRequest,
    user: UserInfo = Depends(require_user),
):
    """
    创建VIP/SVIP购买订单
    - VIP: ¥29 + 送3900 ZS币
    - SVIP: ¥89 + 送10000 ZS币
    """
    # 检查plan_type
    if body.plan_type not in ("vip", "svip"):
        raise HTTPException(status_code=400, detail="无效的套餐类型，仅支持 vip/svip")
    
    # 读取价格配置
    price_key = f"{body.plan_type}_price"
    amount_rmb = float(await get_sys_config(price_key, "29" if body.plan_type == "vip" else "89"))
    bonus_zs = int(await get_sys_config(f"{body.plan_type}_bonus_zs", "3900" if body.plan_type == "vip" else "10000"))
    
    # 生成订单号
    order_no = _gen_order_no()
    amount_fen = int(amount_rmb * 100)  # 元转分
    
    # 调用微信统一下单
    description = f"{'SVIP' if body.plan_type == 'svip' else 'VIP'}会员 - ¥{amount_rmb}"
    code_url = create_native_order(
        order_no=order_no,
        amount_fen=amount_fen,
        description=description,
        spbill_create_ip="127.0.0.1",
    )
    
    if not code_url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="微信支付下单失败，请稍后重试",
        )
    
    # 保存订单到 membership_orders 表
    await Database.execute(
        """INSERT INTO membership_orders 
           (order_no, user_id, username, plan_type, amount_rmb, bonus_zs, code_url, status)
           VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending')""",
        (order_no, user.id, user.username, body.plan_type, amount_rmb, bonus_zs, code_url),
    )
    
    logger.info(f"[会员购买] 用户 {user.username}({user.id}) 购买 {body.plan_type}，金额 {amount_rmb}元")
    return VipCreateResponse(
        order_no=order_no,
        plan_type=body.plan_type,
        amount_rmb=amount_rmb,
        bonus_zs=bonus_zs,
        code_url=code_url,
        status="pending",
    )


@router.post("/vip/notify")
async def wechat_vip_notify(request: Request):
    """
    微信支付异步通知回调（VIP/SVIP购买）
    """
    xml_data = (await request.body()).decode("utf-8")
    logger.info(f"[会员回调] 收到微信通知: {xml_data[:200]}...")
    
    # 验证签名
    result = verify_notify(xml_data)
    if not result:
        return Response(content=fail_xml(), media_type="application/xml")
    
    # 获取订单号
    order_no = result.get("out_trade_no")
    transaction_id = result.get("transaction_id")
    
    # 查询订单
    row = await Database.fetchone(
        "SELECT * FROM membership_orders WHERE order_no = %s",
        (order_no,),
    )
    if not row:
        logger.error(f"[会员回调] 订单不存在: {order_no}")
        return Response(content=fail_xml(), media_type="application/xml")
    
    # 防止重复处理
    if row["status"] == "paid":
        logger.info(f"[会员回调] 订单已处理，跳过: {order_no}")
        return Response(content=success_xml(), media_type="application/xml")
    
    # 处理支付成功逻辑
    user_id = row["user_id"]
    plan_type = row["plan_type"]
    
    now = datetime.now()
    
    # 更新订单状态
    await Database.execute(
        """UPDATE membership_orders 
           SET status = 'paid', wechat_transaction_id = %s, paid_at = %s, 
               notify_raw = %s, updated_at = %s
           WHERE order_no = %s""",
        (transaction_id, now, json.dumps(result, ensure_ascii=False, default=str), now, order_no),
    )
    
    # 激活会员
    await _activate_vip_membership(user_id, row["username"], plan_type)
    
    logger.info(
        f"[会员] ✅ 订单 {order_no} 处理完成！用户 {row['username']}({user_id}) "
        f"开通 {plan_type}，支付 {row['amount_rmb']}元"
    )
    
    return Response(content=success_xml(), media_type="application/xml")


@router.get("/vip/order/{order_no}")
async def get_vip_order_status(
    order_no: str,
    user: UserInfo = Depends(require_user),
):
    """
    查询会员订单状态（供前端轮询）
    """
    row = await Database.fetchone(
        "SELECT * FROM membership_orders WHERE order_no = %s AND user_id = %s",
        (order_no, user.id),
    )
    if not row:
        raise HTTPException(status_code=404, detail="订单不存在")
    
    # 如果状态仍是 pending，主动查询微信侧状态
    if row["status"] == "pending":
        wx_result = query_order(order_no)
        if wx_result and wx_result.get("trade_state") == "SUCCESS":
            transaction_id = wx_result.get("transaction_id", "")
            now = datetime.now()
            
            await Database.execute(
                """UPDATE membership_orders 
                   SET status = 'paid', wechat_transaction_id = %s, paid_at = %s, 
                       notify_raw = %s, updated_at = %s
                   WHERE order_no = %s""",
                (transaction_id, now, json.dumps(wx_result, ensure_ascii=False, default=str), now, order_no),
            )
            await _activate_vip_membership(user.id, user.username, row["plan_type"])
            
            row = await Database.fetchone(
                "SELECT * FROM membership_orders WHERE order_no = %s",
                (order_no,),
            )
    
    return {
        "order_no": row["order_no"],
        "plan_type": row["plan_type"],
        "status": row["status"],
        "amount_rmb": float(row["amount_rmb"]),
        "bonus_zs": row["bonus_zs"],
        "paid_at": row["paid_at"],
    }


@router.get("/vip/plans")
async def get_vip_plans():
    """
    获取VIP/SVIP套餐信息（价格、赠送ZS币、折扣率等）
    """
    return {
        "vip": {
            "price": float(await get_sys_config("vip_price", "29")),
            "bonus_zs": int(await get_sys_config("vip_bonus_zs", "3900")),
            "discount": int(float(await get_sys_config("vip_discount", "90"))),
            "queue_priority": int(await get_sys_config("vip_queue_priority", "1")),
        },
        "svip": {
            "price": float(await get_sys_config("svip_price", "89")),
            "bonus_zs": int(await get_sys_config("svip_bonus_zs", "10000")),
            "discount": int(float(await get_sys_config("svip_discount", "80"))),
            "queue_priority": int(await get_sys_config("svip_queue_priority", "2")),
        },
    }


# ========== 充值 API ==========


# ========== 充值 API ==========


@router.post("/recharge/create", response_model=RechargeCreateResponse)
async def create_recharge(
    body: RechargeCreateRequest,
    user: UserInfo = Depends(require_user),
):
    """
    创建充值订单（人民币→ZS币）
    1. 读取汇率配置
    2. 计算到账ZS币数量
    3. 校验最低充值金额
    4. 创建微信支付订单
    5. 保存订单到数据库
    """
    # 1. 读取配置
    exchange_rate = int(await get_sys_config("exchange_rate", "100"))
    min_recharge = float(await get_sys_config("min_recharge", "10"))

    # 2. 校验最低充值金额
    if body.amount_rmb < min_recharge:
        raise HTTPException(
            status_code=400,
            detail=f"最低充值金额为 {min_recharge} 元",
        )

    # 3. 计算到账ZS币（整数）
    amount_zs = int(body.amount_rmb * exchange_rate)

    # 4. 生成订单号
    order_no = _gen_order_no()
    amount_fen = int(body.amount_rmb * 100)  # 元转分

    # 5. 调用微信统一下单
    description = f"ZS币充值 {body.amount_rmb}元"
    code_url = create_native_order(
        order_no=order_no,
        amount_fen=amount_fen,
        description=description,
        spbill_create_ip="127.0.0.1",
    )

    if not code_url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="微信支付下单失败，请稍后重试",
        )

    # 6. 保存订单到数据库
    await Database.execute(
        """INSERT INTO recharge_orders 
           (order_no, user_id, username, amount_rmb, amount_zs, code_url, status)
           VALUES (%s, %s, %s, %s, %s, %s, 'pending')""",
        (
            order_no,
            user.id,
            user.username,
            body.amount_rmb,
            amount_zs,
            code_url,
        ),
    )

    logger.info(f"[充值] 用户 {user.username}({user.id}) 充值 {body.amount_rmb}元 = {amount_zs} ZS币")
    return RechargeCreateResponse(
        order_no=order_no,
        amount_rmb=body.amount_rmb,
        amount_zs=amount_zs,
        code_url=code_url,
        status="pending",
    )


@router.post("/recharge/notify")
async def wechat_recharge_notify(request: Request):
    """
    微信支付异步通知回调（充值）
    """
    xml_data = (await request.body()).decode("utf-8")
    logger.info(f"[充值回调] 收到微信通知: {xml_data[:200]}...")

    # 1. 验证签名
    result = verify_notify(xml_data)
    if not result:
        return Response(content=fail_xml(), media_type="application/xml")

    # 2. 获取订单号
    order_no = result.get("out_trade_no")
    transaction_id = result.get("transaction_id")

    # 3. 查询订单
    row = await Database.fetchone(
        "SELECT * FROM recharge_orders WHERE order_no = %s",
        (order_no,),
    )
    if not row:
        logger.error(f"[充值回调] 订单不存在: {order_no}")
        return Response(content=fail_xml(), media_type="application/xml")

    # 4. 防止重复处理
    if row["status"] == "paid":
        logger.info(f"[充值回调] 订单已处理，跳过: {order_no}")
        return Response(content=success_xml(), media_type="application/xml")

    # 5. 处理充值成功逻辑
    user_id = row["user_id"]
    amount_zs = row["amount_zs"]

    now = datetime.now()

    # 更新订单状态
    await Database.execute(
        """UPDATE recharge_orders 
           SET status = 'paid', wechat_transaction_id = %s, paid_at = %s, 
               notify_raw = %s, updated_at = %s
           WHERE order_no = %s""",
        (
            transaction_id,
            now,
            json.dumps(result, ensure_ascii=False, default=str),
            now,
            order_no,
        ),
    )

    # 给用户增加ZS币
    await Database.execute(
        "UPDATE users SET zs_balance = zs_balance + %s WHERE id = %s",
        (amount_zs, user_id),
    )

    logger.info(
        f"[充值] ✅ 订单 {order_no} 处理完成！用户 {row['username']}({user_id}) "
        f"充值 {row['amount_rmb']}元 到账 {amount_zs} ZS币"
    )

    return Response(content=success_xml(), media_type="application/xml")


# ========== 余额 & 价格查询 ==========


@router.get("/balance", response_model=BalanceResponse)
async def get_balance(user: UserInfo = Depends(require_user)):
    """
    查询 ZS币 余额
    """
    zs_per_second = int(await get_sys_config("zs_per_second", "5"))
    exchange_rate = int(await get_sys_config("exchange_rate", "100"))

    return BalanceResponse(
        zs_balance=user.zs_balance,
        zs_per_second=zs_per_second,
        exchange_rate=exchange_rate,
    )


@router.get("/price")
async def get_price():
    """
    查询每秒价格
    """
    zs_per_second = int(await get_sys_config("zs_per_second", "5"))
    exchange_rate = int(await get_sys_config("exchange_rate", "100"))
    register_bonus = int(await get_sys_config("register_bonus", "600"))
    invite_bonus = int(await get_sys_config("invite_bonus", "200"))
    min_recharge = float(await get_sys_config("min_recharge", "10"))

    return {
        "zs_per_second": zs_per_second,
        "exchange_rate": exchange_rate,
        "register_bonus": register_bonus,
        "invite_bonus": invite_bonus,
        "min_recharge": min_recharge,
    }


# ========== 订单状态查询（供前端轮询） ==========


@router.get("/recharge/order/{order_no}")
async def get_recharge_order_status(
    order_no: str,
    user: UserInfo = Depends(require_user),
):
    """
    查询充值订单状态（供前端轮询）
    """
    row = await Database.fetchone(
        "SELECT * FROM recharge_orders WHERE order_no = %s AND user_id = %s",
        (order_no, user.id),
    )
    if not row:
        raise HTTPException(status_code=404, detail="订单不存在")

    # 如果状态仍是 pending，主动查询微信侧状态
    if row["status"] == "pending":
        wx_result = query_order(order_no)
        if wx_result and wx_result.get("trade_state") == "SUCCESS":
            # 用户已付款但回调未到，手动处理
            transaction_id = wx_result.get("transaction_id", "")
            user_id = row["user_id"]
            amount_zs = row["amount_zs"]

            await Database.execute(
                """UPDATE recharge_orders 
                   SET status = 'paid', wechat_transaction_id = %s, paid_at = %s, 
                       notify_raw = %s, updated_at = %s
                   WHERE order_no = %s""",
                (
                    transaction_id,
                    datetime.now(),
                    json.dumps(wx_result, ensure_ascii=False, default=str),
                    datetime.now(),
                    order_no,
                ),
            )
            await Database.execute(
                "UPDATE users SET zs_balance = zs_balance + %s WHERE id = %s",
                (amount_zs, user_id),
            )
            row = await Database.fetchone(
                "SELECT * FROM recharge_orders WHERE order_no = %s",
                (order_no,),
            )

    return {
        "order_no": row["order_no"],
        "status": row["status"],
        "amount_rmb": float(row["amount_rmb"]),
        "amount_zs": row["amount_zs"],
        "paid_at": row["paid_at"],
    }


# ========== 充值记录查询 ==========


@router.get("/recharge/records")
async def get_recharge_records(
    page: int = 1,
    page_size: int = 10,
    user: UserInfo = Depends(require_user),
):
    """
    查询当前用户的充值记录（分页）
    """
    # 计算总数
    count_row = await Database.fetchone(
        "SELECT COUNT(*) as cnt FROM recharge_orders WHERE user_id = %s",
        (user.id,),
    )
    total = count_row["cnt"] if count_row else 0

    # 分页查询
    offset = (page - 1) * page_size
    rows = await Database.fetchall(
        """SELECT order_no, amount_rmb, amount_zs, status, paid_at, created_at
           FROM recharge_orders
           WHERE user_id = %s
           ORDER BY created_at DESC
           LIMIT %s OFFSET %s""",
        (user.id, page_size, offset),
    )

    records = []
    for row in rows:
        records.append({
            "order_no": row["order_no"],
            "amount_rmb": float(row["amount_rmb"]),
            "amount_zs": row["amount_zs"],
            "status": row["status"],
            "paid_at": row["paid_at"].isoformat() if row["paid_at"] else None,
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        })

    total_pages = max(1, (total + page_size - 1) // page_size)

    return {
        "records": records,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


# ========== 统一账变记录查询（合并充值/消耗/调整/邀请） ==========


@router.get("/balance/records")
async def get_balance_records(
    page: int = 1,
    page_size: int = 10,
    type_filter: str = "",
    user: UserInfo = Depends(require_user),
):
    """
    查询当前用户的所有账变记录（合并充值、消耗、管理员调整、邀请奖励）
    type_filter: ''=全部, recharge=充值, consumption=消耗, adjustment=调整, invite=邀请
    """
    limit = page_size
    offset = (page - 1) * page_size

    # 分别查询各类型数据，在 Python 中合并排序分页
    all_rows = []

    # ---------- 1. 充值记录（仅已支付的） ----------
    if not type_filter or type_filter == 'recharge':
        rows = await Database.fetchall(
            f"""SELECT 'recharge' as type, created_at, amount_zs as change_amount, status, NULL as extra_info
                FROM recharge_orders
                WHERE user_id = {user.id} AND status = 'paid'
                ORDER BY created_at DESC"""
        )
        all_rows.extend(rows)

    # ---------- 2a. 消耗记录（frozen/deducted/refunded 都展示） ----------
    # 显示实际扣除金额（deducted_zs），未结算时显示冻结金额（frozen_zs）
    if not type_filter or type_filter == 'consumption':
        rows = await Database.fetchall(
            f"""SELECT 'consumption' as type, created_at,
                       -COALESCE(deducted_zs, frozen_zs, 0) as change_amount, status, task_id as extra_info
                FROM generation_log
                WHERE user_id = {user.id} AND status IN ('frozen', 'deducted', 'refunded')
                ORDER BY created_at DESC"""
        )
        all_rows.extend(rows)

    # ---------- 2b. 退款记录（refunded） ----------
    if not type_filter or type_filter == 'refund':
        rows = await Database.fetchall(
            f"""SELECT 'refund' as type, updated_at as created_at,
                       COALESCE(frozen_zs, 0) as change_amount, status, task_id as extra_info
                FROM generation_log
                WHERE user_id = {user.id} AND status = 'refunded'
                ORDER BY updated_at DESC"""
        )
        all_rows.extend(rows)

    # ---------- 3. 管理员调整记录 ----------
    if not type_filter or type_filter == 'adjustment':
        rows = await Database.fetchall(
            f"""SELECT 'adjustment' as type, bcl.created_at,
                       bcl.change_amount, 'done' as status, bcl.reason as extra_info
                FROM balance_change_log bcl
                WHERE bcl.user_id = {user.id}
                ORDER BY bcl.created_at DESC"""
        )
        all_rows.extend(rows)

    # ---------- 4. 邀请奖励记录 ----------
    if not type_filter or type_filter == 'invite':
        rows = await Database.fetchall(
            f"""SELECT 'invite' as type, il.created_at,
                       il.reward_zs as change_amount, 'done' as status, u.username as extra_info
                FROM invite_log il
                LEFT JOIN users u ON u.id = il.invitee_id
                WHERE il.inviter_id = {user.id}
                ORDER BY il.created_at DESC"""
        )
        all_rows.extend(rows)

    # ---------- 在 Python 中排序、分页 ----------
    # 按 created_at 降序排序
    all_rows.sort(key=lambda r: r["created_at"] if r["created_at"] else datetime.min, reverse=True)

    total = len(all_rows)

    # 分页截取
    page_rows = all_rows[offset:offset + limit]

    records = []
    for row in page_rows:
        r = {
            "type": row["type"],
            "change_amount": row["change_amount"],
            "created_at": row["created_at"].isoformat() if hasattr(row["created_at"], 'isoformat') else str(row["created_at"]),
            "status": row.get("status", ""),
            "extra_info": row.get("extra_info") or "",
        }

        # 格式化额外信息
        if r["type"] == "recharge":
            r["label"] = "充值"
        elif r["type"] == "consumption":
            r["label"] = "消耗"
            r["extra_info"] = f"任务: {r['extra_info']}" if r["extra_info"] else ""
        elif r["type"] == "refund":
            r["label"] = "退款"
            r["extra_info"] = f"取消/失败退还" if r["extra_info"] else "取消/失败退还"
        elif r["type"] == "adjustment":
            r["label"] = "调整"
        elif r["type"] == "invite":
            r["label"] = "邀请"
            r["extra_info"] = f"邀请: {r['extra_info']}" if r["extra_info"] else ""

        records.append(r)

    total_pages = max(1, (total + page_size - 1) // page_size)

    return {
        "records": records,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


# ========== ZS币消耗记录查询 ==========


@router.get("/consumption/records")
async def get_consumption_records(
    page: int = 1,
    page_size: int = 10,
    user: UserInfo = Depends(require_user),
):
    """
    查询当前用户的ZS币消耗记录（分页）
    """
    # 计算总数
    count_row = await Database.fetchone(
        "SELECT COUNT(*) as cnt FROM generation_log WHERE user_id = %s",
        (user.id,),
    )
    total = count_row["cnt"] if count_row else 0

    # 分页查询
    offset = (page - 1) * page_size
    rows = await Database.fetchall(
        """SELECT task_id, estimated_seconds, actual_seconds, frozen_zs, deducted_zs, status, created_at, updated_at
           FROM generation_log
           WHERE user_id = %s
           ORDER BY created_at DESC
           LIMIT %s OFFSET %s""",
        (user.id, page_size, offset),
    )

    records = []
    for row in rows:
        records.append({
            "task_id": row["task_id"],
            "estimated_seconds": row["estimated_seconds"],
            "actual_seconds": row["actual_seconds"],
            "frozen_zs": row["frozen_zs"],
            "deducted_zs": row["deducted_zs"],
            "status": row["status"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        })

    total_pages = max(1, (total + page_size - 1) // page_size)

    return {
        "records": records,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }