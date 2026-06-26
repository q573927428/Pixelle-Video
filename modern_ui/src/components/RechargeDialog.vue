<template>
  <el-dialog v-model="visible" title="💰 账户充值" width="360px" class="recharge-dialog" append-to-body @closed="handleClose">
    <div class="recharge-body">
      <!-- 余额信息 -->
      <div class="balance-section">
        <div class="balance-label">当前余额</div>
        <div class="balance-value">{{ auth.zsBalance.value }} <span class="balance-unit">ZS币</span></div>
      </div>

      <!-- 汇率信息 -->
      <div class="rate-section">
        <div class="rate-row">
          <span>兑换比例</span>
          <span><strong>1元</strong> = <strong>{{ exchangeRate }}</strong> ZS币</span>
        </div>
        <div class="rate-row">
          <span>每秒消耗</span>
          <span><strong>{{ zsPerSecond }}</strong> ZS币/秒</span>
        </div>
      </div>

      <!-- 金额选择 -->
      <div class="amount-section">
        <div class="amount-title">选择充值金额</div>
        <div class="amount-grid">
          <div
            v-for="opt in amountOptions"
            :key="opt.rmb"
            class="amount-option"
            :class="{ active: selectedAmount === opt.rmb }"
            @click="selectedAmount = opt.rmb"
          >
            <div class="amount-rmb">¥{{ opt.rmb }}</div>
            <div class="amount-zs">+{{ opt.zs }} ZS币</div>
          </div>
        </div>
      </div>

      <!-- 支付二维码 -->
      <div v-if="!paymentQrUrl" class="pay-start">
        <el-button type="warning" size="large" class="pay-btn" @click="createPayment" :loading="isCreating">
          <el-icon style="margin-right:6px"><Coin /></el-icon>
          微信支付 · ¥{{ selectedAmount }}
        </el-button>
      </div>

      <div v-else class="pay-section">
        <div class="pay-title">微信扫码支付</div>
        <img :src="paymentQrUrl" alt="微信支付二维码" class="qr-img" />
        <div class="pay-hint">
          <el-icon style="margin-right:4px"><WarningFilled /></el-icon>
          请使用微信扫描二维码完成支付
        </div>
        <div class="pay-amount">
          充值金额：<strong style="color:#e6a23c; font-size:22px;">¥{{ selectedAmount }}</strong>
          <div style="font-size:13px; color:#fbbf24; margin-top:4px;">到账 {{ selectedAmount * exchangeRate }} ZS币</div>
        </div>
        <div class="pay-status" v-if="paymentStatus === 'pending'">
          <el-icon class="is-loading"><Loading /></el-icon>
          等待支付...
        </div>
        <div class="pay-status success" v-else-if="paymentStatus === 'paid'">
          <el-icon><CircleCheck /></el-icon>
          充值成功！{{ selectedAmount * exchangeRate }} ZS币已到账
        </div>
        <div class="pay-status error" v-else-if="paymentStatus === 'expired'">
          <el-icon><WarningFilled /></el-icon>
          订单已过期，请重新充值
        </div>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { Coin, WarningFilled, Loading, CircleCheck } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getAuth } from '../composables/useAuth'
import { request } from '../api'

const auth = getAuth()

const visible = ref(false)
const selectedAmount = ref(10)
const exchangeRate = ref(100)
const zsPerSecond = ref(5)
const paymentQrUrl = ref('')
const paymentStatus = ref('')
const orderNo = ref('')
const isCreating = ref(false)
let paymentTimer: ReturnType<typeof setInterval> | null = null

const amountOptions = computed(() => [
  { rmb: 10, zs: 10 * exchangeRate.value },
  { rmb: 50, zs: 50 * exchangeRate.value },
  { rmb: 100, zs: 100 * exchangeRate.value },
  { rmb: 200, zs: 200 * exchangeRate.value },
])

async function fetchPrice() {
  try {
    const res = await request<any>('/api/payment/price')
    exchangeRate.value = parseInt(res.exchange_rate) || 100
    zsPerSecond.value = parseInt(res.zs_per_second) || 5
  } catch {
    // use defaults
  }
}

function open() {
  visible.value = true
  selectedAmount.value = 10
  paymentQrUrl.value = ''
  paymentStatus.value = ''
  orderNo.value = ''
  fetchPrice()
}

function handleClose() {
  stopPolling()
  paymentQrUrl.value = ''
  paymentStatus.value = ''
  orderNo.value = ''
}

async function createPayment() {
  if (isCreating.value) return
  isCreating.value = true
  try {
    const order = await request<{
      order_no: string
      code_url: string
      amount_zs: number
    }>('/api/payment/recharge/create', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...auth._authHeaders(),
      },
      body: JSON.stringify({ amount_rmb: selectedAmount.value }),
    })

    orderNo.value = order.order_no
    paymentStatus.value = 'pending'
    paymentQrUrl.value = `https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=${encodeURIComponent(order.code_url)}`

    startPolling(order.order_no)
  } catch (e: any) {
    ElMessage.error(e.message || '创建充值订单失败')
  } finally {
    isCreating.value = false
  }
}

function startPolling(orderNoStr: string) {
  stopPolling()
  paymentTimer = setInterval(async () => {
    try {
      const res = await request<{
        status: string
        paid_at?: string
      }>(`/api/payment/recharge/order/${orderNoStr}`, {
        headers: { ...auth._authHeaders() },
      })

      if (res.status === 'paid') {
        paymentStatus.value = 'paid'
        stopPolling()
        ElMessage.success('🎉 充值成功！ZS币已到账')

        await auth.fetchMe()

        setTimeout(() => {
          visible.value = false
        }, 3000)
      } else if (res.status === 'expired') {
        paymentStatus.value = 'expired'
        stopPolling()
        ElMessage.warning('订单已过期，请重新充值')
      }
    } catch {
      // 忽略轮询错误
    }
  }, 3000)
}

function stopPolling() {
  if (paymentTimer) {
    clearInterval(paymentTimer)
    paymentTimer = null
  }
}

onUnmounted(() => {
  stopPolling()
})

defineExpose({ open })
</script>

<style scoped>
.recharge-dialog :deep(.el-dialog__body) {
  padding: 0;
}

.recharge-body {
  padding: 16px;
}

.balance-section {
  text-align: center;
  padding: 16px;
  background: rgba(245, 158, 11, 0.06);
  border-radius: 12px;
  margin-bottom: 12px;
  border: 1px solid rgba(245, 158, 11, 0.15);
}

.balance-label {
  font-size: 13px;
  color: #999;
  margin-bottom: 4px;
}

.balance-value {
  font-size: 32px;
  font-weight: 800;
  color: #fbbf24;
}

.balance-unit {
  font-size: 14px;
  color: #f59e0b;
}

.records-link {
  display: inline-flex;
  align-items: center;
  margin-top: 8px;
  font-size: 12px;
  color: #999;
  cursor: pointer;
  transition: color 0.2s;
  padding: 4px 10px;
  border-radius: 6px;
  background: rgba(255,255,255,0.04);
}

.records-link:hover {
  color: #fbbf24;
  background: rgba(245, 158, 11, 0.1);
}

.rate-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px 12px;
  background: rgba(255,255,255,0.03);
  border-radius: 8px;
  margin-bottom: 14px;
}

.rate-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: #aaa;
}

.amount-title {
  font-size: 14px;
  font-weight: 700;
  color: #ddd;
  margin-bottom: 10px;
}

.amount-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-bottom: 14px;
}

.amount-option {
  padding: 12px;
  border-radius: 10px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  cursor: pointer;
  text-align: center;
  transition: all 0.2s;
}

.amount-option.active {
  background: rgba(245, 158, 11, 0.1);
  border-color: #f59e0b;
  box-shadow: 0 0 8px rgba(245, 158, 11, 0.2);
}

.amount-rmb {
  font-size: 18px;
  font-weight: 800;
  color: #fbbf24;
}

.amount-zs {
  font-size: 12px;
  color: #888;
  margin-top: 2px;
}

.pay-start {
  display: flex;
  justify-content: center;
}

.pay-btn {
  width: 100%;
  font-size: 15px;
  font-weight: 700;
  padding: 12px;
  border-radius: 8px;
}

.pay-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 12px;
  background: rgba(255,255,255,0.02);
  border-radius: 10px;
  border: 1px solid rgba(255,255,255,0.06);
}

.pay-title {
  font-size: 15px;
  font-weight: 700;
  color: #07c160;
}

.qr-img {
  width: 160px;
  height: 160px;
  border-radius: 8px;
  border: 2px solid #07c160;
  padding: 4px;
}

.pay-hint {
  display: flex;
  align-items: center;
  font-size: 12px;
  color: #999;
}

.pay-amount {
  text-align: center;
  font-size: 13px;
  color: #ccc;
}

.pay-status {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: #e6a23c;
  padding: 6px 12px;
  background: rgba(230,162,60,0.08);
  border-radius: 8px;
}

.pay-status.success {
  color: #22c55e;
  background: rgba(34,197,94,0.08);
}

.pay-status.error {
  color: #ef4444;
  background: rgba(239,68,68,0.08);
}
</style>