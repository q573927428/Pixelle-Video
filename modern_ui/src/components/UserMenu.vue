<template>
  <div class="user-menu" v-if="auth.isLoggedIn.value">
    <div class="user-row">
      <div class="user-avatar">{{ auth.currentUser.value?.username.charAt(0).toUpperCase() }}</div>
      <div class="user-body">
        <div class="user-top">
          <span class="user-name">{{ auth.currentUser.value?.username }}</span>
          <el-icon class="logout-icon" @click="handleLogout"><SwitchButton /></el-icon>
        </div>
    <!-- VIP/会员标签 -->
    <div v-if="auth.isVipEffective.value" class="vip-tag-row">
      <el-tag v-if="auth.isVip.value" type="warning" size="small" effect="dark" class="vip-tag">VIP</el-tag>
      <el-tag v-else-if="auth.isSvip.value" type="danger" size="small" effect="dark" class="vip-tag svip-tag">SVIP</el-tag>
      <span class="vip-expiry" v-if="auth.vipExpiresAt.value">
        到期 {{ formatDate(auth.vipExpiresAt.value) }}
      </span>
    </div>

    <!-- ZS币余额 -->
    <div class="zs-balance-row">
      <span class="zs-balance-label">
        <img src="/zsicon60.png" class="zs-icon" alt="ZS币" />
        余额
      </span>
      <span class="zs-balance-value">
        <span class="zs-balance-num">{{ auth.zsBalance.value }}</span>
      </span>
    </div>
      </div>
    </div>

    <!-- Account Navigation Grid -->
    <div class="account-nav">
      <div class="nav-item" @click="handleOpenVip">
        <span class="nav-icon">⭐</span>
        <span class="nav-label">{{ auth.isVipEffective.value ? '续费VIP' : '开通VIP' }}</span>
      </div>
      <div class="nav-item" @click="handleRecharge">
        <span class="nav-icon">💎</span>
        <span class="nav-label">余额充值</span>
      </div>
      <div class="nav-item" @click="handleInvite">
        <span class="nav-icon">🔗</span>
        <span class="nav-label">邀请好友</span>
      </div>
    </div>

    <RechargeDialog ref="rechargeDialogRef" />
    <InviteDialog ref="inviteDialogRef" />
    <VipPurchaseDialog ref="vipPurchaseDialogRef" />
  </div>

  <!-- Login Button (when not logged in) -->
  <div class="user-menu" v-else>
    <el-button type="primary" size="small" @click="$emit('show-login')">
      登录
    </el-button>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Coin, SwitchButton, Share, StarFilled } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getAuth } from '../composables/useAuth'
import RechargeDialog from './RechargeDialog.vue'
import InviteDialog from './InviteDialog.vue'
import VipPurchaseDialog from './VipPurchaseDialog.vue'

const emit = defineEmits<{
  (e: 'show-login'): void
}>()

const auth = getAuth()
const rechargeDialogRef = ref<InstanceType<typeof RechargeDialog> | null>(null)
const inviteDialogRef = ref<InstanceType<typeof InviteDialog> | null>(null)
const vipPurchaseDialogRef = ref<InstanceType<typeof VipPurchaseDialog> | null>(null)

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '--'
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

function handleRecharge() {
  rechargeDialogRef.value?.open()
}

function handleInvite() {
  inviteDialogRef.value?.open()
}

function handleOpenVip() {
  vipPurchaseDialogRef.value?.openVipDialog()
}

onMounted(async () => {
  try {
    await auth.fetchMe()
  } catch {
    // ignore
  }
})

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

.zs-balance-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  color: #fbbf24;
  margin-top: 6px;
  padding: 5px 10px;
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.18), rgba(217, 119, 6, 0.1));
  border: 1px solid rgba(245, 158, 11, 0.25);
  border-radius: 8px;
  font-weight: 700;
  box-shadow: 0 0 12px rgba(245, 158, 11, 0.1);
}

.zs-balance-label {
  display: flex;
  align-items: center;
  color: rgba(251, 191, 36, 0.7);
  font-weight: 600;
  font-size: 12px;
}

.zs-icon {
  width: 18px;
  height: 18px;
  margin-right: 4px;
  object-fit: contain;
}

.zs-balance-value {
  display: flex;
  align-items: center;
}

.zs-balance-num {
  color: #22c55e;
  font-weight: 900;
  font-size: 16px;
  text-shadow: 0 0 12px rgba(251, 191, 36, 0.25);
  margin-right: 4px;
}

/* Account Navigation Grid - 2 per row with border */
.account-nav {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
  margin-top: 10px;
}

.nav-item {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 9px 8px;
  border-radius: 10px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.8);
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.1);
  transition: all 0.15s;
  box-sizing: border-box;
}

.nav-item:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.2);
}

.nav-icon {
  font-size: 15px;
  flex-shrink: 0;
}

.nav-label {
  white-space: nowrap;
}

/* VIP 标签行 */
.vip-tag-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 4px;
  padding: 2px 4px;
}

.vip-tag {
  font-weight: 700;
  font-size: 11px;
}

.vip-tag.svip-tag {
  background: #dc2626 !important;
  border-color: #dc2626 !important;
}

.vip-expiry {
  font-size: 11px;
  color: rgba(251, 191, 36, 0.6);
}
</style>