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
          <el-button type="primary" size="large" class="hero-btn hero-btn-primary" @click="router.push('/login')">
            登录
          </el-button>
          <el-button size="large" class="hero-btn hero-btn-secondary" @click="router.push('/register')">
            注册
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
            <span class="stat-label">高清输出</span>
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

    <!-- ====== Footer ====== -->
    <footer class="home-footer">
      <p>© 2026 ZuoSuo AI. All rights reserved.</p>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

const features = [
  { icon: '🤖', title: '数字人带货', desc: '上传数字人照片或者人物照片 + 商品图片，AI 自动生成逼真的数字人带货视频，支持口型同步与动作驱动' },
  { icon: '🎤', title: '个人IP口播', desc: '上传人物照片和10秒录音以及一段文案，AI 自动生成栩栩如生的个人IP人物克隆口播视频' },
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
    flex-direction: row;
    gap: 12px;
  }

  .hero-btn {
    height: 42px !important;
    padding: 0 30px !important;
    font-size: 16px !important;
    border-radius: 12px !important;
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
}

@media (max-width: 480px) {
  .hero-title {
    font-size: 36px;
  }
}
</style>