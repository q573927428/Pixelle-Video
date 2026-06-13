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
    `role` ENUM('normal', 'vip', 'admin') NOT NULL DEFAULT 'normal',
    `daily_limit` INT NOT NULL DEFAULT 3 COMMENT '-1 means unlimited (VIP)',
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

            # Fix: ensure existing VIP users have daily_limit = -1 (migrate old data)
            cursor.execute(
                "UPDATE users SET daily_limit = -1 WHERE role = 'vip' AND daily_limit != -1"
            )
            fixed_count = cursor.rowcount
            if fixed_count > 0:
                logger.info(f"✅ Fixed {fixed_count} existing VIP users: set daily_limit = -1")

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
            rowcount = cursor.rowcount
            cursor.close()
            return rowcount
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