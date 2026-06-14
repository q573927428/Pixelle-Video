# Pixelle-Video 生产部署指南

## 📋 架构概览

```
用户浏览器 ── HTTPS ──→ Nginx ──→ FastAPI ──→ RunningHub (云端)
                          │                    ├── LLM API (外部)
                          │                    └── MySQL (Docker)
                          │
                          └── 静态文件 (前端 Vue 3)
                          └── 视频文件 (直接提供)
```

**核心特点：**
- ✅ **无需 GPU** — 全部使用 RunningHub 云端 + 外部 API
- ✅ **低配服务器** — 2核4G 即可运行
- ✅ **一键部署** — Docker Compose 启动所有服务
- ✅ **HTTPS** — 自动 SSL 证书管理
- ✅ **用户系统** — 内置 MySQL + 登录/注册

---

## 🚀 快速部署（5 分钟）

### 1️⃣ 准备服务器

```bash
# 安装 Docker（如已安装则跳过）
curl -fsSL https://get.docker.com | bash
sudo usermod -aG docker $USER
# 重新登录后生效

# 安装 Docker Compose（Docker 24+ 已内置，无需单独安装）
docker compose version
```

### 2️⃣ 克隆项目并配置

```bash
git clone https://github.com/your-repo/Pixelle-Video.git
cd Pixelle-Video

# 创建配置文件
cp .env.example .env

# 编辑 .env 填入你的配置
vim .env
```

### 3️⃣ 配置环境变量

编辑 `.env` 文件，填入以下关键信息：

```bash
# 域名（必须有，用于 HTTPS）
DOMAIN=your-domain.com

# 你的邮箱（用于 Let's Encrypt 证书通知）
SSL_EMAIL=admin@your-domain.com

# LLM API（用于文案生成）
LLM_API_KEY=sk-your-api-key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-max

# RunningHub（用于视频/图片生成）
RUNNINGHUB_API_KEY=rhk-your-runninghub-key

# MySQL 密码（修改为强密码）
MYSQL_ROOT_PASSWORD=your-strong-password
MYSQL_PASSWORD=your-strong-password
```

### 4️⃣ 配置 config.yaml

确保 `config.yaml` 存在（首次部署会自动从 `config.example.yaml` 复制）：

```bash
# 如果还未创建
cp config.example.yaml config.yaml

# 编辑，填入 LLM 和 RunningHub 配置
vim config.yaml
```

**重要：** `docker-compose.prod.yml` 会通过环境变量传递 `LLM_API_KEY` 和 `RUNNINGHUB_API_KEY`。config.yaml 中的值会被环境变量覆盖（取决于代码实现），建议两者都配置一致。

### 5️⃣ 首次启动（获取 SSL 证书）

```bash
# 先启动 API 和 Nginx（HTTP 模式）
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d api nginx

# 获取 SSL 证书（替换 ${DOMAIN} 和 ${SSL_EMAIL} 为你的实际值）
# 注意：需要先确保域名 DNS 已指向服务器 IP
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm certbot certonly --webroot -w /var/www/certbot -d ${DOMAIN} --email ${SSL_EMAIL} --agree-tos --no-eff-email

# 重启 Nginx 加载 SSL 证书
docker compose -f docker-compose.yml -f docker-compose.prod.yml restart nginx

# 完整启动所有服务
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### 6️⃣ 访问服务

```
https://your-domain.com    → 前端界面
https://your-domain.com/docs  → API 文档
```

---

## 📝 常用命令

```bash
# 查看所有服务状态
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps

# 查看日志
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f api
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f nginx

# 重启某个服务
docker compose -f docker-compose.yml -f docker-compose.prod.yml restart api

# 更新服务（拉取最新代码后）
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# 停止所有服务
docker compose -f docker-compose.yml -f docker-compose.prod.yml down

# 停止并删除数据卷（会丢失数据库数据！）
docker compose -f docker-compose.yml -f docker-compose.prod.yml down -v
```

---

## 🔧 配置详解

### 环境变量说明

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `DOMAIN` | 域名（必须） | `pixelle.example.com` |
| `SSL_EMAIL` | SSL 证书通知邮箱 | `admin@example.com` |
| `USE_CN_MIRROR` | 使用中国镜像 | `false` |
| `MYSQL_ROOT_PASSWORD` | MySQL root 密码 | 无默认，必须设置 |
| `MYSQL_DATABASE` | 数据库名 | `pixelle_video` |
| `MYSQL_USER` | MySQL 用户 | `pixelle` |
| `MYSQL_PASSWORD` | MySQL 用户密码 | 无默认，必须设置 |
| `LLM_API_KEY` | LLM API Key | - |
| `LLM_BASE_URL` | LLM API 地址 | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `LLM_MODEL` | LLM 模型名 | `qwen-max` |
| `RUNNINGHUB_API_KEY` | RunningHub API Key | - |
| `JWT_SECRET_KEY` | JWT 加密密钥 | 默认内置（生产环境请修改） |
| `TZ` | 时区 | `Asia/Shanghai` |

---

## ⚠️ 生产环境注意事项

### 1. 安全配置
- **修改 JWT 密钥**：在 `.env` 中设置 `JWT_SECRET_KEY` 为随机字符串
- **修改 MySQL 密码**：使用强密码，不要使用默认值
- **限制端口访问**：MySQL 端口仅监听 `127.0.0.1`，外部不可访问
- **定期更新**：关注项目更新，及时拉取最新代码

### 2. 数据持久化
Docker Compose 配置了以下数据卷：
- `mysql-data` — MySQL 数据库文件（容器内 `/var/lib/mysql`）
- `ssl-certs` — SSL 证书文件
- `output/` — 视频输出文件（宿主机目录挂载）

### 3. 备份策略
```bash
# 备份数据库
docker exec pixelle-mysql mysqldump -u root -p${MYSQL_ROOT_PASSWORD} pixelle_video > backup_$(date +%Y%m%d).sql

# 备份配置
cp .env .env.backup
cp config.yaml config.yaml.backup

# 备份输出文件
tar -czf output_backup_$(date +%Y%m%d).tar.gz output/
```

### 4. SSL 证书自动续期
Certbot 容器每 12 小时自动检查证书是否需要续期。也可以手动续期：

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm certbot renew
docker compose -f docker-compose.yml -f docker-compose.prod.yml restart nginx
```

---

## ❓ 常见问题

### Q: 如何在不使用 MySQL 的情况下运行？（仅限开发）
注释掉 `docker-compose.prod.yml` 中的 mysql 和 api 的 depends_on，并将 `api/config.py` 中的数据库配置保留为本地 `127.0.0.1`。

### Q: 前端页面修改后如何更新？
```bash
# 重新构建前端并重启 API
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build api

# 或仅重建前端（如果单独修改了前端代码）
cd modern_ui && npm run build
# 然后将 dist 目录复制到 API 容器中
```

### Q: 如何查看运行日志？
```bash
# 实时日志
docker compose logs -f api

# 最近 100 行
docker compose logs --tail=100 api
```

### Q: 出现 502 Bad Gateway？
通常是 API 服务尚未就绪，等待几秒后刷新页面。或者检查：
```bash
docker compose ps  # 检查所有服务是否 running
docker compose logs api  # 检查 API 错误日志
```

---

## 📁 文件结构说明

```
Pixelle-Video/
├── .env.example          # 环境变量模板（新建 .env 用）
├── .env                  # 环境变量（敏感信息，已 gitignore）
├── docker-compose.yml    # 基础 Docker Compose
├── docker-compose.prod.yml  # 生产扩展配置
├── Dockerfile            # API 容器构建文件
├── DEPLOY.md             # 本部署指南
├── nginx/
│   ├── Dockerfile        # Nginx 容器构建
│   └── nginx.conf        # Nginx 反向代理配置
├── api/
│   └── config.py         # API 配置（支持环境变量覆盖）
├── config.yaml           # 应用配置（敏感信息，已 gitignore）
├── output/               # 视频输出目录
└── scripts/
    └── init_db.sql       # 数据库初始化脚本