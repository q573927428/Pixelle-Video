<template>
  <el-dialog v-model="visible" title="📋 充值记录" width="580px" append-to-body @closed="handleClose">
    <div class="records-body">
      <!-- 统计信息 -->
      <div class="stats-bar">
        <div class="stat-item">
          <span class="stat-label">总充值次数</span>
          <span class="stat-value">{{ total }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">充值总额</span>
          <span class="stat-value gold">¥{{ totalRmb }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">到账 ZS币</span>
          <span class="stat-value gold">{{ totalZs }}</span>
        </div>
      </div>

      <!-- 加载状态 -->
      <div v-if="loading" class="loading-wrapper">
        <el-icon class="is-loading" style="font-size:24px;"><Loading /></el-icon>
        <span style="margin-left:8px; color:#999;">加载中...</span>
      </div>

      <!-- 空状态 -->
      <div v-else-if="records.length === 0" class="empty-wrapper">
        <el-icon style="font-size:40px; color:#555;"><Coin /></el-icon>
        <p style="color:#888; margin-top:8px;">暂无充值记录</p>
      </div>

      <!-- 记录列表 -->
      <div v-else class="records-list">
        <div v-for="rec in records" :key="rec.order_no" class="record-item">
          <div class="record-header">
            <span class="record-order-no">{{ rec.order_no }}</span>
            <el-tag :type="statusTagType(rec.status)" size="small" effect="dark">
              {{ statusLabel(rec.status) }}
            </el-tag>
          </div>
          <div class="record-details">
            <div class="detail-row">
              <span class="detail-label">充值金额</span>
              <span class="detail-value">¥{{ rec.amount_rmb }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">到账 ZS币</span>
              <span class="detail-value gold">+{{ rec.amount_zs }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">创建时间</span>
              <span class="detail-value muted">{{ formatTime(rec.created_at) }}</span>
            </div>
            <div class="detail-row" v-if="rec.paid_at">
              <span class="detail-label">支付时间</span>
              <span class="detail-value muted">{{ formatTime(rec.paid_at) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 分页 -->
      <div v-if="totalPages > 1" class="pagination-wrapper">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next"
          small
          @current-change="loadRecords"
        />
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Coin, Loading } from '@element-plus/icons-vue'
import { request } from '../api'

const visible = ref(false)
const records = ref<any[]>([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
const totalPages = ref(0)

// 汇总统计
const totalRmb = ref(0)
const totalZs = ref(0)

function open() {
  visible.value = true
  currentPage.value = 1
  loadRecords()
}

function handleClose() {
  records.value = []
  total.value = 0
  totalPages.value = 0
  totalRmb.value = 0
  totalZs.value = 0
}

async function loadRecords() {
  loading.value = true
  try {
    const res = await request<{
      records: any[]
      total: number
      page: number
      page_size: number
      total_pages: number
    }>(`/api/payment/recharge/records?page=${currentPage.value}&page_size=${pageSize.value}`)

    records.value = res.records
    total.value = res.total
    totalPages.value = res.total_pages

    // 计算汇总（如果是第一页才重新计算，否则累加不准确）
    if (currentPage.value === 1) {
      let rmb = 0
      let zs = 0
      for (const rec of res.records) {
        if (rec.status === 'paid') {
          rmb += rec.amount_rmb
          zs += rec.amount_zs
        }
      }
      totalRmb.value = rmb
      totalZs.value = zs
    }
  } catch {
    records.value = []
  } finally {
    loading.value = false
  }
}

function statusTagType(status: string): string {
  if (status === 'paid') return 'success'
  if (status === 'pending') return 'warning'
  if (status === 'expired') return 'info'
  return 'danger'
}

function statusLabel(status: string): string {
  if (status === 'paid') return '已支付'
  if (status === 'pending') return '待支付'
  if (status === 'expired') return '已过期'
  return status
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

defineExpose({ open })
</script>

<style scoped>
.records-body {
  min-height: 200px;
}

.stats-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 14px;
  padding: 12px 16px;
  background: rgba(255,255,255,0.03);
  border-radius: 10px;
  border: 1px solid rgba(255,255,255,0.06);
}

.stat-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.stat-label {
  font-size: 12px;
  color: #888;
}

.stat-value {
  font-size: 18px;
  font-weight: 800;
  color: #ddd;
}

.stat-value.gold {
  color: #fbbf24;
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
  gap: 8px;
}

.record-item {
  padding: 12px 14px;
  background: rgba(255,255,255,0.03);
  border-radius: 8px;
  border: 1px solid rgba(255,255,255,0.06);
}

.record-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.record-order-no {
  font-size: 12px;
  color: #667;
  font-family: monospace;
}

.record-details {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px 16px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  padding: 2px 0;
}

.detail-label {
  color: #888;
}

.detail-value {
  color: #ccc;
  font-weight: 600;
}

.detail-value.gold {
  color: #fbbf24;
}

.detail-value.muted {
  color: #888;
  font-weight: 400;
  font-size: 12px;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 14px;
}
</style>