"""
修复 recharge_orders 表缺少 code_url 列的脚本
用法: python scripts/fix_recharge_orders_code_url.py

支持两种方式提供数据库连接信息：
1. 命令行参数（推荐）: python scripts/fix_recharge_orders_code_url.py --host=127.0.0.1 --user=root --password=xxx --database=xxx
2. 检查 .env 文件（自动读取项目配置）
"""

import argparse
import os
import sys
from pathlib import Path

import mysql.connector


def parse_env():
    """尝试从项目 .env 文件读取数据库配置"""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return {}

    cfg = {}
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip("'").strip('"')
            if k == "MYSQL_HOST":
                cfg["host"] = v
            elif k == "MYSQL_PORT":
                cfg["port"] = int(v)
            elif k == "MYSQL_USER":
                cfg["user"] = v
            elif k == "MYSQL_PASSWORD":
                cfg["password"] = v
            elif k == "MYSQL_DATABASE":
                cfg["database"] = v
    return cfg


def main():
    parser = argparse.ArgumentParser(description="修复 recharge_orders 表缺少 code_url 列")
    parser.add_argument("--host", help="MySQL 主机地址")
    parser.add_argument("--port", type=int, default=3306, help="MySQL 端口")
    parser.add_argument("--user", help="MySQL 用户名")
    parser.add_argument("--password", help="MySQL 密码")
    parser.add_argument("--database", help="数据库名")
    args = parser.parse_args()

    # 优先用命令行参数，其次尝试 .env 文件
    cfg = {}
    if args.host:
        cfg["host"] = args.host
    if args.user:
        cfg["user"] = args.user
    if args.password:
        cfg["password"] = args.password
    if args.database:
        cfg["database"] = args.database

    # 补充未提供的参数
    env_cfg = parse_env()
    for key in ["host", "user", "password", "database"]:
        if key not in cfg and key in env_cfg:
            cfg[key] = env_cfg[key]
    if "host" not in cfg:
        cfg["host"] = "127.0.0.1"
    if "port" not in cfg:
        cfg["port"] = 3306

    missing = [k for k in ["host", "user", "password", "database"] if k not in cfg]
    if missing:
        print(f"❌ 缺少必要参数: {', '.join(missing)}")
        print("用法: python scripts/fix_recharge_orders_code_url.py --host=127.0.0.1 --user=root --password=xxx --database=xxx")
        sys.exit(1)

    print(f"连接数据库: {cfg['host']}:{cfg.get('port', 3306)}/{cfg['database']}")

    conn = mysql.connector.connect(
        host=cfg["host"],
        port=cfg.get("port", 3306),
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