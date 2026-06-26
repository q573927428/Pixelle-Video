"""
修复 recharge_orders 表缺少 code_url 列的脚本
用法: python scripts/fix_recharge_orders_code_url.py
"""

import sys
import os
from pathlib import Path

# 将项目根目录加入 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.config import api_config
import mysql.connector


def main():
    cfg = api_config.database
    print(f"连接数据库: {cfg['host']}:{cfg['port']}/{cfg['database']}")

    conn = mysql.connector.connect(
        host=cfg["host"],
        port=cfg["port"],
        user=cfg["user"],
        password=cfg["password"],
        database=cfg["database"],
    )

    try:
        cur = conn.cursor()

        # 检查 code_url 列是否已存在
        cur.execute(
            "SELECT COUNT(*) FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'recharge_orders' AND COLUMN_NAME = 'code_url'",
            (cfg["database"],),
        )
        row = cur.fetchone()
        if row[0] > 0:
            print("✅ code_url 列已存在，无需处理")
            return

        # 添加列
        print("正在添加 code_url 列...")
        cur.execute(
            "ALTER TABLE recharge_orders "
            "ADD COLUMN code_url VARCHAR(512) DEFAULT NULL "
            "COMMENT '微信支付二维码链接' AFTER amount_zs"
        )
        conn.commit()
        print("✅ code_url 列添加成功！")

    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()