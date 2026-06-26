<template>
  <div class="account-detail">
    <div class="page-header">
      <h2>💰 账户明细</h2>
    </div>

    <!-- 余额概览 -->
    <div class="balance-overview">
      <div class="balance-card">
        <div class="balance-label">当前 ZS币 余额</div>
        <div class="balance-value">{{ auth.zsBalance.value }}</div>
        <div class="balance-actions">
          <el-button type="warning" size="small" @click="handleRecharge">
            <el-icon style="margin-right:4px"><Coin /></el-icon>
            充值
          </el-button>
        </div>
      </div>
      <div class="balance-stats">
        <div class="stat-item">
          <span class="stat-num recharge-num">{{ summary.totalRecharge }}</span>
          <span class="stat-label">充值次数</span>
        </div>
        <div class="stat-item">
          <span class="stat-num recharge-num">¥{{ summary.totalRechargeAmount }}</span>
          <span class="stat-label">充值总额</span>
        </div>
        <div class="stat-item">
          <span class="stat-num consume-num">{{ summary.totalConsumption }}</span>
          <span class="stat-label">消耗次数</span>
        </div>
        <div class="stat-item">
          <span class="stat-num refund-num">{{ summary.totalRefund }}</span>
          <span class="stat-label">退款次数</span>
        </div>
        <div class="stat-item">
          <span class="stat-num consume-num">{{ summary.totalDeducted }} ZS</span>
          <span class="stat-label">总消耗 ZS</span>
        </div>
        <div class="stat-item">
          <span class="stat-num adjust-num">{{ summary.totalAdjustment }}</span>
          <span class="stat-label">调整次数</span>
        </div>
        <div class="stat-item">
          <span class="stat-num invite-num">{{ summary.totalInvite }}</span>
          <span class="stat-label">邀请次数</span>
        </div>
        <div class="stat-item">
          <span class="stat-num invite-num">{{ summary.totalInviteReward }} ZS</span>
          <span class="stat-label">邀请奖励</span>
        </div>
      </div>
    </div>

    <!-- 分类筛选 -->
    <div class="filter-bar">
      <el-select v-model="typeFilter" placeholder="全部类型" style="width: 160px;" @change="handleFilterChange">
        <el-option label="全部类型" value="" />
        <el-option label="充值" value="recharge" />
        <el-option label="消耗" value="consumption" />
        <el-option label="退款" value="refund" />
        <el-option label="调整" value="adjustment" />
        <el-option label="邀请" value="invite" />
      </el-select>
      <span style="color:#888; font-size:13px; margin-left:12px;">
        共 {{ total }} 条记录
      </span>
    </div>

    <!-- 账变记录列表 -->
    <div class="records-section">
      <div v-if="loading" class="loading-wrapper">
        <el-icon class="is-loading" style="font-size:24px;"><Loading /></el-icon>
        <span style="margin-left:8px; color:#999;">加载中...</span>
      </div>

      <div v-else-if="records.length === 0" class="empty-wrapper">
        <el-icon style="font-size:40px; color:#555;"><Coin /></el-icon>
        <p style="color:#888; margin-top:8px;">暂无账变记录</p>
      </div>

      <div v-else class="records-list">
        <div v-for="(rec, idx) in records" :key="idx" class="record-item">
          <div class="record-header">
            <span class="record-type-cell">
              <el-tag :type="typeTag(rec.type)" size="small" effect="dark">
                {{ rec.label }}
              </el-tag>
            </span>
            <span class="record-amount" :class="rec.change_amount >= 0 ? 'amount-in' : 'amount-out'" style="display:flex;align-items:center;gap:4px;">
              {{ rec.change_amount >= 0 ? '+' : '' }}{{ rec.change_amount }}
              <el-tag v-if="rec.type === 'consumption' && rec.status === 'frozen'" type="warning" size="small" effect="dark" style="font-size:10px;height:18px;line-height:18px;padding:0 4px;">冻结</el-tag>
              <el-tag v-else-if="rec.type === 'consumption' && rec.status === 'deducted'" type="danger" size="small" effect="dark" style="font-size:10px;height:18px;line-height:18px;padding:0 4px;">已扣</el-tag>
              <el-tag v-else-if="rec.type === 'consumption' && rec.status === 'refunded'" type="info" size="small" effect="dark" style="font-size:10px;height:18px;line-height:18px;padding:0 4px;">已退</el-tag>
            </span>
          </div>
          <div class="record-body">
            <span class="record-desc">{{ rec.extra_info || rec.label }}</span>
            <span class="record-time">{{ formatTime(rec.created_at) }}</span>
          </div>
        </div>
      </div>

      <div v-if="totalPages > 1" class="pagination-wrapper">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next"
          small
          @current-change="loadRecords"
        />
      </div>
    </div>

    <!-- 充值弹窗 -->
    <RechargeDialog ref="rechargeDialogRef" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { Coin, Loading } from '@element-plus/icons-vue'
import { getAuth } from '../composables/useAuth'
import { request } from '../api'
import RechargeDialog from '../components/RechargeDialog.vue'

const auth = getAuth()

const pageSize = ref(15)
const page = ref(1)
const total = ref(0)
const totalPages = ref(0)
const records = ref<any[]>([])
const loading = ref(false)
const typeFilter = ref('')

// 汇总统计
const summary = reactive({
  totalRecharge: 0,
  totalRechargeAmount: 0,
  totalConsumption: 0,
  totalDeducted: 0,
  totalRefund: 0,
  totalInvite: 0,
  totalInviteReward: 0,
  totalAdjustment: 0,
})

const rechargeDialogRef = ref<InstanceType<typeof RechargeDialog> | null>(null)

function handleRecharge() {
  rechargeDialogRef.value?.open()
}

function handleFilterChange() {
  page.value = 1
  loadRecords()
}

async function loadRecords() {
  loading.value = true
  try {
    const filterParam = typeFilter.value ? `&type_filter=${typeFilter.value}` : ''
    const res = await request<any>(
      `/api/payment/balance/records?page=${page.value}&page_size=${pageSize.value}${filterParam}`
    )
    records.value = res.records
    total.value = res.total
    totalPages.value = res.total_pages

    // 汇总统计仅在首次加载全部时计算
    if (page.value === 1 && !typeFilter.value) {
      await loadSummary()
    }
  } catch {
    records.value = []
  } finally {
    loading.value = false
  }
}

async function loadSummary() {
  try {
    // 充值统计
    const rechargeRes = await request<any>('/api/payment/recharge/records?page=1&page_size=9999')
    let rechargeCount = 0
    let rechargeRmb = 0
    for (const rec of rechargeRes.records) {
      if (rec.status === 'paid') {
        rechargeCount++
        rechargeRmb += rec.amount_rmb
      }
    }
    summary.totalRecharge = rechargeRes.total
    summary.totalRechargeAmount = rechargeRmb

    // 消耗统计
    const consumeRes = await request<any>('/api/payment/consumption/records?page=1&page_size=9999')
    let deductedTotal = 0
    for (const rec of consumeRes.records) {
      if (rec.deducted_zs !== null) {
        deductedTotal += rec.deducted_zs
      }
    }
    summary.totalConsumption = consumeRes.total
    summary.totalDeducted = deductedTotal

    // 邀请统计
    const inviteRes = await request<any>('/api/auth/invite-info')
    summary.totalInvite = inviteRes.total_invites || 0
    summary.totalInviteReward = inviteRes.total_reward_zs || 0

    // 退款统计
    const refundRes = await request<any>('/api/payment/balance/records?page=1&page_size=9999&type_filter=refund')
    summary.totalRefund = refundRes.total || 0

    // 调整统计
    const adjRes = await request<any>('/api/payment/balance/records?page=1&page_size=9999&type_filter=adjustment')
    summary.totalAdjustment = adjRes.total || 0
  } catch {
    // ignore summary errors
  }
}

function typeTag(type: string): string {
  switch (type) {
    case 'recharge': return 'success'
    case 'consumption': return 'danger'
    case 'refund': return 'primary'
    case 'adjustment': return 'warning'
    case 'invite': return 'info'
    default: return 'info'
  }
}

function formatTime(t: string): string {
  if (!t) return '-'
  try {
    const d = new Date(t)
    return d.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  } catch {
    return t
  }
}

onMounted(() => {
  loadRecords()
})
</script>

<style scoped>
.account-detail {
  padding: 24px;
  max-width: 100%;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 20px;
}

.page-header h2 {
  font-size: 22px;
  font-weight: 700;
  color: #fff;
  margin: 0;
}

/* 余额概览 */
.balance-overview {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
}

.balance-card {
  flex: 0 0 200px;
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.15), rgba(217, 119, 6, 0.08));
  border: 1px solid rgba(245, 158, 11, 0.25);
  border-radius: 12px;
  padding: 16px;
  text-align: center;
}

.balance-label {
  font-size: 12px;
  color: rgba(251, 191, 36, 0.7);
  margin-bottom: 4px;
}

.balance-value {
  font-size: 36px;
  font-weight: 900;
  color: #22c55e;
  text-shadow: 0 0 16px rgba(251, 191, 36, 0.2);
  margin-bottom: 12px;
}

.balance-actions {
  display: flex;
  justify-content: center;
}

.balance-stats {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 1fr 1fr 1fr;
  gap: 8px;
}

.stat-item {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 10px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.stat-num {
  font-size: 20px;
  font-weight: 800;
}

.stat-num.recharge-num { color: #22c55e; }
.stat-num.consume-num { color: #fb923c; }
.stat-num.refund-num { color: #6366f1; }
.stat-num.invite-num { color: #38bdf8; }
.stat-num.adjust-num { color: #fbbf24; }

.stat-label {
  font-size: 11px;
  color: #888;
}

/* 筛选栏 */
.filter-bar {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
}

/* 记录列表 */
.records-section {
  min-height: 200px;
}

.loading-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px 0;
}

.empty-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 0;
}

.records-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.record-item {
  padding: 10px 14px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.record-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.record-type-cell {
  display: flex;
  align-items: center;
}

.record-amount {
  font-size: 18px;
  font-weight: 800;
  font-family: 'Courier New', monospace;
}

.record-amount.amount-in { color: #22c55e; }
.record-amount.amount-out { color: #fb923c; }

.record-body {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
}

.record-desc {
  color: #667;
  max-width: 60%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.record-time {
  color: #555;
  font-size: 11px;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 14px;
}

/* ===== 移动端适配 ===== */
@media (max-width: 768px) {
  .account-detail {
    padding: 12px;
  }

  .balance-overview {
    flex-direction: column;
    gap: 10px;
  }

  .balance-card {
    flex: none;
    padding: 12px;
  }

  .balance-value {
    font-size: 28px;
  }

  .balance-stats {
    grid-template-columns: 1fr 1fr;
    gap: 6px;
  }

  .stat-item { padding: 8px; }
  .stat-num { font-size: 16px; }

  .record-amount { font-size: 16px; }
}
</style>