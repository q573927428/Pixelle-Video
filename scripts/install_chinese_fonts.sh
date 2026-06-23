#!/bin/bash
# =============================================================
# 安装热门免费商用中文字体 (Linux 服务器)
# =============================================================
# 支持的字体：
#   1. 思源黑体 (Source Han Sans SC) - Google/Adobe
#   2. 思源宋体 (Source Han Serif SC) - Google/Adobe
#   3. 阿里巴巴普惠体 (Alibaba PuHuiTi) - 阿里
#   4. 霞鹜文楷 (LXGW WenKai) - 开源手写体
#   5. 未来荧黑 (Wegoe UI) - 开源无衬线体
# =============================================================

set -e

FONT_DIR="/usr/share/fonts/chinese"
mkdir -p "$FONT_DIR"

echo "========================================"
echo "开始安装热门中文字体..."
echo "目标目录: $FONT_DIR"
echo "========================================"

# ---------- 检测包管理器 ----------
install_pkg() {
    if command -v yum &>/dev/null; then
        yum install -y "$@"
    elif command -v apt &>/dev/null; then
        apt install -y "$@"
    elif command -v apk &>/dev/null; then
        apk add "$@"
    elif command -v dnf &>/dev/null; then
        dnf install -y "$@"
    else
        echo "⚠️  未识别的包管理器，跳过系统包安装"
    fi
}

# ---------- 1. 通过系统包管理器安装基础中文字体 ----------
echo ""
echo "[1/5] 通过系统包管理器安装基础中文字体（文泉驿系列）..."
if command -v yum &>/dev/null || command -v dnf &>/dev/null; then
    # CentOS / RHEL / Fedora
    install_pkg wqy-microhei-fonts wqy-zenhei-fonts
elif command -v apt &>/dev/null; then
    # Ubuntu / Debian
    install_pkg fonts-wqy-microhei fonts-wqy-zenhei fonts-noto-cjk
elif command -v apk &>/dev/null; then
    # Alpine
    install_pkg font-wqy-microhei font-noto-cjk
fi

# ---------- 2. 思源黑体 (Noto Sans CJK SC) ----------
echo ""
echo "[2/5] 下载安装思源黑体 Noto Sans CJK SC..."

if [ ! -f "$FONT_DIR/NotoSansSC-Regular.otf" ]; then
    wget -q --show-progress -O /tmp/NotoSansSC.zip \
        "https://github.com/googlefonts/noto-cjk/releases/download/Sans2.004/03_NotoSansCJKsc.zip"
    unzip -q -o /tmp/NotoSansSC.zip -d /tmp/NotoSansSC/
    mkdir -p "$FONT_DIR/NotoSansSC"
    cp /tmp/NotoSansSC/*.otf "$FONT_DIR/NotoSansSC/" 2>/dev/null || true
    # 复制到上层方便查找
    cp "$FONT_DIR/NotoSansSC/NotoSansSC-Regular.otf" "$FONT_DIR/" 2>/dev/null || true
    cp "$FONT_DIR/NotoSansSC/NotoSansSC-Bold.otf" "$FONT_DIR/" 2>/dev/null || true
    rm -rf /tmp/NotoSansSC.zip /tmp/NotoSansSC
    echo "  ✅ 思源黑体安装完成"
else
    echo "  ⏭️  思源黑体已存在，跳过"
fi

# ---------- 3. 思源宋体 (Noto Serif CJK SC) ----------
echo ""
echo "[3/5] 下载安装思源宋体 Noto Serif CJK SC..."

if [ ! -f "$FONT_DIR/NotoSerifSC-Regular.otf" ]; then
    wget -q --show-progress -O /tmp/NotoSerifSC.zip \
        "https://github.com/notofonts/noto-cjk/releases/download/Serif2.002/03_NotoSerifCJKsc.zip"
    unzip -q -o /tmp/NotoSerifSC.zip -d /tmp/NotoSerifSC/
    mkdir -p "$FONT_DIR/NotoSerifSC"
    cp /tmp/NotoSerifSC/*.otf "$FONT_DIR/NotoSerifSC/" 2>/dev/null || true
    cp "$FONT_DIR/NotoSerifSC/NotoSerifSC-Regular.otf" "$FONT_DIR/" 2>/dev/null || true
    cp "$FONT_DIR/NotoSerifSC/NotoSerifSC-Bold.otf" "$FONT_DIR/" 2>/dev/null || true
    rm -rf /tmp/NotoSerifSC.zip /tmp/NotoSerifSC
    echo "  ✅ 思源宋体安装完成"
else
    echo "  ⏭️  思源宋体已存在，跳过"
fi

# ---------- 4. 阿里巴巴普惠体 ----------
echo ""
echo "[4/5] 下载安装阿里巴巴普惠体..."

if [ ! -f "$FONT_DIR/AlibabaPuHuiTi-3-Regular.otf" ]; then
    wget -q --show-progress -O /tmp/AlibabaPuHuiTi.zip \
        "https://puhuiti.oss-cn-hangzhou.aliyuncs.com/AlibabaPuHuiTi-3-105%E5%AD%97%E4%BD%93%E5%8C%85%EF%BC%885.1%20Alibaba%20PuHuiTi%203.105%EF%BC%89.zip"
    unzip -q -o /tmp/AlibabaPuHuiTi.zip -d /tmp/AlibabaPuHuiTi/
    mkdir -p "$FONT_DIR/AlibabaPuHuiTi"
    find /tmp/AlibabaPuHuiTi -name "*.otf" -exec cp {} "$FONT_DIR/AlibabaPuHuiTi/" \; 2>/dev/null || true
    find /tmp/AlibabaPuHuiTi -name "*.ttf" -exec cp {} "$FONT_DIR/AlibabaPuHuiTi/" \; 2>/dev/null || true
    ls "$FONT_DIR/AlibabaPuHuiTi/" 2>/dev/null && {
        cp "$FONT_DIR/AlibabaPuHuiTi/AlibabaPuHuiTi-3-55-Regular.otf" "$FONT_DIR/" 2>/dev/null || true
        cp "$FONT_DIR/AlibabaPuHuiTi/AlibabaPuHuiTi-3-65-Medium.otf" "$FONT_DIR/" 2>/dev/null || true
        echo "  ✅ 阿里巴巴普惠体安装完成"
    } || echo "  ⚠️  阿里巴巴普惠体下载失败（可能需要手动下载）"
    rm -rf /tmp/AlibabaPuHuiTi.zip /tmp/AlibabaPuHuiTi
else
    echo "  ⏭️  阿里巴巴普惠体已存在，跳过"
fi

# ---------- 5. 霞鹜文楷 ----------
echo ""
echo "[5/5] 下载安装霞鹜文楷 LXGW WenKai..."

if [ ! -f "$FONT_DIR/LXGWWenKai-Regular.ttf" ]; then
    wget -q --show-progress -O /tmp/LXGWWenKai.zip \
        "https://github.com/lxgw/LxgwWenKai/releases/download/v1.330/LXGWWenKai-1.330.zip"
    unzip -q -o /tmp/LXGWWenKai.zip -d /tmp/LXGWWenKai/
    mkdir -p "$FONT_DIR/LXGWWenKai"
    find /tmp/LXGWWenKai -name "*.ttf" -exec cp {} "$FONT_DIR/LXGWWenKai/" \; 2>/dev/null || true
    cp "$FONT_DIR/LXGWWenKai/LXGWWenKai-Regular.ttf" "$FONT_DIR/" 2>/dev/null || true
    cp "$FONT_DIR/LXGWWenKai/LXGWWenKai-Bold.ttf" "$FONT_DIR/" 2>/dev/null || true
    rm -rf /tmp/LXGWWenKai.zip /tmp/LXGWWenKai
    echo "  ✅ 霞鹜文楷安装完成"
else
    echo "  ⏭️  霞鹜文楷已存在，跳过"
fi

# ---------- 更新字体缓存 ----------
echo ""
echo "========================================"
echo "更新字体缓存..."
echo "========================================"
fc-cache -fv "$FONT_DIR" 2>/dev/null || {
    # 如果没有 fc-cache，手动创建 fonts.dir
    mkdir -p "$FONT_DIR"
    mkfontscale "$FONT_DIR" 2>/dev/null || true
    mkfontdir "$FONT_DIR" 2>/dev/null || true
}

# ---------- 验证安装结果 ----------
echo ""
echo "========================================"
echo "✅ 安装完成！已安装的中文字体："
echo "========================================"
fc-list :lang=zh 2>/dev/null | sort || {
    echo "(使用 find 方式检测)"
    find "$FONT_DIR" -type f \( -name "*.ttf" -o -name "*.ttc" -o -name "*.otf" \) | sort
}

echo ""
echo "========================================"
echo "现在重启 Pixelle-Video 服务即可使用新字体"
echo "========================================"