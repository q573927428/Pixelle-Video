<template>
  <div class="tool-page">
    <div class="page-header">
      <span class="page-icon">🔐</span>
      <div>
        <h3 class="page-title">用户管理</h3>
        <p class="page-desc">管理用户角色、权限和 VIP 状态</p>
      </div>
    </div>

    <!-- User Table -->
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">用户列表</h3>
        <div style="display: flex; gap: 8px; align-items: center;">
          <el-input
            v-model="searchQuery"
            placeholder="搜索用户名或手机号"
            clearable
            style="width: 220px;"
            :prefix-icon="Search"
            @clear="handleSearch"
            @keyup.enter="handleSearch"
          />
          <el-button size="small" type="primary" @click="handleSearch">搜索</el-button>
          <el-button size="small" @click="loadUsers">刷新</el-button>
        </div>
      </div>
      <div class="card-body">
        <el-table :data="users" v-loading="loading" stripe style="width: 100%">
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column prop="username" label="用户名" min-width="120" />
          <el-table-column prop="phone" label="手机号" min-width="130">
            <template #default="{ row }">
              {{ row.phone || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="role" label="角色" width="100">
            <template #default="{ row }">
              <el-tag :type="roleTagType(row.role)" effect="dark">
                {{ roleLabel(row.role) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="zs_balance" label="ZS币余额" width="100">
            <template #default="{ row }">
              {{ row.zs_balance ?? 0 }}
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="注册时间" min-width="160">
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="380" fixed="right">
            <template #default="{ row }">
                <el-button size="small" @click="openEditDialog(row)">编辑</el-button>
                <el-button size="small" type="warning" plain @click="openAdjustBalanceDialog(row)">调整余额</el-button>
              <el-button
                size="small"
                :type="row.status === 0 ? 'primary' : 'danger'"
                plain
                v-if="row.role !== 'admin'"
                @click="handleToggleStatus(row)"
              >
                {{ row.status === 0 ? '启用' : '禁用' }}
              </el-button>
              <el-button size="small" type="danger" plain v-if="row.role === 'vip' || row.role === 'svip'" @click="handleRemoveVipById(row)">
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

    <!-- ZS币 系统配置 -->
    <div class="card" style="margin-top: 20px;">
      <div class="card-header">
        <h3 class="card-title">⚙️ ZS币 系统配置</h3>
      </div>
      <div class="card-body">
        <div class="config-grid">
          <div class="config-item">
            <label>每秒消耗 ZS币</label>
            <el-input-number v-model.number="sysConfig.zs_per_second" :min="1" :max="100" />
          </div>
          <div class="config-item">
            <label>人民币汇率（1元=？ZS币）</label>
            <el-input-number v-model.number="sysConfig.exchange_rate" :min="1" :max="10000" />
          </div>
          <div class="config-item">
            <label>注册赠送 ZS币</label>
            <el-input-number v-model.number="sysConfig.register_bonus" :min="0" :max="100000" />
          </div>
          <div class="config-item">
            <label>邀请奖励 ZS币</label>
            <el-input-number v-model.number="sysConfig.invite_bonus" :min="0" :max="100000" />
          </div>
          <div class="config-item">
            <label>最低充值金额（元）</label>
            <el-input-number v-model.number="sysConfig.min_recharge" :min="1" :max="10000" />
          </div>
        </div>

        <!-- VIP/SVIP 套餐配置 -->
        <div style="margin-top: 20px; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 16px;">
          <h4 style="margin:0 0 14px;font-size:14px;color:#ddd;">🌟 VIP/SVIP 套餐配置</h4>
          <div class="config-grid">
            <div class="config-item">
              <label>VIP 月费（元）</label>
              <el-input-number v-model.number="sysConfig.vip_price" :min="1" :max="9999" />
            </div>
            <div class="config-item">
              <label>SVIP 月费（元）</label>
              <el-input-number v-model.number="sysConfig.svip_price" :min="1" :max="9999" />
            </div>
            <div class="config-item">
              <label>VIP 赠送 ZS币</label>
              <el-input-number v-model.number="sysConfig.vip_bonus_zs" :min="0" :max="100000" />
            </div>
            <div class="config-item">
              <label>SVIP 赠送 ZS币</label>
              <el-input-number v-model.number="sysConfig.svip_bonus_zs" :min="0" :max="100000" />
            </div>
            <div class="config-item">
              <label>VIP 折扣率（90=9折）</label>
              <el-input-number v-model.number="sysConfig.vip_discount" :min="1" :max="100" />
            </div>
            <div class="config-item">
              <label>SVIP 折扣率（80=8折）</label>
              <el-input-number v-model.number="sysConfig.svip_discount" :min="1" :max="100" />
            </div>
            <div class="config-item">
              <label>VIP 队列优先级</label>
              <el-input-number v-model.number="sysConfig.vip_queue_priority" :min="0" :max="10" />
            </div>
            <div class="config-item">
              <label>SVIP 队列优先级</label>
              <el-input-number v-model.number="sysConfig.svip_queue_priority" :min="0" :max="10" />
            </div>
          </div>
        </div>
        <div style="margin-top: 14px; text-align: right;">
          <el-button type="primary" :loading="configSaving" @click="saveSysConfig">保存配置</el-button>
        </div>
      </div>
    </div>

    <!-- Edit Dialog -->
    <el-dialog v-model="editDialogVisible" title="编辑用户" width="420px">
      <el-form v-if="editingUser" label-position="top">
        <el-form-item label="用户名">
          <el-input :model-value="editingUser.username" disabled />
        </el-form-item>

        <el-form-item label="手机号">
          <el-input :model-value="editingUser.phone || '-'" disabled />
        </el-form-item>

        <el-form-item label="角色">
          <el-select v-model="editForm.role" style="width: 100%">
            <el-option label="普通用户" value="normal" />
            <el-option label="VIP 会员" value="vip" />
            <el-option label="SVIP 会员" value="svip" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>

        <el-form-item label="VIP/SVIP 到期时间" v-if="editForm.role === 'vip' || editForm.role === 'svip'">
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
          <div class="small muted" style="margin-top: 4px;">-1 表示无限制（SVIP），VIP 默认为 10 次</div>
        </el-form-item>

        <el-form-item label="账号状态">
          <el-switch
            v-model="editForm.status"
            :active-value="1"
            :inactive-value="0"
            active-text="启用"
            inactive-text="禁用"
            :disabled="editingUser?.role === 'admin'"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSaveEdit">保存</el-button>
      </template>
    </el-dialog>

    <!-- Adjust Balance Dialog -->
    <el-dialog v-model="adjustBalanceDialogVisible" title="调整 ZS币余额" width="400px">
      <el-form v-if="adjustBalanceUser" label-position="top">
        <el-form-item label="用户">
          <el-input :model-value="adjustBalanceUser.username" disabled />
        </el-form-item>
        <el-form-item label="当前余额">
          <el-input :model-value="String(adjustBalanceUser.zs_balance ?? 0)" disabled />
        </el-form-item>
        <el-form-item label="调整类型">
          <el-radio-group v-model="adjustBalanceType">
            <el-radio value="add">增加</el-radio>
            <el-radio value="deduct">减少</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="调整数量（ZS币）">
          <el-input-number v-model.number="adjustBalanceAmount" :min="1" :max="1000000" style="width: 100%" />
        </el-form-item>
        <el-form-item label="调整原因">
          <el-input v-model="adjustBalanceReason" type="textarea" :rows="2" maxlength="500" show-word-limit placeholder="请输入调整原因" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="adjustBalanceDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="adjustBalanceSaving" @click="handleAdjustBalance">确认调整</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
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
const searchQuery = ref('')

const editDialogVisible = ref(false)
const editingUser = ref<UserInfo | null>(null)
const editForm = ref<{ role: string; daily_limit: number; status: number; vip_expires_at: string | null }>({
  role: 'normal',
  daily_limit: 1,
  status: 1,
  vip_expires_at: null,
})
const saving = ref(false)

const adjustBalanceDialogVisible = ref(false)
const adjustBalanceUser = ref<UserInfo | null>(null)
const adjustBalanceType = ref<'add' | 'deduct'>('add')
const adjustBalanceAmount = ref(100)
const adjustBalanceReason = ref('')
const adjustBalanceSaving = ref(false)

// ZS币 系统配置（含VIP/SVIP）
const sysConfig = ref({
  zs_per_second: 5,
  exchange_rate: 100,
  register_bonus: 600,
  invite_bonus: 200,
  min_recharge: 10,
  // VIP/SVIP配置
  vip_price: 29,
  svip_price: 89,
  vip_bonus_zs: 3900,
  svip_bonus_zs: 10000,
  vip_discount: 90,
  svip_discount: 80,
  vip_queue_priority: 1,
  svip_queue_priority: 2,
})
const configSaving = ref(false)

async function loadSysConfig() {
  try {
    const auth = getAuth()
    const res = await request<any>('/api/auth/admin/config', {
      headers: auth._authHeaders(),
    })
    sysConfig.value = {
      zs_per_second: parseInt(res.zs_per_second) || 5,
      exchange_rate: parseInt(res.exchange_rate) || 100,
      register_bonus: parseInt(res.register_bonus) || 600,
      invite_bonus: parseInt(res.invite_bonus) || 200,
      min_recharge: parseInt(res.min_recharge) || 10,
      vip_price: parseInt(res.vip_price) || 29,
      svip_price: parseInt(res.svip_price) || 89,
      vip_bonus_zs: parseInt(res.vip_bonus_zs) || 3900,
      svip_bonus_zs: parseInt(res.svip_bonus_zs) || 10000,
      vip_discount: parseInt(res.vip_discount) || 90,
      svip_discount: parseInt(res.svip_discount) || 80,
      vip_queue_priority: parseInt(res.vip_queue_priority) || 1,
      svip_queue_priority: parseInt(res.svip_queue_priority) || 2,
    }
  } catch {
    // use defaults
  }
}

async function saveSysConfig() {
  configSaving.value = true
  try {
    const auth = getAuth()
    const headers = {
      'Content-Type': 'application/json',
      ...auth._authHeaders(),
    }
    const config = sysConfig.value
    await request(`/api/auth/admin/config/zs_per_second`, {
      method: 'PUT', headers, body: JSON.stringify({ config_value: String(config.zs_per_second) }),
    })
    await request(`/api/auth/admin/config/exchange_rate`, {
      method: 'PUT', headers, body: JSON.stringify({ config_value: String(config.exchange_rate) }),
    })
    await request(`/api/auth/admin/config/register_bonus`, {
      method: 'PUT', headers, body: JSON.stringify({ config_value: String(config.register_bonus) }),
    })
    await request(`/api/auth/admin/config/invite_bonus`, {
      method: 'PUT', headers, body: JSON.stringify({ config_value: String(config.invite_bonus) }),
    })
    await request(`/api/auth/admin/config/min_recharge`, {
      method: 'PUT', headers, body: JSON.stringify({ config_value: String(config.min_recharge) }),
    })
    // 保存VIP/SVIP配置
    await request(`/api/auth/admin/config/vip_price`, {
      method: 'PUT', headers, body: JSON.stringify({ config_value: String(config.vip_price) }),
    })
    await request(`/api/auth/admin/config/svip_price`, {
      method: 'PUT', headers, body: JSON.stringify({ config_value: String(config.svip_price) }),
    })
    await request(`/api/auth/admin/config/vip_bonus_zs`, {
      method: 'PUT', headers, body: JSON.stringify({ config_value: String(config.vip_bonus_zs) }),
    })
    await request(`/api/auth/admin/config/svip_bonus_zs`, {
      method: 'PUT', headers, body: JSON.stringify({ config_value: String(config.svip_bonus_zs) }),
    })
    await request(`/api/auth/admin/config/vip_discount`, {
      method: 'PUT', headers, body: JSON.stringify({ config_value: String(config.vip_discount) }),
    })
    await request(`/api/auth/admin/config/svip_discount`, {
      method: 'PUT', headers, body: JSON.stringify({ config_value: String(config.svip_discount) }),
    })
    await request(`/api/auth/admin/config/vip_queue_priority`, {
      method: 'PUT', headers, body: JSON.stringify({ config_value: String(config.vip_queue_priority) }),
    })
    await request(`/api/auth/admin/config/svip_queue_priority`, {
      method: 'PUT', headers, body: JSON.stringify({ config_value: String(config.svip_queue_priority) }),
    })
    ElMessage.success('系统配置已更新（含VIP/SVIP套餐配置）')
  } catch (e: any) {
    ElMessage.error(`保存失败：${e.message}`)
  } finally {
    configSaving.value = false
  }
}

onMounted(() => {
  loadUsers()
  loadSysConfig()
})

function handleSearch() {
  page.value = 1
  loadUsers()
}

async function loadUsers() {
  loading.value = true
  try {
    const auth = getAuth()
    let url = `/api/auth/admin/users?page=${page.value}&page_size=${pageSize.value}`
    if (searchQuery.value.trim()) {
      url += `&search=${encodeURIComponent(searchQuery.value.trim())}`
    }
    const res = await request<UserListResponse>(url, {
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
  if (role === 'svip') return 'danger'
  return 'info'
}

function roleLabel(role: string): string {
  if (role === 'admin') return '管理'
  if (role === 'vip') return 'VIP'
  if (role === 'svip') return 'SVIP'
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

function openEditDialog(user: UserInfo) {
  editingUser.value = user
  editForm.value = {
    role: user.role,
    daily_limit: user.daily_limit,
    status: user.status,
    vip_expires_at: user.vip_expires_at || null,
  }
  editDialogVisible.value = true
}

async function handleSaveEdit() {
  if (!editingUser.value) return
  saving.value = true
  try {
    const auth = getAuth()
    const role = editForm.value.role
    const body: Record<string, any> = {
      role,
    }
    // Only send daily_limit for normal/admin when not auto-managed
    if (role === 'vip') {
      // VIP: auto-set to 10 by backend
    } else if (role === 'svip') {
      // SVIP: auto-set to -1 (unlimited) by backend
    } else {
      body.daily_limit = editForm.value.daily_limit
    }
    if ((role === 'vip' || role === 'svip') && editForm.value.vip_expires_at) {
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

async function handleToggleStatus(user: UserInfo) {
  const action = user.status === 0 ? '启用' : '禁用'
  try {
    await ElMessageBox.confirm(
      `确定要${action}用户「${user.username}」吗？`,
      `确认${action}用户`,
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }
  try {
    const auth = getAuth()
    await request(`/api/auth/admin/users/${user.id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...auth._authHeaders(),
      },
      body: JSON.stringify({ status: user.status === 0 ? 1 : 0 }),
    })
    ElMessage.success(`已${action}用户「${user.username}」`)
    loadUsers()
  } catch (e: any) {
    ElMessage.error(`操作失败：${e.message}`)
  }
}

function openAdjustBalanceDialog(user: UserInfo) {
  adjustBalanceUser.value = user
  adjustBalanceType.value = 'add'
  adjustBalanceAmount.value = 100
  adjustBalanceReason.value = ''
  adjustBalanceDialogVisible.value = true
}

async function handleAdjustBalance() {
  if (!adjustBalanceUser.value) return
  const userId = adjustBalanceUser.value.id
  const amount = adjustBalanceAmount.value
  if (amount <= 0) {
    ElMessage.warning('调整数量必须大于0')
    return
  }
  const changeAmount = adjustBalanceType.value === 'add' ? amount : -amount
  const reason = adjustBalanceReason.value.trim()

  try {
    await ElMessageBox.confirm(
      `确定要${adjustBalanceType.value === 'add' ? '增加' : '减少'}用户「${adjustBalanceUser.value.username}」${amount} ZS币吗？${reason ? `\n原因：${reason}` : ''}`,
      '确认调整余额',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }

  adjustBalanceSaving.value = true
  try {
    const auth = getAuth()
    await request('/api/auth/admin/adjust-balance', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...auth._authHeaders(),
      },
      body: JSON.stringify({
        user_id: userId,
        change_amount: changeAmount,
        reason,
      }),
    })
    ElMessage.success(`已${adjustBalanceType.value === 'add' ? '增加' : '减少'}用户「${adjustBalanceUser.value.username}」${amount} ZS币`)
    adjustBalanceDialogVisible.value = false
    loadUsers()
  } catch (e: any) {
    ElMessage.error(`调整失败：${e.message}`)
  } finally {
    adjustBalanceSaving.value = false
  }
}

async function handleRemoveVipById(user: UserInfo) {
  try {
    await ElMessageBox.confirm(
       `确定要取消「${user.username}」的 ${user.role === 'svip' ? 'SVIP' : 'VIP'} 资格吗？`,
      '确认取消',
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
    ElMessage.success(`已取消「${user.username}」的 ${user.role === 'svip' ? 'SVIP' : 'VIP'} 资格`)
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

.config-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.config-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.config-item label {
  font-size: 13px;
  color: #aaa;
  font-weight: 600;
}
</style>
