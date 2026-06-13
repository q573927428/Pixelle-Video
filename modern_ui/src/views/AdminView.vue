<template>
  <div class="tool-page">
    <div class="page-header">
      <span class="page-icon">🔐</span>
      <div>
        <h3 class="page-title">用户管理</h3>
        <p class="page-desc">管理用户角色、权限和 VIP 状态</p>
      </div>
    </div>

    <!-- VIP Management Card -->
    <div class="card" style="margin-bottom: 16px;">
      <div class="card-header">
        <h3 class="card-title">💎 VIP 会员设置</h3>
      </div>
      <div class="card-body">
        <el-form :model="vipForm" label-width="100px" label-position="top" style="max-width: 500px;">
          <el-form-item label="用户名">
            <el-input v-model="vipForm.username" placeholder="输入要设置为VIP的用户名" clearable />
          </el-form-item>
          <el-form-item label="VIP 到期时间">
            <el-date-picker
              v-model="vipForm.expiresAt"
              type="datetime"
              placeholder="选择VIP到期时间"
              style="width: 100%"
              value-format="YYYY-MM-DD HH:mm:ss"
              :disabled-date="disabledDate"
            />
          </el-form-item>
          <el-form-item>
            <div style="display: flex; gap: 8px;">
              <el-button type="warning" :loading="vipSetting" @click="handleSetVip">
                <el-icon style="margin-right: 4px;"><StarFilled /></el-icon>
                设为 VIP 会员
              </el-button>
              <el-button type="danger" plain :loading="vipRemoving" @click="handleRemoveVip">
                取消 VIP
              </el-button>
            </div>
            <div class="small muted" style="margin-top: 6px;">
              设为VIP后自动获得无限生成次数，到期后自动降级为普通用户
            </div>
          </el-form-item>
        </el-form>
      </div>
    </div>

    <!-- User Table -->
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">用户列表</h3>
        <el-button size="small" @click="loadUsers">刷新</el-button>
      </div>
      <div class="card-body">
        <el-table :data="users" v-loading="loading" stripe style="width: 100%">
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column prop="username" label="用户名" min-width="120" />
          <el-table-column prop="email" label="邮箱" min-width="160">
            <template #default="{ row }">
              {{ row.email || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="role" label="角色" width="100">
            <template #default="{ row }">
              <el-tag :type="roleTagType(row.role)" effect="dark">
                {{ roleLabel(row.role) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="VIP 到期" width="150">
            <template #default="{ row }">
              <span v-if="row.role === 'vip' && row.vip_expires_at" class="vip-expiry-cell">
                {{ formatDate(row.vip_expires_at) }}
              </span>
              <span v-else class="muted">-</span>
            </template>
          </el-table-column>
          <el-table-column prop="daily_limit" label="每日上限" width="100">
            <template #default="{ row }">
              {{ row.daily_limit === -1 ? '无限制' : row.daily_limit }}
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="注册时间" min-width="160">
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <el-button size="small" @click="openEditDialog(row)">编辑</el-button>
              <el-button size="small" type="danger" plain v-if="row.role === 'vip'" @click="handleRemoveVipById(row)">
                取消VIP
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- Pagination -->
        <div style="display: flex; justify-content: center; margin-top: 16px;">
          <el-pagination
            v-model:current-page="page"
            :page-size="pageSize"
            :total="total"
            layout="prev, pager, next"
            @current-change="loadUsers"
          />
        </div>
      </div>
    </div>

    <!-- Edit Dialog -->
    <el-dialog v-model="editDialogVisible" title="编辑用户" width="420px">
      <el-form v-if="editingUser" label-position="top">
        <el-form-item label="用户名">
          <el-input :model-value="editingUser.username" disabled />
        </el-form-item>

        <el-form-item label="角色">
          <el-select v-model="editForm.role" style="width: 100%">
            <el-option label="普通用户" value="normal" />
            <el-option label="VIP 会员" value="vip" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>

        <el-form-item label="VIP 到期时间" v-if="editForm.role === 'vip'">
          <el-date-picker
            v-model="editForm.vip_expires_at"
            type="datetime"
            placeholder="选择VIP到期时间"
            style="width: 100%"
            value-format="YYYY-MM-DD HH:mm:ss"
          />
        </el-form-item>

        <el-form-item label="每日生成上限">
          <el-input-number v-model="editForm.daily_limit" :min="-1" style="width: 100%" />
          <div class="small muted" style="margin-top: 4px;">-1 表示无限制（VIP）</div>
        </el-form-item>

        <el-form-item label="账号状态">
          <el-switch
            v-model="editForm.status"
            :active-value="1"
            :inactive-value="0"
            active-text="启用"
            inactive-text="禁用"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSaveEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { StarFilled } from '@element-plus/icons-vue'
import { request } from '../api'
import { getAuth } from '../composables/useAuth'
import type { UserInfo } from '../composables/useAuth'

interface UserListResponse {
  users: UserInfo[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

const users = ref<UserInfo[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

const editDialogVisible = ref(false)
const editingUser = ref<UserInfo | null>(null)
const editForm = ref<{ role: string; daily_limit: number; status: number; vip_expires_at: string | null }>({
  role: 'normal',
  daily_limit: 3,
  status: 1,
  vip_expires_at: null,
})
const saving = ref(false)

// VIP management
const vipForm = ref({
  username: '',
  expiresAt: '',
})
const vipSetting = ref(false)
const vipRemoving = ref(false)

onMounted(() => {
  loadUsers()
})

async function loadUsers() {
  loading.value = true
  try {
    const auth = getAuth()
    const res = await request<UserListResponse>(`/api/auth/admin/users?page=${page.value}&page_size=${pageSize.value}`, {
      headers: auth._authHeaders(),
    })
    users.value = res.users
    total.value = res.total
  } catch (e: any) {
    ElMessage.error(`加载用户列表失败：${e.message}`)
  } finally {
    loading.value = false
  }
}

function roleTagType(role: string): string {
  if (role === 'admin') return 'danger'
  if (role === 'vip') return 'warning'
  return 'info'
}

function roleLabel(role: string): string {
  if (role === 'admin') return '管理员'
  if (role === 'vip') return 'VIP'
  return '普通'
}

function formatDate(dateStr: string): string {
  if (!dateStr) return '-'
  try {
    return new Date(dateStr).toLocaleString('zh-CN')
  } catch {
    return dateStr
  }
}

function disabledDate(time: Date): boolean {
  return time.getTime() <= Date.now()
}

function openEditDialog(user: UserInfo) {
  editingUser.value = user
  editForm.value = {
    role: user.role,
    daily_limit: user.daily_limit,
    status: 1,
    vip_expires_at: user.vip_expires_at || null,
  }
  editDialogVisible.value = true
}

async function handleSaveEdit() {
  if (!editingUser.value) return
  saving.value = true
  try {
    const auth = getAuth()
    const body: Record<string, any> = {
      role: editForm.value.role,
      daily_limit: editForm.value.daily_limit,
    }
    if (editForm.value.role === 'vip' && editForm.value.vip_expires_at) {
      body.vip_expires_at = editForm.value.vip_expires_at
    }
    await request(`/api/auth/admin/users/${editingUser.value.id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...auth._authHeaders(),
      },
      body: JSON.stringify(body),
    })
    ElMessage.success('用户信息已更新')
    editDialogVisible.value = false
    loadUsers()
  } catch (e: any) {
    ElMessage.error(`更新失败：${e.message}`)
  } finally {
    saving.value = false
  }
}

async function handleSetVip() {
  if (!vipForm.value.username.trim()) {
    ElMessage.warning('请输入用户名')
    return
  }
  if (!vipForm.value.expiresAt) {
    ElMessage.warning('请选择VIP到期时间')
    return
  }
  vipSetting.value = true
  try {
    const auth = getAuth()
    await request('/api/auth/admin/set-vip', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...auth._authHeaders(),
      },
      body: JSON.stringify({
        username: vipForm.value.username.trim(),
        vip_expires_at: vipForm.value.expiresAt,
      }),
    })
    ElMessage.success(`已成功将「${vipForm.value.username}」设置为 VIP 会员`)
    vipForm.value.username = ''
    vipForm.value.expiresAt = ''
    loadUsers()
  } catch (e: any) {
    ElMessage.error(`设置失败：${e.message}`)
  } finally {
    vipSetting.value = false
  }
}

async function handleRemoveVip() {
  if (!vipForm.value.username.trim()) {
    ElMessage.warning('请输入用户名')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确定要取消「${vipForm.value.username}」的 VIP 资格吗？`,
      '确认取消 VIP',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }
  vipRemoving.value = true
  try {
    const auth = getAuth()
    // Find user by username first
    const targetUser = users.value.find(u => u.username === vipForm.value.username.trim())
    if (!targetUser) {
      ElMessage.error('未找到该用户')
      vipRemoving.value = false
      return
    }
    await request(`/api/auth/admin/remove-vip/${targetUser.id}`, {
      method: 'POST',
      headers: auth._authHeaders(),
    })
    ElMessage.success(`已取消「${vipForm.value.username}」的 VIP 资格`)
    vipForm.value.username = ''
    loadUsers()
  } catch (e: any) {
    ElMessage.error(`操作失败：${e.message}`)
  } finally {
    vipRemoving.value = false
  }
}

async function handleRemoveVipById(user: UserInfo) {
  try {
    await ElMessageBox.confirm(
      `确定要取消「${user.username}」的 VIP 资格吗？`,
      '确认取消 VIP',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }
  try {
    const auth = getAuth()
    await request(`/api/auth/admin/remove-vip/${user.id}`, {
      method: 'POST',
      headers: auth._authHeaders(),
    })
    ElMessage.success(`已取消「${user.username}」的 VIP 资格`)
    loadUsers()
  } catch (e: any) {
    ElMessage.error(`操作失败：${e.message}`)
  }
}
</script>

<style scoped>
.vip-expiry-cell {
  font-size: 12px;
  color: #e6a23c;
}

.muted {
  color: #999;
  font-size: 12px;
}

.small {
  font-size: 12px;
}
</style>