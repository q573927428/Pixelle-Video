"""
MySQL Database Connection

Uses mysql-connector-python with threading pool for async-compatible access.
Supports MySQL 8+ caching_sha2_password authentication.
"""

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
import mysql.connector
from mysql.connector.pooling import MySQLConnectionPool
from loguru import logger
from api.config import api_config


# SQL to create tables if they don't exist
CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS `users` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `username` VARCHAR(50) NOT NULL UNIQUE,
    `password_hash` VARCHAR(255) NOT NULL,
    `email` VARCHAR(255) DEFAULT NULL,
    `role` ENUM('normal', 'vip', 'svip', 'admin') NOT NULL DEFAULT 'normal',
    `daily_limit` INT NOT NULL DEFAULT 1 COMMENT '-1 means unlimited (SVIP), 10 means VIP',
    `status` TINYINT NOT NULL DEFAULT 1 COMMENT '1=active, 0=disabled',
    `vip_expires_at` DATETIME DEFAULT NULL COMMENT 'VIP会员到期时间',
    `zs_balance` INT NOT NULL DEFAULT 0 COMMENT 'ZS币余额（整数，1元=100ZS币，1秒=5ZS币）',
    `invited_by` INT DEFAULT NULL COMMENT '邀请人用户ID',
    `invite_code` VARCHAR(16) DEFAULT NULL UNIQUE COMMENT '用户邀请码',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_username` (`username`),
    INDEX `idx_role` (`role`),
    INDEX `idx_invite_code` (`invite_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `daily_usage` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `date` DATE NOT NULL,
    `used_count` INT NOT NULL DEFAULT 0,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY `uk_user_date` (`user_id`, `date`),
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    INDEX `idx_user_date` (`user_id`, `date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `user_uploads` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `file_path` VARCHAR(500) NOT NULL,
    `original_name` VARCHAR(255) NOT NULL,
    `file_size` BIGINT NOT NULL DEFAULT 0 COMMENT 'File size in bytes',
    `category` VARCHAR(50) NOT NULL DEFAULT 'misc',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_user_category` (`user_id`, `category`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `sms_codes` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `phone` VARCHAR(20) NOT NULL COMMENT '手机号',
    `code` VARCHAR(6) NOT NULL COMMENT '验证码',
    `used` TINYINT NOT NULL DEFAULT 0 COMMENT '0=未使用, 1=已使用',
    `expires_at` DATETIME NOT NULL COMMENT '过期时间',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_phone_code` (`phone`, `code`),
    INDEX `idx_phone_created` (`phone`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `sys_config` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `config_key` VARCHAR(64) NOT NULL UNIQUE COMMENT '配置键',
    `config_value` VARCHAR(255) NOT NULL COMMENT '配置值',
    `description` VARCHAR(255) DEFAULT NULL COMMENT '描述',
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `recharge_orders` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `order_no` VARCHAR(64) NOT NULL UNIQUE,
    `user_id` INT NOT NULL,
    `username` VARCHAR(50) NOT NULL,
    `amount_rmb` DECIMAL(10,2) NOT NULL COMMENT '充值金额（人民币）',
    `amount_zs` INT NOT NULL COMMENT '到账ZS币数量（整数）',
    `code_url` VARCHAR(512) DEFAULT NULL COMMENT '微信支付二维码链接',
    `status` VARCHAR(20) NOT NULL DEFAULT 'pending',
    `wechat_transaction_id` VARCHAR(64) DEFAULT NULL,
    `paid_at` DATETIME DEFAULT NULL,
    `notify_raw` TEXT DEFAULT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_order_no` (`order_no`),
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `invite_log` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `inviter_id` INT NOT NULL COMMENT '邀请人用户ID',
    `invitee_id` INT NOT NULL COMMENT '被邀请人用户ID',
    `reward_zs` INT NOT NULL DEFAULT 0 COMMENT '邀请人获得的ZS币奖励',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_inviter` (`inviter_id`),
    INDEX `idx_invitee` (`invitee_id`),
    FOREIGN KEY (`inviter_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`invitee_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `balance_change_log` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL COMMENT '用户ID',
    `admin_id` INT NOT NULL COMMENT '操作管理员ID',
    `change_amount` INT NOT NULL COMMENT '变动数量（正数=增加，负数=减少）',
    `balance_before` INT NOT NULL COMMENT '变动前余额',
    `balance_after` INT NOT NULL COMMENT '变动后余额',
    `reason` VARCHAR(500) DEFAULT '' COMMENT '变动原因',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_admin_id` (`admin_id`),
    INDEX `idx_created_at` (`created_at`),
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`admin_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `generation_log` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `task_id` VARCHAR(64) NOT NULL COMMENT '任务ID',
    `user_id` INT NOT NULL,
    `estimated_seconds` INT NOT NULL COMMENT '预估时长（秒，整数）',
    `actual_seconds` INT DEFAULT NULL COMMENT '实际时长（秒，整数，向上取整）',
    `frozen_zs` INT NOT NULL COMMENT '预冻结ZS币（整数）',
    `deducted_zs` INT DEFAULT NULL COMMENT '实际扣除ZS币（整数）',
    `status` VARCHAR(20) NOT NULL DEFAULT 'frozen'
        COMMENT 'frozen=已冻结, deducted=已扣款, refunded=已退款',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_task_id` (`task_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 会员套餐订单表（VIP/SVIP购买记录）
CREATE TABLE IF NOT EXISTS `membership_orders` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `order_no` VARCHAR(64) NOT NULL UNIQUE,
    `user_id` INT NOT NULL,
    `username` VARCHAR(50) NOT NULL,
    `plan_type` VARCHAR(20) NOT NULL COMMENT 'vip/svip',
    `amount_rmb` DECIMAL(10,2) NOT NULL COMMENT '支付金额（人民币）',
    `bonus_zs` INT NOT NULL DEFAULT 0 COMMENT '赠送ZS币数量',
    `months` INT NOT NULL DEFAULT 1 COMMENT '购买月数',
    `code_url` VARCHAR(512) DEFAULT NULL COMMENT '微信支付二维码链接',
    `status` VARCHAR(20) NOT NULL DEFAULT 'pending',
    `wechat_transaction_id` VARCHAR(64) DEFAULT NULL,
    `paid_at` DATETIME DEFAULT NULL,
    `notify_raw` TEXT DEFAULT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_order_no` (`order_no`),
    INDEX `idx_plan_type` (`plan_type`),
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

# Default admin credentials
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"
DEFAULT_ADMIN_EMAIL = "admin@pixelle.ai"


# Migration SQL to add vip_expires_at column if missing
MIGRATE_ADD_VIP_EXPIRES_AT = """
ALTER TABLE `users`
ADD COLUMN IF NOT EXISTS `vip_expires_at` DATETIME DEFAULT NULL COMMENT 'VIP会员到期时间'
AFTER `status`;
"""


class Database:
    """MySQL database connection pool manager using mysql-connector-python"""

    _pool = None
    _executor = ThreadPoolExecutor(max_workers=4)

    @classmethod
    def _get_connection(cls):
        """Get a connection from pool (synchronous)"""
        if cls._pool is None:
            cfg = api_config.database
            logger.info(f"Connecting to MySQL: {cfg['host']}:{cfg['port']}/{cfg['database']}")
            config = {
                "host": cfg["host"],
                "port": cfg["port"],
                "user": cfg["user"],
                "password": cfg["password"],
                "database": cfg["database"],
                "charset": "utf8mb4",
                "autocommit": True,
                "pool_name": "pixelle_pool",
                "pool_size": 10,
            }
            cls._pool = MySQLConnectionPool(**config)
            logger.info("✅ MySQL connection pool created")
        return cls._pool.get_connection()

    @classmethod
    async def get_pool(cls):
        """Get or create connection pool (async wrapper)"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(cls._executor, cls._get_connection)
        return cls._pool

    @classmethod
    async def init_tables(cls):
        """Create database tables if they don't exist and seed default admin"""
        try:
            await cls.get_pool()
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(cls._executor, cls._init_tables_sync)
            logger.info("✅ Database tables initialized (created if not exist)")
        except Exception as e:
            logger.error(f"❌ Failed to initialize database tables: {e}")
            raise

    @classmethod
    def _init_tables_sync(cls):
        """Synchronous table initialization"""
        conn = cls._get_connection()
        try:
            cursor = conn.cursor()
            for statement in CREATE_TABLES_SQL.split(";"):
                stmt = statement.strip()
                if stmt:
                    cursor.execute(stmt)
            cursor.close()
            # Run migrations
            cls._run_migrations_sync(conn)
            # Seed default admin
            cls._seed_default_admin_sync(conn)
            # Seed sys_config defaults
            cls._seed_sys_config_sync(conn)
        finally:
            conn.close()

    @classmethod
    def _run_migrations_sync(cls, conn):
        """Run database migrations"""
        try:
            cursor = conn.cursor(dictionary=True)
            db_name = conn.database
            # 5.6 清除所有会员角色，统一转为普通用户（上线执行一次）
            # 注意：这里用 zs_balance 字段是否存在来判断是否已清理
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'users' AND COLUMN_NAME = 'zs_balance'",
                (db_name,)
            )
            has_zs_balance = cursor.fetchone()
            if has_zs_balance and has_zs_balance["cnt"] > 0:
                # zs_balance 字段存在说明是新版系统，清除所有会员数据
                cursor.execute(
                    "UPDATE users SET "
                    "role = 'normal', "
                    "vip_expires_at = NULL, "
                    "daily_limit = 1 "
                    "WHERE role IN ('vip', 'svip')"
                )
                cleared_count = cursor.rowcount
                if cleared_count > 0:
                    logger.info(f"✅ 已清除 {cleared_count} 个会员用户（vip/svip → normal），统一转为按次计费模式")
                else:
                    logger.info("ℹ️ 无会员用户需要清理（已全部为普通用户）")
            
            # Check if vip_expires_at column exists
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'users' AND COLUMN_NAME = 'vip_expires_at'",
                (db_name,)
            )
            row = cursor.fetchone()
            if row and row["cnt"] == 0:
                cursor.execute(
                    "ALTER TABLE `users` ADD COLUMN `vip_expires_at` DATETIME DEFAULT NULL "
                    "COMMENT 'VIP会员到期时间' AFTER `status`"
                )
                logger.info("✅ Added vip_expires_at column to users table")

            # Check if zs_balance column exists
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'users' AND COLUMN_NAME = 'zs_balance'",
                (db_name,)
            )
            row_zs = cursor.fetchone()
            if row_zs and row_zs["cnt"] == 0:
                cursor.execute(
                    "ALTER TABLE `users` ADD COLUMN `zs_balance` INT NOT NULL DEFAULT 0 "
                    "COMMENT 'ZS币余额（整数，1元=100ZS币，1秒=5ZS币）' AFTER `vip_expires_at`"
                )
                logger.info("✅ Added zs_balance column to users table")

            # Check if invite_code column exists
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'users' AND COLUMN_NAME = 'invite_code'",
                (db_name,)
            )
            row_ic = cursor.fetchone()
            if row_ic and row_ic["cnt"] == 0:
                cursor.execute(
                    "ALTER TABLE `users` ADD COLUMN `invited_by` INT DEFAULT NULL "
                    "COMMENT '邀请人用户ID' AFTER `zs_balance`,"
                    "ADD COLUMN `invite_code` VARCHAR(16) DEFAULT NULL UNIQUE "
                    "COMMENT '用户邀请码' AFTER `invited_by`"
                )
                logger.info("✅ Added invited_by/invite_code columns to users table")

            # Migrate role ENUM: if MySQL doesn't support 'svip', alter the table
            cursor.execute(
                "SELECT COLUMN_TYPE FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'users' AND COLUMN_NAME = 'role'",
                (db_name,)
            )
            col_type_row = cursor.fetchone()
            if col_type_row and "svip" not in col_type_row["COLUMN_TYPE"]:
                cursor.execute(
                    "ALTER TABLE `users` MODIFY COLUMN `role` "
                    "ENUM('normal', 'vip', 'svip', 'admin') NOT NULL DEFAULT 'normal'"
                )
                logger.info("✅ Updated users.role ENUM to include 'svip'")

            # VIP: daily_limit = -1 (unlimited)
            cursor.execute(
                "UPDATE users SET daily_limit = -1 WHERE role = 'vip' AND daily_limit = 10"
            )
            fixed_vip_count = cursor.rowcount
            if fixed_vip_count > 0:
                logger.info(f"✅ Updated {fixed_vip_count} VIP users: daily_limit changed from 10 to -1")

            # SVIP: daily_limit = -1 (unlimited)
            cursor.execute(
                "UPDATE users SET daily_limit = -1 WHERE role = 'svip' AND daily_limit != -1"
            )
            fixed_svip_count = cursor.rowcount
            if fixed_svip_count > 0:
                logger.info(f"✅ Fixed {fixed_svip_count} SVIP users: set daily_limit = -1")

            # Check if phone column exists
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'users' AND COLUMN_NAME = 'phone'",
                (db_name,)
            )
            row_phone = cursor.fetchone()
            if row_phone and row_phone["cnt"] == 0:
                cursor.execute(
                    "ALTER TABLE `users` ADD COLUMN `phone` VARCHAR(20) DEFAULT NULL "
                    "COMMENT '手机号' AFTER `email`,"
                    "ADD UNIQUE INDEX `idx_phone` (`phone`)"
                )
                logger.info("✅ Added phone column to users table")

            cursor.close()
        except Exception as e:
            logger.warning(f"⚠️ Migration warning: {e}")

    @classmethod
    def _seed_sys_config_sync(cls, conn):
        """Seed default system configuration values"""
        try:
            cursor = conn.cursor()
            default_configs = [
                ('zs_per_second', '5', '每秒消耗ZS币数量'),
                ('exchange_rate', '100', '1元人民币可兑换ZS币数量'),
                ('register_bonus', '600', '新用户注册赠送ZS币数量'),
                ('min_recharge', '10', '最低充值金额（元人民币）'),
                ('invite_bonus', '200', '邀请好友注册，邀请人获得的ZS币奖励'),
                # VIP/SVIP 套餐配置
                ('vip_price', '29', 'VIP会员月费（元）'),
                ('svip_price', '89', 'SVIP会员月费（元）'),
                ('vip_bonus_zs', '3900', 'VIP会员开通赠送ZS币数量'),
                ('svip_bonus_zs', '10000', 'SVIP会员开通赠送ZS币数量'),
                ('vip_discount', '90', 'VIP会员生成视频折扣率（90=9折）'),
                ('svip_discount', '80', 'SVIP会员生成视频折扣率（80=8折）'),
                ('vip_queue_priority', '1', 'VIP队列优先级'),
                ('svip_queue_priority', '2', 'SVIP队列优先级'),
            ]
            for key, value, desc in default_configs:
                cursor.execute(
                    "INSERT IGNORE INTO sys_config (config_key, config_value, description) VALUES (%s, %s, %s)",
                    (key, value, desc)
                )
            cursor.close()
            logger.info("✅ System configuration seeded (sys_config)")
        except Exception as e:
            logger.warning(f"⚠️ Failed to seed sys_config: {e}")

    @classmethod
    def _seed_default_admin_sync(cls, conn):
        """Create default admin user if it doesn't exist (synchronous)"""
        try:
            from api.auth.utils import hash_password

            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT id FROM users WHERE username = %s",
                (DEFAULT_ADMIN_USERNAME,)
            )
            existing = cursor.fetchone()
            cursor.close()

            if existing:
                logger.debug(f"Default admin user '{DEFAULT_ADMIN_USERNAME}' already exists, skipping")
                return

            password_hash = hash_password(DEFAULT_ADMIN_PASSWORD)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (username, password_hash, email, role, daily_limit) VALUES (%s, %s, %s, %s, %s)",
                (DEFAULT_ADMIN_USERNAME, password_hash, DEFAULT_ADMIN_EMAIL, "admin", -1)
            )
            cursor.close()
            logger.info(f"✅ Default admin user created: '{DEFAULT_ADMIN_USERNAME}' / '{DEFAULT_ADMIN_PASSWORD}'")
        except Exception as e:
            logger.warning(f"⚠️ Failed to seed default admin user: {e}")

    @classmethod
    async def close(cls):
        """Close connection pool"""
        if cls._pool:
            cls._pool = None
            logger.info("MySQL connection pool closed")

    @classmethod
    async def execute(cls, sql: str, params=None):
        """Execute SQL query (INSERT/UPDATE/DELETE)"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(cls._executor, cls._execute_sync, sql, params)

    @classmethod
    def _execute_sync(cls, sql: str, params=None):
        """Synchronous execute"""
        conn = cls._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params or ())
            # For INSERT statements, return last insert id
            if sql.strip().upper().startswith('INSERT'):
                result = cursor.lastrowid
            else:
                result = cursor.rowcount
            cursor.close()
            return result
        finally:
            conn.close()

    @classmethod
    async def fetchone(cls, sql: str, params=None):
        """Fetch one row"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(cls._executor, cls._fetchone_sync, sql, params)

    @classmethod
    def _fetchone_sync(cls, sql: str, params=None):
        """Synchronous fetchone"""
        conn = cls._get_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, params or ())
            row = cursor.fetchone()
            cursor.close()
            return row
        finally:
            conn.close()

    @classmethod
    async def fetchall(cls, sql: str, params=None):
        """Fetch all rows"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(cls._executor, cls._fetchall_sync, sql, params)

    @classmethod
    def _fetchall_sync(cls, sql: str, params=None):
        """Synchronous fetchall"""
        conn = cls._get_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, params or ())
            rows = cursor.fetchall()
            cursor.close()
            return rows
        finally:
            conn.close()