<template>
  <div class="home-wrapper">
    <!-- ====== Hero Section ====== -->
    <section class="hero-section">
      <div class="hero-bg-glow"></div>
      <div class="hero-content">
        <div class="hero-logo">🎬</div>
        <h1 class="hero-title">
          <span>ZuoSuo AI</span>
        </h1>
        <p class="hero-subtitle">
          基于 AI 的视频创作平台 · 智能生成数字人 · 快速制作精彩视频
        </p>

        <div class="hero-actions">
          <el-button type="primary" size="large" class="hero-btn hero-btn-primary" @click="$emit('show-login')">
            立即登录
          </el-button>
          <el-button size="large" class="hero-btn hero-btn-secondary" @click="$emit('show-register')">
            免费注册
          </el-button>
        </div>

        <div class="hero-stats">
          <div class="stat-item">
            <span class="stat-value">AI 驱动</span>
            <span class="stat-label">智能视频生成</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item">
            <span class="stat-value">高清画质</span>
            <span class="stat-label">1080P 输出</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item">
            <span class="stat-value">快速渲染</span>
            <span class="stat-label">分钟级生成</span>
          </div>
        </div>
      </div>
    </section>

    <!-- ====== Features Section ====== -->
    <section class="section features-section">
      <div class="section-header">
        <h2 class="section-title">核心功能</h2>
        <p class="section-desc">一站式 AI 视频创作工具，满足您的多元创作需求</p>
      </div>
      <div class="features-grid">
        <div v-for="feature in features" :key="feature.title" class="feature-card">
          <div class="feature-icon-wrapper">
            <span class="feature-icon">{{ feature.icon }}</span>
          </div>
          <h3 class="feature-title">{{ feature.title }}</h3>
          <p class="feature-desc">{{ feature.desc }}</p>
        </div>
      </div>
    </section>

    <!-- ====== Video Showcase Section ====== -->
    <section class="section showcase-section">
      <div class="section-header">
        <h2 class="section-title">效果展示</h2>
        <p class="section-desc">看看 AI 生成的精彩视频效果</p>
      </div>

      <!-- Portrait Videos (竖屏 4 个) -->
      <div class="showcase-group">
        <h3 class="showcase-group-title">📱 竖屏视频</h3>
        <div class="showcase-grid portrait-grid">
          <div
            v-for="item in portraitVideos"
            :key="item.title"
            class="showcase-card showcase-card-portrait"
          >
            <div class="showcase-card-header">
              <span class="showcase-card-icon">{{ item.icon }}</span>
              <span class="showcase-card-title">{{ item.title }}</span>
            </div>
            <div class="showcase-video-wrapper portrait-wrapper">
              <video
                :src="item.src"
                :poster="item.poster"
                class="showcase-video"
                muted
                loop
                controls
                playsinline
                preload="metadata"
              ></video>
              <div class="showcase-video-overlay">
                <el-icon class="play-icon"><VideoPlay /></el-icon>
              </div>
            </div>
            <p class="showcase-card-desc">{{ item.desc }}</p>
          </div>
        </div>
      </div>

      <!-- Landscape Videos (横屏 3 个) -->
      <div class="showcase-group">
        <h3 class="showcase-group-title">🖥️ 横屏视频</h3>
        <div class="showcase-grid landscape-grid">
          <div
            v-for="item in landscapeVideos"
            :key="item.title"
            class="showcase-card showcase-card-landscape"
          >
            <div class="showcase-card-header">
              <span class="showcase-card-icon">{{ item.icon }}</span>
              <span class="showcase-card-title">{{ item.title }}</span>
            </div>
            <div class="showcase-video-wrapper landscape-wrapper">
              <video
                :src="item.src"
                :poster="item.poster"
                class="showcase-video"
                muted
                loop
                controls
                playsinline
                preload="metadata"
              ></video>
              <div class="showcase-video-overlay">
                <el-icon class="play-icon"><VideoPlay /></el-icon>
              </div>
            </div>
            <p class="showcase-card-desc">{{ item.desc }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- ====== Plans / VIP Comparison ====== -->
    <section class="section plans-section">
      <div class="section-header">
        <h2 class="section-title">选择您的方案</h2>
        <p class="section-desc">适合各类创作者的价格方案</p>
      </div>

      <div class="plans-grid">
        <!-- Free Plan (左列) -->
        <div class="plan-card plan-free">
          <div class="plan-badge">免费</div>
          <div class="plan-header">
            <h3 class="plan-name">普通用户</h3>
            <div class="plan-price">
              <span class="price-value">免费</span>
            </div>
            <p class="plan-desc">体验基础 AI 视频创作功能</p>
          </div>
          <ul class="plan-features">
            <li v-for="item in freePlan" :key="item" class="plan-feature-item">
              <el-icon><Check /></el-icon>
              <span>{{ item }}</span>
            </li>
          </ul>
          <el-button class="plan-btn" @click="$emit('show-register')">免费注册</el-button>
        </div>

        <!-- VIP Plan (中列 - 最突出) -->
        <div class="plan-card plan-vip">
          <div class="plan-badge plan-badge-vip">🔥 超高性价比</div>
          <div class="plan-header">
            <h3 class="plan-name">VIP 会员</h3>
            <div class="plan-price">
              <div class="price-original-row">
                <span class="price-original">¥788</span>
                <span class="price-period">/年</span>
              </div>
              <div class="price-current-row">
                <span class="price-currency">¥</span>
                <span class="price-value">388</span>
                <span class="price-period">/年</span>
                <span class="price-save">省 ¥400</span>
              </div>
            </div>
            <p class="plan-desc">解锁全部功能，畅享无限制创作</p>
          </div>
          <ul class="plan-features">
            <li v-for="item in vipPlan" :key="item" class="plan-feature-item plan-feature-vip">
              <el-icon><Check /></el-icon>
              <span>{{ item }}</span>
            </li>
          </ul>
          <el-button type="primary" class="plan-btn plan-btn-vip" @click="$emit('show-login')">开通 VIP</el-button>
        </div>

        <!-- WeChat Plan (右列 - 微信联系) -->
        <div class="plan-card plan-wechat">
          <div class="plan-badge plan-badge-wechat">💬 联系我们</div>
          <div class="plan-header">
            <h3 class="plan-name">添加微信</h3>
            <div class="plan-price">
              <span class="price-value wechat-price">享优惠</span>
            </div>
            <p class="plan-desc">添加好友，获取专属服务和优惠</p>
          </div>
          <ul class="plan-features plan-features-wechat">
            <li class="plan-feature-item">
              <el-icon style="color:#07c160;"><Discount /></el-icon>
              <span>微信专享价 <strong style="color:#e6a23c;">¥358/年</strong>（省¥30）</span>
            </li>
            <li class="plan-feature-item">
              <el-icon style="color:#07c160;"><MagicStick /></el-icon>
              <span>赠送 <strong>3天</strong> 免费体验</span>
            </li>
          </ul>

          <!-- QR Code + WeChat ID 合并在一行 -->
          <div class="wechat-qr-row">
            <img src="/wechat.png" alt="微信二维码" class="wechat-qr-img" />
            <div class="wechat-qr-right">
              <div class="wechat-info-row">
                <el-icon style="color:#07c160; font-size:16px;"><ChatLineSquare /></el-icon>
                <span class="wechat-id-text">zhuxixy</span>
                <el-button size="small" type="success" plain class="wechat-copy-btn" @click="copyWechatId">
                  复制
                </el-button>
              </div>
              <div class="wechat-qr-label">长按或扫码添加好友</div>
            </div>
          </div>

          <div class="wechat-hint">
            <el-icon style="margin-right:4px;"><InfoFilled /></el-icon>
            备注"AI视频"享专属福利
          </div>
        </div>
      </div>
    </section>

    <!-- ====== CTA Section ====== -->
    <section class="section cta-section">
      <div class="cta-card">
        <h2 class="cta-title">准备好开始创作了吗？</h2>
        <p class="cta-desc">立即注册，释放您的创意潜能</p>
        <div class="cta-actions">
          <el-button type="primary" size="large" class="cta-btn" @click="$emit('show-register')">
            免费注册
          </el-button>
          <el-button size="large" class="cta-btn cta-btn-outline" @click="$emit('show-login')">
            登录
          </el-button>
        </div>
      </div>
    </section>

    <!-- ====== Footer ====== -->
    <footer class="home-footer">
      <p>© 2026 ZuoSuo AI. All rights reserved.</p>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { Check, ChatLineSquare, VideoPlay, ChatDotSquare, Discount, MagicStick, Clock, InfoFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

defineEmits<{
  (e: 'show-login'): void
  (e: 'show-register'): void
}>()

async function copyWechatId() {
  try {
    await navigator.clipboard.writeText('zhuxixy')
    ElMessage.success('微信号已复制')
  } catch {
    ElMessage.warning('复制失败，请手动记下微信号：zhuxixy')
  }
}

const features = [
  { icon: '🤖', title: '数字人带货', desc: '上传数字人照片或者人物照片 + 商品图片，AI 自动生成逼真的数字人带货视频，支持口型同步与动作驱动' },
  { icon: '🎤', title: '个人IP口播', desc: '上传人物照片和10秒录音以及一段文案，AI 自动生成栩栩如生的个人IP人物克隆口播视频' },
  { icon: '🔄', title: '动作迁移', desc: '将参考视频中的人物动作迁移到目标人物上，实现精准的动作复制与风格转换' },
  { icon: '🎨', title: '图生视频', desc: '将静态图片转化为动态视频，赋予图像生命力与故事性' },
]

// ── 竖屏视频展示数据（9:16） ──
const portraitVideos = [
  {
    icon: '👤',
    title: '数字人带货',
    src: '/modern/videos/shu-01.mp4',
    poster: '',
    desc: '数字人带货视频',
  },
  {
    icon: '🎤',
    title: '个人IP口播',
    src: '/modern/videos/shu-05.mp4',
    poster: '',
    desc: '个人IP语音克隆口播视频',
  },
  {
    icon: '🔄',
    title: '动作迁移',
    src: '/modern/videos/shu-03.mp4',
    poster: '',
    desc: '舞蹈动作迁移效果',
  },
  {
    icon: '🎨',
    title: '图生视频',
    src: '/modern/videos/shu-02.mp4',
    poster: '',
    desc: '人像照片转动态视频',
  },
]

// ── 横屏视频展示数据（16:9） ──
const landscapeVideos = [
  {
    icon: '🎬',
    title: '副业赚钱 - 电影模板',
    src: '/modern/videos/heng-01.mp4',
    poster: '',
    desc: 'AI 副业赚钱',
  },
  {
    icon: '🗣️',
    title: '历史解说',
    src: '/modern/videos/heng-02.mp4',
    poster: '',
    desc: '资治通鉴启示录',
  },
  {
    icon: '📖',
    title: '情感类书单 - 克隆音色',
    src: '/modern/videos/heng-05.mp4',
    poster: '',
    desc: '冬日暖阳,情感类人物音色克隆',
  },
]

const freePlan = [
  '每日 3 次视频生成',
  '720P 基础画质输出',
  '基础数字人模板',
  '标准渲染队列',
  '社区支持',
]

const vipPlan = [
  '无限次视频生成',
  '1080P 超清画质输出',
  '全部数字人模板解锁',
  '优先渲染队列',
  '专属技术支持',
  '新功能抢先体验',
]
</script>

<style scoped>
/* ====== Global Layout ====== */
.home-wrapper {
  min-height: 100vh;
  overflow-x: hidden;
}

.section {
  max-width: 1200px;
  margin: 0 auto;
  padding: 100px 24px;
}

.section-header {
  text-align: center;
  margin-bottom: 64px;
}

.section-title {
  font-size: 40px;
  font-weight: 950;
  letter-spacing: -0.04em;
  margin: 0 0 16px;
  background: linear-gradient(135deg, #fff 0%, #a78bfa 50%, #67e8f9 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.section-desc {
  font-size: 18px;
  color: var(--muted, #94a3b8);
  margin: 0;
}

/* ====== Hero ====== */
.hero-section {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 120px 24px 80px;
  overflow: hidden;
}

.hero-bg-glow {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 800px;
  height: 800px;
  transform: translate(-50%, -50%);
  background: radial-gradient(circle, rgba(124, 58, 237, 0.25) 0%, rgba(6, 182, 212, 0.12) 40%, transparent 70%);
  pointer-events: none;
}

.hero-content {
  position: relative;
  text-align: center;
  max-width: 900px;
  z-index: 1;
}

.hero-logo {
  font-size: 80px;
  margin-bottom: 24px;
  filter: drop-shadow(0 20px 60px rgba(124, 58, 237, 0.4));
}

.hero-title {
  font-size: clamp(48px, 6vw, 72px);
  font-weight: 950;
  letter-spacing: -0.04em;
  margin: 0 0 24px;
  line-height: 1.08;
}

.hero-title span {
  background: linear-gradient(135deg, #fff 0%, #a78bfa 50%, #67e8f9 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.hero-subtitle {
  font-size: clamp(16px, 2vw, 22px);
  color: var(--muted, #94a3b8);
  margin: 0 0 48px;
  line-height: 1.6;
}

.hero-actions {
  display: flex;
  gap: 16px;
  justify-content: center;
  margin-bottom: 64px;
}

.hero-btn {
  height: 56px !important;
  padding: 0 40px !important;
  font-size: 18px !important;
  font-weight: 800 !important;
  border-radius: 16px !important;
}

.hero-btn-primary {
  --el-button-bg-color: #7c3aed !important;
  --el-button-border-color: #7c3aed !important;
  --el-button-hover-bg-color: #6d28d9 !important;
  --el-button-hover-border-color: #6d28d9 !important;
}

.hero-btn-secondary {
  background: rgba(255, 255, 255, 0.08) !important;
  border: 1px solid rgba(255, 255, 255, 0.18) !important;
  color: #e5eefb !important;
}

.hero-btn-secondary:hover {
  background: rgba(255, 255, 255, 0.14) !important;
  border-color: rgba(255, 255, 255, 0.3) !important;
}

.hero-stats {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 48px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-value {
  font-size: 20px;
  font-weight: 900;
  color: #e5eefb;
}

.stat-label {
  font-size: 14px;
  color: var(--muted, #94a3b8);
}

.stat-divider {
  width: 1px;
  height: 48px;
  background: rgba(148, 163, 184, 0.25);
}

/* ====== Features ====== */
.features-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px;
}

.feature-card {
  padding: 32px;
  border: 1px solid rgba(148, 163, 184, 0.15);
  border-radius: 20px;
  background: rgba(15, 23, 42, 0.5);
  backdrop-filter: blur(12px);
  transition: transform 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease;
}

.feature-card:hover {
  transform: translateY(-4px);
  border-color: rgba(125, 211, 252, 0.35);
  box-shadow: 0 24px 60px rgba(124, 58, 237, 0.15);
}

.feature-icon-wrapper {
  width: 56px;
  height: 56px;
  display: grid;
  place-items: center;
  border-radius: 16px;
  background: linear-gradient(135deg, rgba(124, 58, 237, 0.25), rgba(6, 182, 212, 0.15));
  margin-bottom: 20px;
}

.feature-icon {
  font-size: 28px;
}

.feature-title {
  font-size: 20px;
  font-weight: 900;
  margin: 0 0 12px;
  color: #e5eefb;
}

.feature-desc {
  font-size: 14px;
  line-height: 1.7;
  color: var(--muted, #94a3b8);
  margin: 0;
}

/* ====== Showcase Section ====== */
.showcase-section {
  padding-bottom: 40px;
}

.showcase-group {
  margin-bottom: 56px;
}

.showcase-group:last-child {
  margin-bottom: 0;
}

.showcase-group-title {
  font-size: 22px;
  font-weight: 900;
  color: #e5eefb;
  margin: 0 0 28px;
  letter-spacing: -0.02em;
}

.showcase-grid {
  display: grid;
  gap: 24px;
}

.portrait-grid {
  grid-template-columns: repeat(4, 1fr);
}

.landscape-grid {
  grid-template-columns: repeat(3, 1fr);
}

.showcase-card {
  border: 1px solid rgba(148, 163, 184, 0.15);
  border-radius: 20px;
  background: rgba(15, 23, 42, 0.5);
  backdrop-filter: blur(12px);
  overflow: hidden;
  transition: transform 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease;
}

.showcase-card:hover {
  transform: translateY(-4px);
  border-color: rgba(125, 211, 252, 0.35);
  box-shadow: 0 24px 60px rgba(124, 58, 237, 0.15);
}

.showcase-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px 20px 0;
}

.showcase-card-icon {
  font-size: 20px;
  line-height: 1;
}

.showcase-card-title {
  font-size: 16px;
  font-weight: 800;
  color: #e5eefb;
  letter-spacing: -0.02em;
}

.showcase-video-wrapper {
  position: relative;
  margin: 12px 12px 0;
  border-radius: 12px;
  overflow: hidden;
  background: rgba(0, 0, 0, 0.4);
  cursor: pointer;
}

.portrait-wrapper {
  aspect-ratio: 9 / 16;
}

.landscape-wrapper {
  aspect-ratio: 16 / 9;
}

.showcase-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.showcase-video-overlay {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  background: rgba(0, 0, 0, 0.25);
  opacity: 0;
  transition: opacity 0.25s ease;
  pointer-events: none;
}

.showcase-video-wrapper:hover .showcase-video-overlay {
  opacity: 1;
}

.play-icon {
  font-size: 48px;
  color: rgba(255, 255, 255, 0.85);
  filter: drop-shadow(0 4px 16px rgba(0, 0, 0, 0.5));
}

.showcase-card-desc {
  font-size: 13px;
  color: var(--muted, #94a3b8);
  margin: 0;
  padding: 12px 20px 18px;
  line-height: 1.5;
}

/* ====== Plans ====== */
.plans-grid {
  display: grid;
  grid-template-columns: 1fr 1.2fr 1fr;
  gap: 24px;
  max-width: 1100px;
  margin: 0 auto;
  align-items: start;
}

.plan-card {
  padding: 44px 32px;
  border: 1px solid rgba(148, 163, 184, 0.15);
  border-radius: 24px;
  background: rgba(15, 23, 42, 0.5);
  backdrop-filter: blur(12px);
  position: relative;
  transition: transform 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease;
  display: flex;
  flex-direction: column;
}

.plan-card:hover {
  transform: translateY(-4px);
}

/* ── VIP 中列最突出 ── */
.plan-vip {
  border-color: rgba(124, 58, 237, 0.35);
  background: linear-gradient(135deg, rgba(124, 58, 237, 0.15), rgba(6, 182, 212, 0.1));
  transform: scale(1.05);
  z-index: 2;
  padding: 52px 36px;
  box-shadow: 0 0 40px rgba(124, 58, 237, 0.15);
}

.plan-vip:hover {
  transform: scale(1.05) translateY(-4px);
  border-color: rgba(124, 58, 237, 0.6);
  box-shadow: 0 24px 60px rgba(124, 58, 237, 0.25);
}

/* ── 微信卡绿色主题 ── */
.plan-wechat {
  border-color: rgba(7, 193, 96, 0.25);
  background: linear-gradient(135deg, rgba(7, 193, 96, 0.08), rgba(6, 182, 212, 0.05));
}

.plan-wechat:hover {
  border-color: rgba(7, 193, 96, 0.5);
  box-shadow: 0 24px 60px rgba(7, 193, 96, 0.12);
}

/* ── Badges ── */
.plan-badge {
  display: inline-block;
  padding: 6px 16px;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.15);
  color: var(--muted, #94a3b8);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  margin-bottom: 24px;
}

.plan-badge-vip {
  background: linear-gradient(135deg, rgba(124, 58, 237, 0.35), rgba(6, 182, 212, 0.25));
  color: #c4b5fd;
}

.plan-badge-wechat {
  background: rgba(7, 193, 96, 0.15);
  color: #07c160;
}

/* ── Header ── */
.plan-header {
  margin-bottom: 28px;
}

.plan-name {
  font-size: 24px;
  font-weight: 900;
  margin: 0 0 16px;
  color: #e5eefb;
}

.plan-price {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 12px;
}

.price-original-row {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.price-original {
  font-size: 18px;
  font-weight: 700;
  color: #64748b;
  text-decoration: line-through;
}

.price-current-row {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.price-currency {
  font-size: 24px;
  font-weight: 950;
  color: #e6a23c;
}

.price-value {
  font-size: 42px;
  font-weight: 950;
  color: #e6a23c;
  letter-spacing: -0.04em;
  line-height: 1;
}

.wechat-price {
  font-size: 32px;
  font-weight: 900;
  color: #07c160;
  letter-spacing: 0;
}

.price-period {
  font-size: 16px;
  color: var(--muted, #94a3b8);
}

.price-save {
  font-size: 12px;
  font-weight: 700;
  color: #22c55e;
  background: rgba(34, 197, 94, 0.12);
  padding: 2px 8px;
  border-radius: 4px;
  margin-left: 6px;
}

.plan-desc {
  font-size: 14px;
  color: var(--muted, #94a3b8);
  margin: 0;
  line-height: 1.5;
}

/* ── Features List ── */
.plan-features {
  list-style: none;
  padding: 0;
  margin: 0 0 36px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  flex: 1;
}

.plan-features-wechat {
  margin-bottom: 20px;
}

.plan-feature-item {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 15px;
  color: #cbd5e1;
}

.plan-feature-item .el-icon {
  color: #22c55e;
  font-size: 18px;
  flex-shrink: 0;
}

.plan-feature-vip .el-icon {
  color: #a78bfa;
}

/* ── Buttons ── */
.plan-btn {
  width: 100%;
  height: 48px !important;
  font-size: 16px !important;
  font-weight: 800 !important;
  border-radius: 14px !important;
  margin-top: auto;
}

.plan-btn-vip {
  --el-button-bg-color: #7c3aed !important;
  --el-button-border-color: #7c3aed !important;
  --el-button-hover-bg-color: #6d28d9 !important;
  --el-button-hover-border-color: #6d28d9 !important;
}

/* ── WeChat Card Specific ── */
.wechat-qr-row {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 14px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 12px;
  border: 1px solid rgba(7, 193, 96, 0.12);
  margin-bottom: 14px;
}

.wechat-qr-img {
  width: 86px;
  height: 86px;
  border-radius: 8px;
  border: 2px solid #07c160;
  flex-shrink: 0;
}

.wechat-qr-right {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
}

.wechat-qr-label {
  font-size: 12px;
  color: #aaa;
}

.wechat-info-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  flex-wrap: wrap;
  margin-bottom: 0;
  justify-content: flex-start;
}

.wechat-id-text {
  color: #07c160;
  font-weight: 700;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
  transition: background 0.2s;
}

.wechat-id-text:hover {
  background: rgba(7, 193, 96, 0.1);
}

.wechat-copy-btn {
  height: 26px !important;
  font-size: 11px !important;
  padding: 0 8px !important;
  border-radius: 6px !important;
}

.wechat-hint {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: #888;
  background: rgba(255, 255, 255, 0.02);
  padding: 7px 12px;
  border-radius: 8px;
  border: 1px dashed rgba(255, 255, 255, 0.06);
  margin-top: auto;
}

/* ====== CTA ====== */
.cta-section {
  padding-bottom: 80px;
}

.cta-card {
  text-align: center;
  padding: 80px 48px;
  border-radius: 32px;
  border: 1px solid rgba(148, 163, 184, 0.15);
  background: linear-gradient(135deg, rgba(124, 58, 237, 0.15), rgba(6, 182, 212, 0.1));
  backdrop-filter: blur(12px);
  position: relative;
  overflow: hidden;
}

.cta-card::before {
  content: '';
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle, rgba(124, 58, 237, 0.08) 0%, transparent 60%);
  pointer-events: none;
}

.cta-title {
  font-size: 36px;
  font-weight: 950;
  margin: 0 0 16px;
  color: #e5eefb;
  letter-spacing: -0.04em;
}

.cta-desc {
  font-size: 18px;
  color: var(--muted, #94a3b8);
  margin: 0 0 36px;
}

.cta-actions {
  display: flex;
  gap: 16px;
  justify-content: center;
}

.cta-btn {
  height: 56px !important;
  padding: 0 40px !important;
  font-size: 18px !important;
  font-weight: 800 !important;
  border-radius: 16px !important;
  position: relative;
}

.cta-btn-outline {
  background: rgba(255, 255, 255, 0.08) !important;
  border: 1px solid rgba(255, 255, 255, 0.18) !important;
  color: #e5eefb !important;
}

.cta-btn-outline:hover {
  background: rgba(255, 255, 255, 0.14) !important;
  border-color: rgba(255, 255, 255, 0.3) !important;
}

/* ====== Footer ====== */
.home-footer {
  text-align: center;
  padding: 32px 24px;
  border-top: 1px solid rgba(148, 163, 184, 0.1);
  color: var(--muted, #64748b);
  font-size: 14px;
}

.home-footer p {
  margin: 0;
}

/* ====== Responsive ====== */
@media (max-width: 1100px) {
  .plans-grid {
    grid-template-columns: 1fr 1fr;
    max-width: 700px;
    gap: 24px;
  }

  .plan-vip {
    transform: none;
    padding: 44px 32px;
  }

  .plan-vip:hover {
    transform: translateY(-4px);
  }

  .plan-wechat {
    grid-column: 1 / -1;
    max-width: 500px;
    margin: 0 auto;
  }
}

@media (max-width: 768px) {
  .section {
    padding: 60px 20px;
  }

  .section-title {
    font-size: 32px;
  }

  .hero-section {
    min-height: auto;
    padding: 80px 20px 60px;
  }

  .hero-logo {
    font-size: 56px;
  }

  .hero-actions {
    flex-direction: column;
    align-items: center;
  }

  .hero-stats {
    flex-direction: column;
    gap: 16px;
  }

  .stat-divider {
    width: 48px;
    height: 1px;
  }

  .features-grid {
    grid-template-columns: 1fr;
  }

  .plans-grid {
    grid-template-columns: 1fr;
    max-width: 450px;
  }

  .plan-wechat {
    grid-column: auto;
    max-width: none;
  }

  .cta-card {
    padding: 48px 24px;
  }

  .cta-actions {
    flex-direction: column;
    align-items: center;
  }

  .portrait-grid {
    grid-template-columns: 1fr 1fr;
  }

  .landscape-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 480px) {
  .hero-title {
    font-size: 36px;
  }

  .plan-card {
    padding: 32px 24px;
  }

  .portrait-grid {
    grid-template-columns: 1fr;
  }
}
</style>