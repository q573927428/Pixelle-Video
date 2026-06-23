#!/bin/bash
# =============================================================
# 安装热门免费商用中文字体 (Linux 服务器)
# =============================================================
# 支持的字体（按优先级）：
#   1. 思源黑体 (Noto Sans SC)  - Google/Adobe 出品
#   2. 思源宋体 (Noto Serif SC) - Google/Adobe 出品
#   3. 阿里巴巴普惠体 (Alibaba PuHuiTi) - 阿里出品
#   4. 霞鹜文楷 (LXGW WenKai) - 开源手写楷体
#   5. 文泉驿微米黑 (WQY Micro Hei) - 开源
# =============================================================
# 使用方法：
#   bash scripts/install_chinese_fonts.sh
# =============================================================

# 不要 set -e，手动处理每个步骤的失败
FONT_DIR="/usr/share/fonts/chinese"
NOTO_DIR="$FONT_DIR/NotoSansSC"
NOTO_SERIF_DIR="$FONT_DIR/NotoSerifSC"
mkdir -p "$FONT_DIR" "$NOTO_DIR" "$NOTO_SERIF_DIR"

echo "========================================"
echo "🎯 开始安装热门中文字体..."
echo "📂 目标目录: $FONT_DIR"
echo "========================================"

# ---------- 1. 思源黑体 (Noto Sans SC) - 最高优先级 ----------
echo ""
echo "[1/5] 思源黑体 Noto Sans SC (Google/Adobe)..."
if [ ! -f "$NOTO_DIR/NotoSansSC-Regular.otf" ]; then
    echo "  ⏳ 正在下载思源黑体..."
    if wget -q --show-progress -O /tmp/NotoSansSC.zip \
        "https://github.com/googlefonts/noto-cjk/releases/download/Sans2.004/03_NotoSansCJKsc.zip"; then
        unzip -q -o /tmp/NotoSansSC.zip -d /tmp/NotoSansSC/ 2>/dev/null
        cp /tmp/NotoSansSC/*.otf "$NOTO_DIR/" 2>/dev/null || true
        cp "$NOTO_DIR/NotoSansSC-Regular.otf" "$FONT_DIR/" 2>/dev/null || true
        cp "$NOTO_DIR/NotoSansSC-Bold.otf" "$FONT_DIR/" 2>/dev/null || true
        rm -rf /tmp/NotoSansSC.zip /tmp/NotoSansSC
        echo "  ✅ 思源黑体安装完成"
    else
        echo "  ⚠️  思源黑体下载失败（GitHub 网络问题），跳过"
    fi
else
    echo "  ⏭️  思源黑体已存在，跳过"
fi

# ---------- 2. 思源宋体 (Noto Serif SC) - 次高优先级 ----------
echo ""
echo "[2/5] 思源宋体 Noto Serif SC (Google/Adobe)..."
if [ ! -f "$NOTO_SERIF_DIR/NotoSerifSC-Regular.otf" ]; then
    echo "  ⏳ 正在下载思源宋体..."
    if wget -q --show-progress -O /tmp/NotoSerifSC.zip \
        "https://github.com/notofonts/noto-cjk/releases/download/Serif2.002/03_NotoSerifCJKsc.zip"; then
        unzip -q -o /tmp/NotoSerifSC.zip -d /tmp/NotoSerifSC/ 2>/dev/null
        cp /tmp/NotoSerifSC/*.otf "$NOTO_SERIF_DIR/" 2>/dev/null || true
        cp "$NOTO_SERIF_DIR/NotoSerifSC-Regular.otf" "$FONT_DIR/" 2>/dev/null || true
        cp "$NOTO_SERIF_DIR/NotoSerifSC-Bold.otf" "$FONT_DIR/" 2>/dev/null || true
        rm -rf /tmp/NotoSerifSC.zip /tmp/NotoSerifSC
        echo "  ✅ 思源宋体安装完成"
    else
        echo "  ⚠️  思源宋体下载失败（GitHub 网络问题），跳过"
    fi
else
    echo "  ⏭️  思源宋体已存在，跳过"
fi

# ---------- 3. 阿里巴巴普惠体 ----------
echo ""
echo "[3/5] 阿里巴巴普惠体 Alibaba PuHuiTi..."
if [ ! -f "$FONT_DIR/AlibabaPuHuiTi-3-55-Regular.otf" ]; then
    echo "  ⏳ 正在下载阿里巴巴普惠体..."
    if wget -q --show-progress -O /tmp/AlibabaPuHuiTi.zip \
        "https://puhuiti.oss-cn-hangzhou.aliyuncs.com/AlibabaPuHuiTi-3-105%E5%AD%97%E4%BD%93%E5%8C%85%EF%BC%885.1%20Alibaba%20PuHuiTi%203.105%EF%BC%89.zip"; then
        mkdir -p /tmp/AlibabaPuHuiTi
        unzip -q -o /tmp/AlibabaPuHuiTi.zip -d /tmp/AlibabaPuHuiTi/ 2>/dev/null || true
        find /tmp/AlibabaPuHuiTi -name "*.otf" -exec cp {} "$FONT_DIR/" \; 2>/dev/null || true
        find /tmp/AlibabaPuHuiTi -name "*.ttf" -exec cp {} "$FONT_DIR/" \; 2>/dev/null || true
        echo "  ✅ 阿里巴巴普惠体安装完成"
        rm -rf /tmp/AlibabaPuHuiTi.zip /tmp/AlibabaPuHuiTi
    else
        echo "  ⚠️  阿里巴巴普惠体下载失败（阿里云 OSS 网络问题），跳过"
    fi
else
    echo "  ⏭️  阿里巴巴普惠体已存在，跳过"
fi

# ---------- 4. 霞鹜文楷 ----------
echo ""
echo "[4/5] 霞鹜文楷 LXGW WenKai (开源手写体)..."
if [ ! -f "$FONT_DIR/LXGWWenKai-Regular.ttf" ]; then
    echo "  ⏳ 正在下载霞鹜文楷..."
    if wget -q --show-progress -O /tmp/LXGWWenKai.zip \
        "https://github.com/lxgw/LxgwWenKai/releases/download/v1.330/LXGWWenKai-1.330.zip"; then
        unzip -q -o /tmp/LXGWWenKai.zip -d /tmp/LXGWWenKai/ 2>/dev/null
        find /tmp/LXGWWenKai -name "*.ttf" -exec cp {} "$FONT_DIR/" \; 2>/dev/null || true
        echo "  ✅ 霞鹜文楷安装完成"
        rm -rf /tmp/LXGWWenKai.zip /tmp/LXGWWenKai
    else
        echo "  ⚠️  霞鹜文楷下载失败（GitHub 网络问题），跳过"
    fi
else
    echo "  ⏭️  霞鹜文楷已存在，跳过"
fi

# ---------- 5. 尝试 via 系统包管理器安装额外字体 ----------
echo ""
echo "[5/5] 通过系统包管理器安装额外字体..."
if command -v yum &>/dev/null; then
    # CentOS / RHEL - wqy 字体在 EPEL 仓库中
    echo "  ⏳ CentOS 系统，尝试安装 EPEL + 文泉驿字体..."
    yum install -y epel-release 2>/dev/null && echo "  ✅ EPEL 已安装" || echo "  ⚠️  EPEL 安装跳过"
    yum install -y wqy-microhei-fonts wqy-zenhei-fonts 2>/dev/null && echo "  ✅ 文泉驿字体已安装" || echo "  ⚠️  文泉驿字体不可用（不影响已有字体）"
    yum install -y google-noto-cjk-fonts 2>/dev/null && echo "  ✅ Noto CJK 已安装" || echo "  ⚠️  Noto CJK 不可用"
elif command -v apt &>/dev/null; then
    echo "  ⏳ Debian/Ubuntu 系统，安装字体包..."
    apt install -y fonts-wqy-microhei fonts-wqy-zenhei fonts-noto-cjk 2>/dev/null && echo "  ✅ 字体包已安装" || echo "  ⚠️  部分字体包安装失败"
elif command -v apk &>/dev/null; then
    echo "  ⏳ Alpine 系统，安装字体包..."
    apk add font-wqy-microhei font-noto-cjk 2>/dev/null && echo "  ✅ 字体包已安装" || echo "  ⚠️  部分字体包安装失败"
fi

# ---------- 更新字体缓存 ----------
echo ""
echo "========================================"
echo "🔄 更新字体缓存..."
echo "========================================"
fc-cache -fv "$FONT_DIR" 2>/dev/null || echo "  (fc-cache 不可用，跳过)"
fc-cache -f 2>/dev/null || true

# ---------- 验证安装结果 ----------
echo ""
echo "========================================"
echo "✅ 安装完成！已安装的中文字体："
echo "========================================"
if command -v fc-list &>/dev/null; then
    fc-list :lang=zh 2>/dev/null | sort || echo "  (无中文字体)"
fi

echo ""
echo "📁 $FONT_DIR 目录内容："
find "$FONT_DIR" -type f \( -name "*.ttf" -o -name "*.ttc" -o -name "*.otf" \) 2>/dev/null | sort || echo "  (空)"

echo ""
echo "========================================"
echo "🎉 安装完毕！请重启 Pixelle-Video 服务："
echo "   supervisorctl restart pixelle-video"
echo "========================================"