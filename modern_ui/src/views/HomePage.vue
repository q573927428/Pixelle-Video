<template>
  <div class="home-wrapper">
    <!-- ====== Hero Section ====== -->
    <section class="hero-section">
      <div class="hero-bg-glow"></div>
      <div class="hero-content">
        <div class="hero-logo">🎬</div>
        <h1 class="hero-title">
          <span>Pixelle Studio</span>
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

    <!-- ====== Plans / VIP Comparison ====== -->
    <section class="section plans-section">
      <div class="section-header">
        <h2 class="section-title">选择您的方案</h2>
        <p class="section-desc">普通用户与 VIP 会员权益对比</p>
      </div>

      <div class="plans-grid">
        <!-- Free Plan -->
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

        <!-- VIP Plan -->
        <div class="plan-card plan-vip">
          <div class="plan-badge plan-badge-vip">VIP 推荐</div>
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

          <!-- WeChat Discount -->
          <div class="vip-wechat-tip">
            <el-icon style="margin-right:4px"><ChatLineSquare /></el-icon>
            🎉 <strong>添加微信优惠30元</strong>，仅需 <strong style="color:#e6a23c;">¥358</strong>
          </div>

          <!-- WeChat QR Code -->
          <div class="vip-qr-section">
            <img src="/wechat.png" alt="微信二维码" class="vip-qr-img" />
            <div class="vip-wechat-info">
              <el-icon style="margin-right:4px; color:#07c160;"><ChatLineSquare /></el-icon>
              <span>微信号：</span>
              <span class="vip-wechat-id">Pixelle_VIP</span>
              <el-button size="small" type="success" plain style="margin-left:8px;" @click="copyWechatId">
                复制微信号
              </el-button>
            </div>
            <div class="vip-wechat-hint">长按或扫码添加微信，付款后开通 VIP</div>
          </div>

          <el-button type="primary" class="plan-btn plan-btn-vip" @click="$emit('show-login')">开通 VIP</el-button>
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
      <p>© 2026 Pixelle Studio. All rights reserved.</p>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { Check, ChatLineSquare } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

defineEmits<{
  (e: 'show-login'): void
  (e: 'show-register'): void
}>()

async function copyWechatId() {
  try {
    await navigator.clipboard.writeText('Pixelle_VIP')
    ElMessage.success('微信号已复制')
  } catch {
    ElMessage.warning('复制失败，请手动记下微信号：Pixelle_VIP')
  }
}

const features = [
  { icon: '🤖', title: 'AI 数字人', desc: '上传照片或视频，AI 自动生成逼真的数字人，支持口型同步与动作驱动' },
  { icon: '⚡', title: '快速创作', desc: '通过简单的文字描述或素材上传，快速生成高质量视频内容' },
  { icon: '🎨', title: '素材创作', desc: '强大的素材处理能力，支持图片、视频、音频等多种素材的智能编辑' },
  { icon: '🎥', title: '图生视频', desc: '将静态图片转化为动态视频，赋予图像生命力与故事性' },
  { icon: '💃', title: '动作迁移', desc: '将参考视频中的动作迁移到目标人物上，实现动作复制与风格转换' },
  { icon: '📊', title: '任务管理', desc: '完善的视频任务管理系统，实时追踪生成进度，轻松管理历史记录' },
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
  grid-template-columns: repeat(3, 1fr);
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

/* ====== Plans ====== */
.plans-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 32px;
  max-width: 900px;
  margin: 0 auto;
}

.plan-card {
  padding: 48px 36px;
  border: 1px solid rgba(148, 163, 184, 0.15);
  border-radius: 24px;
  background: rgba(15, 23, 42, 0.5);
  backdrop-filter: blur(12px);
  position: relative;
  transition: transform 0.25s ease, border-color 0.25s ease;
}

.plan-card:hover {
  transform: translateY(-4px);
}

.plan-vip {
  border-color: rgba(124, 58, 237, 0.35);
  background: linear-gradient(135deg, rgba(124, 58, 237, 0.12), rgba(6, 182, 212, 0.08));
}

.plan-vip:hover {
  border-color: rgba(124, 58, 237, 0.6);
  box-shadow: 0 24px 60px rgba(124, 58, 237, 0.2);
}

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

.plan-header {
  margin-bottom: 32px;
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

.plan-features {
  list-style: none;
  padding: 0;
  margin: 0 0 36px;
  display: flex;
  flex-direction: column;
  gap: 14px;
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

.plan-btn {
  width: 100%;
  height: 48px !important;
  font-size: 16px !important;
  font-weight: 800 !important;
  border-radius: 14px !important;
}

.plan-btn-vip {
  --el-button-bg-color: #7c3aed !important;
  --el-button-border-color: #7c3aed !important;
  --el-button-hover-bg-color: #6d28d9 !important;
  --el-button-hover-border-color: #6d28d9 !important;
}

.vip-wechat-tip {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  color: #e6a23c;
  background: rgba(230, 162, 60, 0.08);
  padding: 10px;
  border-radius: 8px;
  margin-bottom: 16px;
  border: 1px dashed rgba(230, 162, 60, 0.3);
}

.vip-qr-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.02);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  margin-bottom: 20px;
}

.vip-qr-img {
  width: 140px;
  height: 140px;
  border-radius: 8px;
  border: 2px solid #07c160;
}

.vip-wechat-info {
  display: flex;
  align-items: center;
  font-size: 14px;
  color: #ddd;
}

.vip-wechat-id {
  color: #07c160;
  font-weight: 700;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
  transition: background 0.2s;
}

.vip-wechat-id:hover {
  background: rgba(7, 193, 96, 0.1);
}

.vip-wechat-hint {
  font-size: 12px;
  color: #999;
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
@media (max-width: 1024px) {
  .features-grid {
    grid-template-columns: repeat(2, 1fr);
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
  }

  .cta-card {
    padding: 48px 24px;
  }

  .cta-actions {
    flex-direction: column;
    align-items: center;
  }
}

@media (max-width: 480px) {
  .hero-title {
    font-size: 36px;
  }

  .plan-card {
    padding: 32px 24px;
  }
}
</style>