<template>
  <div class="user-menu" v-if="auth.isLoggedIn.value">
    <div class="user-row">
      <div class="user-avatar">{{ auth.currentUser.value?.username.charAt(0).toUpperCase() }}</div>
      <div class="user-body">
        <div class="user-top">
          <span class="user-name">{{ auth.currentUser.value?.username }}</span>
          <el-icon class="logout-icon" @click="handleLogout"><SwitchButton /></el-icon>
        </div>
        <!-- ZS币余额 -->
        <div class="zs-balance-row">
          <span class="zs-balance-label">
            <!-- <el-icon style="font-size:14px; margin-right:3px; color:#e6a23c;"><Coin /></el-icon> -->
            ZS币余额
          </span>
          <span class="zs-balance-value">
            <span class="zs-balance-num">{{ auth.zsBalance.value }}</span>
          </span>
        </div>
      </div>
    </div>

    <!-- Action Buttons -->
    <div class="user-actions">
      <div class="user-action-btn recharge" @click="handleRecharge">
        <el-icon><Coin /></el-icon>
        <span>充值</span>
      </div>
      <div class="user-action-btn invite" @click="handleInvite">
        <el-icon><Share /></el-icon>
        <span>邀请</span>
      </div>
    </div>

    <RechargeDialog ref="rechargeDialogRef" />
    <InviteDialog ref="inviteDialogRef" />
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
import { Coin, SwitchButton, Share } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getAuth } from '../composables/useAuth'
import RechargeDialog from './RechargeDialog.vue'
import InviteDialog from './InviteDialog.vue'

const emit = defineEmits<{
  (e: 'show-login'): void
}>()

const auth = getAuth()
const rechargeDialogRef = ref<InstanceType<typeof RechargeDialog> | null>(null)
const inviteDialogRef = ref<InstanceType<typeof InviteDialog> | null>(null)

function handleRecharge() {
  rechargeDialogRef.value?.open()
}

function handleInvite() {
  inviteDialogRef.value?.open()
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

/* 充值按钮 - 金色渐变 */
.user-action-btn.recharge {
  background: linear-gradient(135deg, #f59e0b, #d97706);
  border-color: #f59e0b;
  color: #fff;
  font-weight: 700;
  font-size: 13px;
  padding: 9px 20px;
  box-shadow: 0 0 12px rgba(245, 158, 11, 0.25);
}

.user-action-btn.recharge:hover {
  background: linear-gradient(135deg, #fbbf24, #f59e0b);
  border-color: #fbbf24;
  color: #fff;
  box-shadow: 0 0 24px rgba(245, 158, 11, 0.4);
  transform: translateY(-1px);
}

.user-action-btn.invite {
  background: linear-gradient(135deg, #22c55e, #16a34a);
  border-color: #22c55e;
  color: #fff;
  font-weight: 700;
  font-size: 13px;
  padding: 9px 20px;
  box-shadow: 0 0 12px rgba(34, 197, 94, 0.25);
}

.user-action-btn.invite:hover {
  background: linear-gradient(135deg, #4ade80, #22c55e);
  border-color: #4ade80;
  box-shadow: 0 0 24px rgba(34, 197, 94, 0.4);
  transform: translateY(-1px);
}

.user-action-btn.admin:hover {
  background: rgba(64, 158, 255, 0.15);
  color: #409eff;
  border-color: rgba(64, 158, 255, 0.3);
}
</style>