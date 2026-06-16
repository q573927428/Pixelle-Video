# Pixelle-Video 宝塔面板部署指南（Python项目 + Node项目）

> 本文档使用宝塔面板内置的 **Python项目** 和 **Node项目** 功能部署，无需手动配置 Supervisor 和 Nginx。
> 适用于 2 核 4G 及以上配置的服务器。

## 📋 部署架构

```
用户浏览器 ── HTTPS ──→ Nginx (宝塔Python项目自动生成) ──→ FastAPI (端口自动分配)
                          │                                     ├── LLM API (外部)
                          │                                     ├── RunningHub (云端)
                          │                                     └── MySQL (宝塔自带)
                          │
                          └── 前端 (先通过Node项目构建好，再由FastAPI在/modern提供)
                          └── 视频文件 (output/ 目录)
```

---

## 一、准备工作

### 1.1 宝塔面板安装必要软件

打开宝塔面板 → **软件商店**，安装以下软件：

| 软件 | 备注 |
|------|------|
| **Nginx** | 通常已安装 |
| **MySQL 5.7+ / 8.0+** | 用于用户认证 |
| **Node.js 20+** | 用 **Node.js版本管理器** 安装，用于构建前端 |

> Python **不需要**手动安装 —— 宝塔 **Python项目** 创建时会自动选择合适版本。

### 1.2 SSH 安装系统依赖（FFmpeg + uv）

登录服务器 SSH，执行：

```bash
# 1. 安装 FFmpeg（视频处理必需）
# CentOS/Alibaba Linux
yum install -y ffmpeg

# Ubuntu/Debian
apt-get update && apt-get install -y ffmpeg

# 验证
ffmpeg -version

# 2. 安装 uv（Python 包管理器，比 pip 快 10-100 倍）
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
uv --version

# 国内服务器用 pip 安装 uv 更快：
# pip install -i https://pypi.tuna.tsinghua.edu.cn/simple/ uv
```

---

## 二、方法一：使用宝塔 Python项目部署（推荐）

这是最简洁的方式，宝塔面板会自动处理：虚拟环境、进程守护、Nginx 反向代理。

### 2.1 手动准备项目代码和依赖

先 SSH 登录服务器，手动克隆代码并安装依赖（因为宝塔 Python项目默认用 pip + requirements.txt，而本项目用 uv + pyproject.toml）：

```bash
# 进入宝塔默认网站目录
cd /www/wwwroot

# 克隆项目（你的仓库）
git clone -b modern_ui --single-branch https://ghfast.top/https://github.com/q573927428/Pixelle-Video.git
# 或者：git clone https://github.com/q573927428/Pixelle-Video.git

cd Pixelle-Video

# 创建配置文件
cp .env.example .env
cp config.example.yaml config.yaml
```

### 2.2 配置 .env

你的 `.env` 已经配置好了，确认关键信息：

| 配置项 | 值 |
|--------|-----|
| 域名 | `ai.zuosuo.com` |
| LLM | 火山引擎（豆包模型） |
| RunningHub | 已配置 |
| MySQL | 数据库 `pixelle_video`，用户 `root` |

> ⚠️ **MySQL 注意**：你当前 `.env` 中 `MYSQL_USER=root`，如果宝塔的 MySQL root 有密码策略问题，建议在宝塔面板单独创建一个数据库用户（见第四节）。

### 2.3 配置 config.yaml

编辑 `config.yaml`，填入和 `.env` 一致的密钥：

```yaml
llm:
  api_key: "ark-2d258ea0-623e-4eae-a33e-82c793f1bc2c-78a68"
  base_url: "https://ark.cn-beijing.volces.com/api/v3"
  model: "doubao-seed-2-0-pro-260215"

comfyui:
  runninghub_api_key: "52692e551b47412997f66ce195120f68"
  comfyui_url: http://127.0.0.1:8188
  tts:
    default_workflow: selfhost/tts_edge.json
  image:
    default_workflow: runninghub/image_flux.json
  video:
    default_workflow: runninghub/video_wan2.1_fusionx.json

template:
  default_template: "1080x1920/image_default.html"
```

### 2.4 SSH 安装 Python 依赖（关键步骤）

宝塔 Python项目创建后会自动生成虚拟环境，但依赖需要手动用 uv 安装（因为项目用 `pyproject.toml` 而非 `requirements.txt`）：

```bash
cd /www/wwwroot/Pixelle-Video

# 使用 uv 创建虚拟环境并安装依赖
uv venv

# 安装项目本身及其所有依赖
uv pip install -e .

# 如果国内服务器慢，加镜像：
# uv pip install -e . -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 安装 Playwright 浏览器（用于渲染）
uv run playwright install --with-deps chromium
```

### 2.5 在宝塔面板创建 Python项目

1. **宝塔面板 → 网站 → Python项目 → 添加Python项目**

2. 填写以下信息：

   | 字段 | 值 |
   |------|-----|
   | **项目名称** | `Pixelle-Video` |
   | **项目路径** | `/www/wwwroot/Pixelle-Video` |
   | **Python版本** | 选择 **3.11** 或 **3.12** |
   | **框架** | 选择 **自定义** |
   | **启动方式** | 选择 **uv** 或填命令 |
   | **启动命令** | `uv run python api/app.py --host 127.0.0.1 --port 8000` |
   | **环境变量** | `UV_CACHE_DIR=/www/wwwroot/Pixelle-Video/.uv_cache` |
   | **监听端口** | `8000` |

   > **关于启动命令**：
   > - 如果宝塔 Python项目不支持 uv，可以改用虚拟环境中的 python：
   > - `.venv/bin/python api/app.py --host 127.0.0.1 --port 8000`（Linux）
   > - 或在项目内创建一个 `start.sh` 脚本作为启动文件

3. **提交**，宝塔会自动：
   - ✅ 创建虚拟环境
   - ✅ 设置 Nginx 反向代理
   - ✅ 配置进程守护（开机自启）
   - ✅ 创建日志目录

### 2.6 验证后端

创建完成后，宝塔 Python项目列表会显示运行状态。点击 **日志** 查看启动输出。

也可以直接访问测试：
```
http://你的服务器IP:8000/health
```

如果返回 JSON 状态信息，说明后端运行正常。

---

## 三、构建前端（Node项目）

### 3.1 使用宝塔 Node项目构建（推荐）

1. **宝塔面板 → 网站 → Node项目 → 添加Node项目**

2. 填写：

   | 字段 | 值 |
   |------|-----|
   | **项目名称** | `Pixelle-Video-Frontend` |
   | **项目路径** | `/www/wwwroot/Pixelle-Video/modern_ui` |
   | **Node版本** | 选择 **20+** |
   | **启动命令** | `pnpm build` |
   | **项目备注** | 构建完即可，不需要持续运行 |

3. **提交**，宝塔会自动安装依赖并执行 `pnpm build`

4. 构建成功后，检查产物：
   ```bash
   ls -la /www/wwwroot/Pixelle-Video/modern_ui/dist/
   # 确认有 index.html 和 assets/ 目录
   ```

> **或者** SSH 手动构建：
> ```bash
> cd /www/wwwroot/Pixelle-Video/modern_ui
> npm install -g pnpm
> pnpm install
> pnpm build
> ```

---

## 四、配置 MySQL 数据库

### 4.1 宝塔面板创建数据库

1. **宝塔面板 → 数据库 → 添加数据库**

2. 填写：
   - **数据库名**：`pixelle_video`
   - **用户名**：建议新建一个用户，如 `pixelle_user`（不建议用 root）
   - **密码**：设置密码（如 `Pixelle@2024`）
   - **访问权限**：`localhost`

3. 点击 **提交**

### 4.2 更新 .env 中的数据库配置

记得将 `.env` 中的数据库信息改为你刚创建的用户和密码：

```bash
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_DATABASE=pixelle_video
MYSQL_USER=pixelle_user      # 改为新创建的用户
MYSQL_PASSWORD=Pixelle@2024  # 改为新密码
```

> 项目启动时会自动创建表，无需手动导入 SQL。

---

## 五、修改 Nginx 配置（关键）

宝塔 Python项目会自动生成 Nginx 配置，但本项目需要额外处理前端路径（`/modern` -> `/`）。

### 5.1 找到自动生成的配置

**宝塔面板 → 网站 → Python项目** → 找到 `Pixelle-Video` → 点击 **配置文件**

默认生成的配置类似：

```nginx
server {
    listen 80;
    server_name ai.zuosuo.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # 静态文件处理等...
}
```

### 5.2 替换为完整配置

将配置文件内容替换为以下内容（**保留宝塔自动生成的 SSL 配置部分**）：

```nginx
# HTTP → HTTPS 跳转
server {
    listen 80;
    server_name ai.zuosuo.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ai.zuosuo.com;

    # ====== 以下 SSL 配置请保留宝塔自动生成的部分 ======
    # 宝塔面板会自动管理 SSL 证书，不要删除下面几行：
    # ssl_certificate    /www/server/panel/vhost/cert/ai.zuosuo.com/fullchain.pem;
    # ssl_certificate_key /www/server/panel/vhost/cert/ai.zuosuo.com/privkey.pem;
    # ssl_protocols TLSv1.1 TLSv1.2 TLSv1.3;
    # ... 其他 SSL 配置由宝塔自动管理 ...
    # =================================================

    # 上传大小限制（视频上传需要）
    client_max_body_size 500M;

    # 超时时间
    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;

    # ====== 前端页面（反向代理到 FastAPI 的 /modern 路径） ======
    location / {
        proxy_pass http://127.0.0.1:8000/modern;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 修复前端资源路径：将 /modern/xxx 替换为 /xxx
        sub_filter_once off;
        sub_filter 'href="/modern/' 'href="/';
        sub_filter 'src="/modern/' 'src="/';
        sub_filter 'action="/modern/' 'action="/';
    }

    # 前端静态资源（启用长缓存，提升性能）
    location /assets/ {
        proxy_pass http://127.0.0.1:8000/modern/assets/;
        proxy_set_header Host $host;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # ====== API 接口 ======
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # ====== 健康检查 ======
    location /health {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # ====== API 文档 ======
    location /docs {
        proxy_pass http://127.0.0.1:8000;
    }
    location /openapi.json {
        proxy_pass http://127.0.0.1:8000;
    }
    location /redoc {
        proxy_pass http://127.0.0.1:8000;
    }

    # ====== 视频输出文件（直接提供，不走反向代理，性能更好） ======
    location /output/ {
        alias /www/wwwroot/Pixelle-Video/output/;
        add_header Content-Disposition "inline";
        add_header Cache-Control "public, max-age=3600";
    }

    # ====== 文件上传 ======
    location /files/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_request_buffering off;
    }

    # 禁止访问敏感文件
    location ~ /\. {
        deny all;
    }
    location ~ /config\.yaml$ {
        deny all;
    }
    location ~ /\.env$ {
        deny all;
    }
}
```

> ⚠️ **重要**：
> 1. **不要完全删除宝塔自动生成的 SSL 部分**，只替换 `location` 块
> 2. 或者更简单的方式：在宝塔的 **网站 → Python项目** 设置中，找到 **反向代理** 或 **配置文件**，只修改 `location /` 部分
> 3. 保存后，点击 **重载配置**

### 5.3 配置 SSL 证书

如果还没配置 SSL：
1. **宝塔面板 → 网站 → Python项目** → 找到 `Pixelle-Video`
2. 点击 **SSL** → **Let's Encrypt** → 申请证书（域名 `ai.zuosuo.com`）
3. 申请成功后自动配置

---

## 六、访问服务

| 服务 | 地址 |
|------|------|
| 前端界面 | `https://ai.zuosuo.com` |
| API 文档 | `https://ai.zuosuo.com/docs` |
| 健康检查 | `https://ai.zuosuo.com/health` |
| 后台管理 | `https://ai.zuosuo.com/#/admin`（如果实现了的话） |

---

## 七、更新代码

```bash
cd /www/wwwroot/Pixelle-Video

# 拉取最新代码
git pull

# 更新 Python 依赖
uv pip install -e .

# 重新构建前端
cd modern_ui
pnpm install
pnpm build
cd ..

# 在宝塔 Python项目页面点击 **重启**
```

---

## 八、常见问题

### Q1: 宝塔 Python项目不支持 uv 怎么办？

宝塔 Python项目通常会自动检测并使用 `pip`。对于本项目，有以下方案：

**方案A（推荐）**：在 SSH 中提前用 uv 装好依赖，然后在宝塔 Python项目中设置启动命令时使用虚拟环境的 python：

```bash
# 启动命令改为：
/www/wwwroot/Pixelle-Video/.venv/bin/python api/app.py --host 127.0.0.1 --port 8000
```

**方案B**：生成 requirements.txt 文件，让宝塔自动安装：

```bash
cd /www/wwwroot/Pixelle-Video
uv pip export > requirements.txt
```

然后宝塔 Python项目的 **安装方式** 选择 `pip install -r requirements.txt`（但这样装的是不带项目本身的，可能缺包）

> 方案A更可靠，推荐使用。

### Q2: 502 Bad Gateway

1. 检查宝塔 Python项目状态是否 **运行中**
2. 查看项目 **日志** 是否有报错
3. 检查端口 `8000` 是否被占用：`netstat -tlnp | grep 8000`
4. 如果端口冲突，修改启动命令中的端口号，同时修改 Nginx 配置中的 `proxy_pass`

### Q3: 前端页面空白或样式错乱

1. 确认 `modern_ui/dist/` 目录存在且有内容
2. 确认 Nginx 配置中的 `sub_filter` 是否正确
3. 浏览器按 F12 打开控制台，看有无 404 错误
4. 直接访问 `https://ai.zuosuo.com/modern/` 测试（如果这个能打开，说明是 sub_filter 问题）

### Q4: MySQL 连接失败

1. 宝塔面板确认 MySQL 运行中
2. 确认 `.env` 中的数据库用户、密码与宝塔中创建的一致
3. 如果宝塔 MySQL root 有密码验证问题，建议新建一个专用用户

### Q5: Playwright 安装失败

```bash
# 手动安装
pip install playwright
playwright install chromium
playwright install-deps chromium
```

### Q6: 修改了 Nginx 配置不生效

宝塔面板中修改配置后，记得点击 **重载配置** 或 **重启 Nginx**。
或者在 SSH 中执行：
```bash
nginx -t        # 测试配置是否正确
nginx -s reload  # 重新加载
```

---

## 九、方法二（备选）：HTML项目 + Supervisor

如果不想用 Python项目，也可以用传统方式：

1. **宝塔 → 网站 → 添加站点**（纯静态，域名 `ai.zuosuo.com`）
2. SSH 中手动安装依赖、构建前端
3. 使用 **Supervisor管理器** 守护后端进程
4. 手动修改网站 Nginx 配置（反向代理 + sub_filter）

具体步骤参考 [旧版方案](DEPLOY_LEGACY.md)（已废弃，不推荐）。

---

## 十、参考

- [项目官方部署指南 (Docker)](DEPLOY.md)
- [项目配置文件说明](config.example.yaml)
- [宝塔 Python项目官方文档](https://www.bt.cn/new/bt_python.html)