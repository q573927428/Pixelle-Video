<template>
  <el-dialog v-model="visible" title="🎉 邀请好友赚 ZS币" width="380px" class="invite-dialog" append-to-body>
    <div class="invite-body">
      <!-- 规则说明 -->
      <div class="invite-rule">
        <el-icon style="font-size:20px; color:#22c55e;"><Present /></el-icon>
        <span>每邀请 1 位好友注册，您将获得 <strong>{{ inviteBonus }}</strong> ZS币奖励</span>
      </div>

      <!-- 邀请统计 -->
      <div class="invite-stats" v-if="inviteInfo">
        <div class="stat-item">
          <div class="stat-value">{{ inviteInfo.total_invites }}</div>
          <div class="stat-label">已邀请</div>
        </div>
        <div class="stat-item">
          <div class="stat-value">{{ inviteInfo.total_reward_zs }}</div>
          <div class="stat-label">已获得 ZS币</div>
        </div>
      </div>

      <!-- 邀请码 -->
      <div class="invite-code-section" v-if="inviteInfo">
        <div class="code-label">我的邀请码</div>
        <div class="code-value">{{ inviteInfo.invite_code }}</div>
        <el-button type="primary" size="small" @click="copyInviteLink" :icon="CopyDocument">
          复制邀请链接
        </el-button>
      </div>

      <div v-else class="loading-section">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>加载中...</span>
      </div>

      <!-- 邀请记录 -->
      <div class="invite-history" v-if="inviteInfo && inviteInfo.invitees.length > 0">
        <div class="history-title">邀请记录</div>
        <div class="history-item" v-for="(item, idx) in inviteInfo.invitees" :key="idx">
          <span class="history-user">{{ item.username }}</span>
          <span class="history-time">{{ formatTime(item.created_at) }}</span>
        </div>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Present, CopyDocument, Loading } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getAuth } from '../composables/useAuth'
import { request } from '../api'

const auth = getAuth()

const visible = ref(false)
const inviteInfo = ref<any>(null)
const inviteBonus = ref(200)

async function fetchInviteInfo() {
  try {
    const res = await request<any>('/api/auth/invite-info', {
      headers: { ...auth._authHeaders() },
    })
    inviteInfo.value = res
    inviteBonus.value = res.invite_bonus || 200
  } catch {
    // ignore
  }
}

function open() {
  visible.value = true
  fetchInviteInfo()
}

async function copyInviteLink() {
  if (!inviteInfo.value || !inviteInfo.value.invite_code) return
  const link = window.location.origin + '/register?invite=' + inviteInfo.value.invite_code
  try {
    await navigator.clipboard.writeText(link)
    ElMessage.success('邀请链接已复制！')
  } catch {
    ElMessage.warning('复制失败，请手动复制')
  }
}

function formatTime(timeStr: string) {
  try {
    const d = new Date(timeStr)
    return d.toLocaleDateString('zh-CN')
  } catch {
    return timeStr
  }
}

defineExpose({ open })
</script>

<style scoped>
.invite-dialog :deep(.el-dialog__body) {
  padding: 0;
}

.invite-body {
  padding: 16px;
}

.invite-rule {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  background: rgba(34,197,94,0.06);
  border-radius: 8px;
  margin-bottom: 14px;
  font-size: 13px;
  color: #ccc;
}

.invite-rule strong {
  color: #22c55e;
  font-size: 16px;
}

.invite-stats {
  display: flex;
  gap: 12px;
  margin-bottom: 14px;
}

.stat-item {
  flex: 1;
  text-align: center;
  padding: 12px;
  background: rgba(255,255,255,0.03);
  border-radius: 8px;
}

.stat-value {
  font-size: 24px;
  font-weight: 800;
  color: #fbbf24;
}

.stat-label {
  font-size: 12px;
  color: #888;
  margin-top: 4px;
}

.invite-code-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px;
  background: rgba(64,158,255,0.04);
  border-radius: 10px;
  margin-bottom: 14px;
  border: 1px solid rgba(64,158,255,0.12);
}

.code-label {
  font-size: 13px;
  color: #999;
}

.code-value {
  font-size: 28px;
  font-weight: 800;
  color: #fff;
  letter-spacing: 6px;
  font-family: monospace;
}

.loading-section {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 24px;
  color: #888;
}

.invite-history {
  margin-top: 6px;
}

.history-title {
  font-size: 13px;
  font-weight: 700;
  color: #ddd;
  margin-bottom: 8px;
}

.history-item {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  border-bottom: 1px solid rgba(255,255,255,0.04);
  font-size: 13px;
}

.history-user {
  color: #ccc;
}

.history-time {
  color: #888;
  font-size: 12px;
}
</style>