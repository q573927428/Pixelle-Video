<template>
  <div class="tool-page">
    <div class="page-header">
      <span class="page-icon">🔐</span>
      <div>
        <h3 class="page-title">用户管理</h3>
        <p class="page-desc">管理用户角色、权限和状态</p>
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
          <el-table-column prop="role" label="角色" width="120">
            <template #default="{ row }">
              <el-tag :type="roleTagType(row.role)" effect="dark">
                {{ roleLabel(row.role) }}
              </el-tag>
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
    <el-dialog v-model="editDialogVisible" title="编辑用户" width="400px">
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
import { ElMessage } from 'element-plus'
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
const editForm = ref({ role: 'normal', daily_limit: 3, status: 1 })
const saving = ref(false)

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
  return new Date(dateStr).toLocaleString('zh-CN')
}

function openEditDialog(user: UserInfo) {
  editingUser.value = user
  editForm.value = {
    role: user.role,
    daily_limit: user.daily_limit,
    status: 1, // We don't track status in the list, default to 1
  }
  editDialogVisible.value = true
}

async function handleSaveEdit() {
  if (!editingUser.value) return
  saving.value = true
  try {
    const auth = getAuth()
    await request(`/api/auth/admin/users/${editingUser.value.id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...auth._authHeaders(),
      },
      body: JSON.stringify(editForm.value),
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
</script>
