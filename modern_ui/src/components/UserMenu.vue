<template>
  <div class="user-menu" v-if="auth.isLoggedIn.value">
    <div class="user-row">
      <div class="user-avatar">{{ auth.currentUser.value?.username.charAt(0).toUpperCase() }}</div>
      <div class="user-body">
        <div class="user-top">
          <span class="user-name">{{ auth.currentUser.value?.username }}</span>
          <el-icon class="logout-icon" @click="handleLogout"><SwitchButton /></el-icon>
        </div>
        <div class="user-badges">
          <el-tag :type="roleTagType" size="small" effect="dark">
            {{ auth.roleLabel.value }}
          </el-tag>
          <span class="usage-chip" :class="{ unlimited: usage?.is_unlimited }" v-if="usage">
            <el-icon style="font-size:13px; margin-right:3px"><DataAnalysis /></el-icon>
            <template v-if="usage?.is_unlimited">♾️ 无限制</template>
            <template v-else>剩余 {{ usage?.remaining ?? '--' }} 次</template>
          </span>
        </div>
        <div v-if="userVipExpiry" class="vip-expiry-row">
          <el-icon style="font-size:13px; margin-right:4px"><Clock /></el-icon>
          <span>{{ userVipExpiry }}</span>
        </div>
      </div>
    </div>

    <!-- Action Buttons -->
    <div class="user-actions">
      <div class="user-action-btn" v-if="!auth.isAdmin.value" @click="showVipDialog">
        <el-icon><StarFilled /></el-icon>
        <span>{{ auth.isVip.value ? '续费VIP' : '购买VIP' }}</span>
      </div>
      <div class="user-action-btn admin" v-if="auth.isAdmin.value" @click="goAdmin">
        <el-icon><Setting /></el-icon>
        <span>用户管理</span>
      </div>
    </div>

    <!-- VIP Purchase Dialog -->
    <el-dialog v-model="vipDialogVisible" title="🌟 升级 VIP 会员" width="420px" class="vip-dialog" append-to-body>
      <div class="vip-body">
<!-- Price -->
        <div class="vip-price-section">
          <div class="vip-price-card original">
            <div class="vip-label-badge">原价</div>
            <div class="vip-price-amount">
              <span class="vip-currency">¥</span>
              <span class="vip-original-price">788</span>
            </div>
            <div class="vip-price-unit">/ 每年</div>
          </div>
          <div class="vip-price-arrow">→</div>
          <div class="vip-price-card current">
            <div class="vip-label-badge hot">限时特惠</div>
            <div class="vip-price-amount">
              <span class="vip-currency">¥</span>
              <span class="vip-current-price">388</span>
            </div>
            <div class="vip-price-unit">/ 每年</div>
            <div class="vip-save-tag">省 ¥400</div>
          </div>
        </div>

        <!-- Benefits -->
        <div class="vip-benefits">
          <div class="vip-benefit-item">✅ 无限次数生成视频</div>
          <div class="vip-benefit-item">✅ 优先排队处理任务</div>
          <div class="vip-benefit-item">✅ 高清无水印导出</div>
          <div class="vip-benefit-item">✅ 专属客服支持</div>
        </div>

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
            <span class="vip-wechat-id" @click="copyWechatId">Pixelle_VIP</span>
            <el-button size="small" type="success" plain style="margin-left:8px;" @click="copyWechatId">
              复制微信号
            </el-button>
          </div>
          <div class="vip-wechat-hint">长按或扫码添加微信，付款后开通 VIP</div>
        </div>
      </div>
    </el-dialog>
  </div>

  <!-- Login Button (when not logged in) -->
  <div class="user-menu" v-else>
    <el-button type="primary" size="small" @click="$emit('show-login')">
      登录
    </el-button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { DataAnalysis, Setting, SwitchButton, StarFilled, Clock, ChatLineSquare } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getAuth } from '../composables/useAuth'

const emit = defineEmits<{
  (e: 'show-login'): void
  (e: 'go-admin'): void
}>()

const auth = getAuth()
const vipDialogVisible = ref(false)

const roleTagType = computed(() => {
  const role = auth.currentUser.value?.role
  if (role === 'admin') return 'danger'
  if (role === 'vip') return 'warning'
  return 'info'
})

const userVipExpiry = computed(() => {
  const user = auth.currentUser.value
  if (user?.role === 'vip' && user?.vip_expires_at) {
    try {
      const date = new Date(user.vip_expires_at)
      return `到期 ${date.toLocaleDateString('zh-CN')}`
    } catch {
      return null
    }
  }
  return null
})

const usage = ref<{ remaining: number; is_unlimited: boolean } | null>(null)
let usageTimer: ReturnType<typeof setInterval> | null = null

async function refreshUsage() {
  try {
    const u = await auth.fetchUsage()
    usage.value = {
      remaining: u.is_unlimited ? -1 : u.remaining,
      is_unlimited: u.is_unlimited,
    }
  } catch {
    // fallback to daily_limit from user info
    const user = auth.currentUser.value
    usage.value = {
      remaining: user?.daily_limit ?? 0,
      is_unlimited: user?.role === 'vip' || user?.daily_limit === -1,
    }
  }
}

onMounted(() => {
  // 立即刷新，之后每 5 秒自动刷新（任务完成后次数会自动更新）
  refreshUsage()
  usageTimer = setInterval(refreshUsage, 5000)
})

onUnmounted(() => {
  if (usageTimer) {
    clearInterval(usageTimer)
    usageTimer = null
  }
})

function showVipDialog() {
  vipDialogVisible.value = true
}

function goAdmin() {
  emit('go-admin')
}

async function handleLogout() {
  try {
    await ElMessageBox.confirm('确定要退出登录吗？', '确认退出', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'info',
    })
    auth.logout()
    ElMessage.success('已退出登录')
    window.location.reload()
  } catch {
    // cancelled
  }
}

async function copyWechatId() {
  try {
    await navigator.clipboard.writeText('Pixelle_VIP')
    ElMessage.success('微信号已复制')
  } catch {
    ElMessage.warning('复制失败，请手动记下微信号：Pixelle_VIP')
  }
}
</script>

<style scoped>
.user-menu {
  padding: 14px 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  margin-top: auto;
  position: relative;
}

.user-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea, #764ba2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 16px;
  color: #fff;
  flex-shrink: 0;
}

.user-body {
  flex: 1;
  min-width: 0;
}

.user-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.user-name {
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

.user-badges {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 4px;
}

.logout-icon {
  font-size: 16px;
  color: rgba(255, 255, 255, 0.5);
  cursor: pointer;
  transition: color 0.2s;
  flex-shrink: 0;
}

.logout-icon:hover {
  color: #f56c6c;
}

.vip-expiry-row {
  display: flex;
  align-items: center;
  font-size: 12px;
  color: #e6a23c;
  margin-top: 6px;
  padding: 3px 8px;
  background: rgba(230, 162, 60, 0.08);
  border-radius: 4px;
}

.usage-chip {
  display: inline-flex;
  align-items: center;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
  background: rgba(64, 158, 255, 0.1);
  padding: 3px 8px;
  border-radius: 4px;
  white-space: nowrap;
  transition: background 0.2s;
}

.usage-chip:hover {
  background: rgba(64, 158, 255, 0.2);
}

.usage-chip.unlimited {
  color: #e6a23c;
  background: rgba(230, 162, 60, 0.12);
}

.usage-chip.unlimited:hover {
  background: rgba(230, 162, 60, 0.2);
}

/* Action Buttons */
.user-actions {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-top: 12px;
  flex-wrap: wrap;
}

.user-action-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  padding: 8px 18px;
  border-radius: 10px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.7);
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.08);
  transition: all 0.15s;
  white-space: nowrap;
}

/* 购买VIP按钮 - 醒目金色渐变 */
.user-action-btn:first-child {
  background: linear-gradient(135deg, #f59e0b, #d97706);
  border-color: #f59e0b;
  color: #fff;
  font-weight: 800;
  font-size: 14px;
  padding: 9px 24px;
  box-shadow: 0 0 12px rgba(245, 158, 11, 0.25);
}

.user-action-btn:first-child:hover {
  background: linear-gradient(135deg, #fbbf24, #f59e0b);
  border-color: #fbbf24;
  color: #fff;
  box-shadow: 0 0 24px rgba(245, 158, 11, 0.4);
  transform: translateY(-1px);
}

.user-action-btn.admin:hover {
  background: rgba(64, 158, 255, 0.15);
  color: #409eff;
  border-color: rgba(64, 158, 255, 0.3);
}

.user-action-btn.logout:hover {
  background: rgba(245, 108, 108, 0.15);
  color: #f56c6c;
  border-color: rgba(245, 108, 108, 0.3);
}

/* VIP Dialog Styles */
:deep(.vip-dialog .el-dialog__body) {
  padding: 0;
}

.vip-body {
  padding: 20px 24px;
}

.vip-price-section {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-bottom: 20px;
  padding: 16px;
  background: linear-gradient(135deg, rgba(230, 162, 60, 0.08), rgba(230, 162, 60, 0.02));
  border-radius: 12px;
  border: 1px solid rgba(230, 162, 60, 0.15);
}

.vip-price-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 14px 20px;
  border-radius: 10px;
  min-width: 110px;
}

.vip-price-card.original {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.vip-price-card.current {
  background: linear-gradient(135deg, rgba(230, 162, 60, 0.12), rgba(245, 158, 11, 0.06));
  border: 1px solid rgba(230, 162, 60, 0.25);
}

.vip-label-badge {
  font-size: 11px;
  font-weight: 700;
  color: #999;
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.05);
}

.vip-label-badge.hot {
  color: #fbbf24;
  background: rgba(230, 162, 60, 0.15);
}

.vip-price-amount {
  display: flex;
  align-items: baseline;
  gap: 1px;
}

.vip-currency {
  font-size: 16px;
  font-weight: 700;
  color: #999;
}

.vip-price-card.current .vip-currency {
  color: #e6a23c;
  font-size: 18px;
}

.vip-original-price {
  font-size: 22px;
  font-weight: 700;
  color: #999;
  text-decoration: line-through;
}

.vip-current-price {
  font-size: 30px;
  font-weight: 800;
  color: #e6a23c;
  line-height: 1;
}

.vip-price-unit {
  font-size: 11px;
  color: #999;
}

.vip-save-tag {
  font-size: 11px;
  font-weight: 700;
  color: #22c55e;
  background: rgba(34, 197, 94, 0.1);
  padding: 2px 8px;
  border-radius: 4px;
}

.vip-price-arrow {
  font-size: 20px;
  color: rgba(255, 255, 255, 0.2);
  font-weight: 300;
}

.vip-benefits {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
  padding: 12px 16px;
  background: rgba(64, 158, 255, 0.04);
  border-radius: 8px;
}

.vip-benefit-item {
  font-size: 14px;
  color: #ddd;
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
}

.vip-qr-img {
  width: 160px;
  height: 160px;
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
</style>