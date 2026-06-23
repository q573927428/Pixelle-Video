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
      <div class="user-action-btn" v-if="!auth.isAdmin.value" @click="handleBuyVip">
        <el-icon><StarFilled /></el-icon>
        <span>{{ actionButtonLabel }}</span>
      </div>
      <!-- 升级SVIP按钮（仅VIP可见） -->
      <div class="user-action-btn upgrade" v-if="auth.isVip.value && !auth.isAdmin.value" @click="handleUpgradeVip">
        <el-icon><Top /></el-icon>
        <span>升级SVIP</span>
      </div>
      <div class="user-action-btn admin" v-if="auth.isAdmin.value" @click="goAdmin">
        <el-icon><Setting /></el-icon>
        <span>用户管理</span>
      </div>
    </div>

    <VipPurchaseDialog ref="vipDialogRef" />
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
import { DataAnalysis, Setting, SwitchButton, StarFilled, Clock, Top } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getAuth } from '../composables/useAuth'
import VipPurchaseDialog from './VipPurchaseDialog.vue'

const emit = defineEmits<{
  (e: 'show-login'): void
  (e: 'go-admin'): void
}>()

const auth = getAuth()
const vipDialogRef = ref<InstanceType<typeof VipPurchaseDialog> | null>(null)

function handleBuyVip() {
  vipDialogRef.value?.openVipDialog()
}

function handleUpgradeVip() {
  vipDialogRef.value?.openUpgradeDialog()
}

// 按钮文案：普通用户显示"购买VIP"，VIP显示"续费VIP"，SVIP显示"续费SVIP"
const actionButtonLabel = computed(() => {
  if (auth.isSvip.value) return '续费SVIP'
  if (auth.isVip.value) return '续费VIP'
  return '购买VIP'
})

const roleTagType = computed(() => {
  const role = auth.currentUser.value?.role
  if (role === 'admin') return 'danger'
  if (role === 'vip') return 'warning'
  if (role === 'svip') return 'danger'
  return 'info'
})

const userVipExpiry = computed(() => {
  const user = auth.currentUser.value
  if ((user?.role === 'vip' || user?.role === 'svip') && user?.vip_expires_at) {
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

async function refreshUserInfo() {
  try {
    await auth.fetchMe()
  } catch {
    // ignore
  }
}

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
      is_unlimited: user?.role === 'vip' || user?.role === 'svip' || user?.daily_limit === -1,
    }
  }
}

onMounted(() => {
  refreshUserInfo()
  refreshUsage()
  usageTimer = setInterval(refreshUsage, 5000)
})

onUnmounted(() => {
  if (usageTimer) {
    clearInterval(usageTimer)
    usageTimer = null
  }
})

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

/* 升级SVIP按钮 - 紫色渐变 */
.user-action-btn.upgrade {
  background: linear-gradient(135deg, #8b5cf6, #6d28d9);
  border-color: #8b5cf6;
  color: #fff;
  font-weight: 800;
  font-size: 14px;
  padding: 9px 24px;
  box-shadow: 0 0 12px rgba(139, 92, 246, 0.25);
}

.user-action-btn.upgrade:hover {
  background: linear-gradient(135deg, #a78bfa, #8b5cf6);
  border-color: #a78bfa;
  color: #fff;
  box-shadow: 0 0 24px rgba(139, 92, 246, 0.4);
  transform: translateY(-1px);
}

</style>
