"""Script to initialize database tables and create default admin user"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import mysql.connector
from api.config import api_config
from api.auth.utils import hash_password

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


def main():
    cfg = api_config.database
    print(f"Connecting to MySQL: {cfg['host']}:{cfg['port']}/{cfg['database']}")

    conn = mysql.connector.connect(
        host=cfg["host"], port=cfg["port"],
        user=cfg["user"], password=cfg["password"],
        database=cfg["database"], charset="utf8mb4", autocommit=True
    )

    # Create tables
    cursor = conn.cursor()
    for statement in CREATE_TABLES_SQL.split(";"):
        stmt = statement.strip()
        if stmt:
            cursor.execute(stmt)
    cursor.close()
    print("✅ Tables created (if not exist)")

    # Create admin user
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id FROM users WHERE username = 'admin'")
    existing = cursor.fetchone()
    cursor.close()

    if existing:
        print(f"Admin user 'admin' already exists (id={existing['id']})")
    else:
        pw = hash_password("admin123")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, password_hash, email, role, daily_limit) VALUES (%s, %s, %s, %s, %s)",
            ("admin", pw, "admin@pixelle.ai", "admin", -1)
        )
        cursor.close()
        print("✅ Admin user created: admin / admin123")

    conn.close()
    print("Done.")


if __name__ == "__main__":
    main()
