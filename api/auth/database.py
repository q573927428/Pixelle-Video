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
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_username` (`username`),
    INDEX `idx_role` (`role`)
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
        finally:
            conn.close()

    @classmethod
    def _run_migrations_sync(cls, conn):
        """Run database migrations"""
        try:
            cursor = conn.cursor(dictionary=True)
            db_name = conn.database
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

            # Migrate role ENUM: if MySQL doesn't support 'svip', alter the table
            # Check if 'svip' is in the ENUM values
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

            # VIP: daily_limit = 10 (was -1, now changed to 10 per day)
            cursor.execute(
                "UPDATE users SET daily_limit = 10 WHERE role = 'vip' AND daily_limit = -1"
            )
            fixed_vip_count = cursor.rowcount
            if fixed_vip_count > 0:
                logger.info(f"✅ Updated {fixed_vip_count} VIP users: daily_limit changed from -1 to 10")

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

            # Create payment_orders table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS `payment_orders` (
                    `id` INT AUTO_INCREMENT PRIMARY KEY,
                    `order_no` VARCHAR(64) NOT NULL UNIQUE COMMENT '商户订单号（业务唯一）',
                    `user_id` INT NOT NULL COMMENT '用户ID',
                    `username` VARCHAR(50) NOT NULL COMMENT '用户名（冗余，方便对账）',
                    `plan_type` VARCHAR(16) NOT NULL DEFAULT 'vip' COMMENT '套餐类型: vip/svip',
                    `plan_name` VARCHAR(64) NOT NULL DEFAULT 'VIP会员年卡' COMMENT '套餐名称',
                    `amount` DECIMAL(10,2) NOT NULL COMMENT '支付金额（元）',
                    `duration_days` INT NOT NULL DEFAULT 365 COMMENT '开通天数',
                    `status` VARCHAR(20) NOT NULL DEFAULT 'pending'
                        COMMENT '订单状态: pending=待支付, paid=已支付, expired=已过期, cancelled=已取消, refunded=已退款',
                    `wechat_transaction_id` VARCHAR(64) DEFAULT NULL COMMENT '微信支付订单号',
                    `code_url` VARCHAR(255) DEFAULT NULL COMMENT '微信支付二维码链接',
                    `paid_at` DATETIME DEFAULT NULL COMMENT '支付完成时间',
                    `vip_expires_at` DATETIME DEFAULT NULL COMMENT '本次开通后的会员到期时间',
                    `notify_raw` TEXT DEFAULT NULL COMMENT '微信回调原始数据（JSON）',
                    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX `idx_user_id` (`user_id`),
                    INDEX `idx_order_no` (`order_no`),
                    INDEX `idx_status` (`status`),
                    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            logger.info("✅ payment_orders table initialized")

            cursor.close()
        except Exception as e:
            logger.warning(f"⚠️ Migration warning: {e}")

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