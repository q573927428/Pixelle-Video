<template>
  <div class="user-menu" v-if="auth.isLoggedIn.value">
    <div class="user-row">
      <div class="user-avatar">{{ auth.currentUser.value?.username.charAt(0).toUpperCase() }}</div>
      <div class="user-body">
        <div class="user-top">
          <span class="user-name">{{ auth.currentUser.value?.username }}</span>
          <el-tooltip content="退出登录" placement="top">
            <div class="logout-btn" @click="handleLogout" title="退出登录">
              <el-icon><SwitchButton /></el-icon>
            </div>
          </el-tooltip>
        </div>
        <div class="user-badges">
          <el-tag :type="roleTagType" size="small" effect="dark">
            {{ auth.roleLabel.value }}
          </el-tag>
          <span class="usage-chip" :class="{ unlimited: usage?.is_unlimited }" @click="showDropdown = !showDropdown" v-if="usage">
            <el-icon style="font-size:13px; margin-right:3px"><DataAnalysis /></el-icon>
            <template v-if="usage?.is_unlimited">♾️ 无限制</template>
            <template v-else>剩余 {{ usage?.remaining ?? '--' }} 次</template>
          </span>
        </div>
      </div>
    </div>

    <!-- Dropdown -->
    <div v-if="showDropdown" class="dropdown-menu" @click.stop>
      <div class="dropdown-item" @click="showUsage">
        <el-icon><DataAnalysis /></el-icon>
        <span>详细统计</span>
      </div>
      <div class="dropdown-item" v-if="auth.isAdmin.value" @click="goAdmin">
        <el-icon><Setting /></el-icon>
        <span>用户管理</span>
      </div>
      <div class="dropdown-divider" />
      <div class="dropdown-item logout" @click="handleLogout">
        <el-icon><SwitchButton /></el-icon>
        <span>退出登录</span>
      </div>
    </div>

    <!-- Usage Dialog -->
    <el-dialog v-model="usageDialogVisible" title="使用统计" width="360px">
      <div v-if="usage" class="usage-info">
        <div class="usage-item">
          <span class="usage-label">会员类型</span>
          <span class="usage-value">{{ auth.roleLabel.value }}</span>
        </div>
        <div class="usage-item">
          <span class="usage-label">今日已生成</span>
          <span class="usage-value">{{ usage.used_today }} 个</span>
        </div>
        <div class="usage-item">
          <span class="usage-label">今日剩余</span>
          <span class="usage-value" :class="{ unlimited: usage.is_unlimited }">
            {{ usage.is_unlimited ? '无限制' : usage.remaining + ' 个' }}
          </span>
        </div>
        <el-progress
          v-if="!usage.is_unlimited"
          :percentage="usagePercentage"
          :status="usage.remaining <= 0 ? 'exception' : 'success'"
          :stroke-width="16"
          :format="usageFormat"
          style="margin-top: 16px;"
        />
      </div>
      <div v-else class="usage-loading">加载中...</div>
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
import { DataAnalysis, Setting, SwitchButton } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getAuth, type UserDailyUsage } from '../composables/useAuth'

const emit = defineEmits<{
  (e: 'show-login'): void
  (e: 'go-admin'): void
}>()

const auth = getAuth()
const showDropdown = ref(false)
const usageDialogVisible = ref(false)
const usage = ref<UserDailyUsage | null>(null)

const roleTagType = computed(() => {
  const role = auth.currentUser.value?.role
  if (role === 'admin') return 'danger'
  if (role === 'vip') return 'warning'
  return 'info'
})

const usagePercentage = computed(() => {
  if (!usage.value || usage.value.is_unlimited) return 0
  const total = usage.value.used_today + usage.value.remaining
  return total > 0 ? Math.round((usage.value.used_today / total) * 100) : 0
})

const usageFormat = (percentage: number) => {
  if (!usage.value) return ''
  return `${usage.value.used_today} / ${usage.value.used_today + usage.value.remaining}`
}

// Close dropdown when clicking outside
function handleClickOutside() {
  showDropdown.value = false
}

async function loadUsage() {
  try {
    usage.value = await auth.fetchUsage()
  } catch {
    usage.value = null
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  loadUsage()
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})

async function showUsage() {
  showDropdown.value = false
  usageDialogVisible.value = true
  try {
    usage.value = await auth.fetchUsage()
  } catch (e: any) {
    ElMessage.error(`获取使用统计失败：${e.message}`)
  }
}

function goAdmin() {
  showDropdown.value = false
  emit('go-admin')
}

async function handleLogout() {
  showDropdown.value = false
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

.logout-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  cursor: pointer;
  color: rgba(255, 255, 255, 0.35);
  transition: all 0.2s;
  flex-shrink: 0;
}

.logout-btn:hover {
  background: rgba(245, 108, 108, 0.15);
  color: #f56c6c;
}

.user-badges {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 4px;
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
  cursor: pointer;
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

.dropdown-menu {
  position: absolute;
  bottom: 100%;
  left: 12px;
  right: 12px;
  background: #1e1e2e;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  padding: 6px;
  margin-bottom: 8px;
  box-shadow: 0 -8px 24px rgba(0, 0, 0, 0.3);
  z-index: 100;
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  color: rgba(255, 255, 255, 0.8);
  font-size: 14px;
  transition: background 0.15s;
}

.dropdown-item:hover {
  background: rgba(255, 255, 255, 0.08);
}

.dropdown-item.logout:hover {
  color: #f56c6c;
}

.dropdown-divider {
  height: 1px;
  background: rgba(255, 255, 255, 0.08);
  margin: 4px 0;
}

.usage-info {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.usage-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}

.usage-label {
  color: #666;
  font-size: 14px;
}

.usage-value {
  font-weight: 600;
  font-size: 14px;
}

.usage-value.unlimited {
  color: #e6a23c;
}

.usage-loading {
  text-align: center;
  color: #999;
  padding: 24px;
}
</style>