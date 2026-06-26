"""
支付相关 API 路由 - 充值（人民币→ZS币）
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