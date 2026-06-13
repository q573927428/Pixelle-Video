-- Pixelle-Video Database Initialization Script
-- Run this script to create the database and tables for multi-user support

CREATE DATABASE IF NOT EXISTS pixelle_video
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE pixelle_video;

-- ==================== Users Table ====================
CREATE TABLE IF NOT EXISTS users (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  username      VARCHAR(50)  NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  email         VARCHAR(100) DEFAULT NULL,
  role          ENUM('vip', 'normal', 'admin') NOT NULL DEFAULT 'normal',
  status        TINYINT(1)   NOT NULL DEFAULT 1 COMMENT '1=active, 0=disabled',
  daily_limit   INT          NOT NULL DEFAULT 3  COMMENT '-1=unlimited (VIP)',
  created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_role (role),
  INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==================== Daily Usage Table ====================
CREATE TABLE IF NOT EXISTS daily_usage (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  user_id    INT NOT NULL,
  date       DATE NOT NULL,
  count      INT NOT NULL DEFAULT 0,
  UNIQUE KEY uk_user_date (user_id, date),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_user_date (user_id, date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==================== Generation Logs Table (optional audit) ====================
CREATE TABLE IF NOT EXISTS generation_logs (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  user_id    INT NOT NULL,
  task_id    VARCHAR(100) DEFAULT NULL,
  type       VARCHAR(50)  DEFAULT 'video',
  status     VARCHAR(20)  DEFAULT 'completed',
  created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_user_id (user_id),
  INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==================== Seed Data: Default Admin User ====================
-- Default admin: username=admin, password=admin123
-- IMPORTANT: Change this password after first login!
INSERT INTO users (username, password_hash, email, role, daily_limit)
VALUES ('admin', 'a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6$5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', 'admin@pixelle.com', 'admin', -1)
ON DUPLICATE KEY UPDATE username=username;
-- Note: The password hash above is for 'admin123' with salt 'a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6'
-- You can register a new admin via the API and then delete this default one.
