<template>
  <!-- VIP/SVIP Monthly Purchase Dialog -->
  <el-dialog v-model="vipDialogVisible" title="🌟 开通 VIP 会员" width="360px" class="vip-dialog" append-to-body @closed="handleDialogClose">
    <div class="vip-body">
      <!-- Plan Selection: VIP / SVIP -->
      <div class="vip-plan-tabs">
        <div
          class="vip-plan-tab"
          :class="{ active: currentPlanType === 'vip' }"
          @click="switchPlan('vip')"
        >
          <div class="vip-plan-check" v-if="currentPlanType === 'vip'">
            <el-icon><CircleCheckFilled /></el-icon>
          </div>
          <div class="vip-plan-name">VIP 会员</div>
          <div class="vip-plan-price">¥{{ vipPrice }}</div>
          <div class="vip-plan-unit">/ 每月</div>
          <div class="vip-plan-bonus">送 {{ vipBonusZs }} ZS币</div>
        </div>
        <div
          class="vip-plan-tab"
          :class="{ active: currentPlanType === 'svip' }"
          @click="switchPlan('svip')"
        >
          <div class="vip-plan-check" v-if="currentPlanType === 'svip'">
            <el-icon><CircleCheckFilled /></el-icon>
          </div>
          <div class="vip-plan-name hot">SVIP 会员 🔥</div>
          <div class="vip-plan-price svip">¥{{ svipPrice }}</div>
          <div class="vip-plan-unit">/ 每月</div>
          <div class="vip-plan-bonus">送 {{ svipBonusZs }} ZS币</div>
        </div>
      </div>

      <!-- Features Comparison -->
      <div class="vip-compare">
        <div class="vip-compare-header">
          <div class="vip-compare-col plan-col-free">普通用户</div>
          <div class="vip-compare-col plan-col-vip">{{ currentPlanType === 'svip' ? 'SVIP' : 'VIP' }}</div>
        </div>
        <div class="vip-compare-row">
          <div class="vip-compare-col plan-col-free"><span class="cmp-remove">✕</span> 队列优先级</div>
          <div class="vip-compare-col plan-col-vip"><span class="cmp-check">✓</span> 优先队列</div>
        </div>
        <div class="vip-compare-row">
          <div class="vip-compare-col plan-col-free">生成折扣：无折扣</div>
          <div class="vip-compare-col plan-col-vip">
            <template v-if="currentPlanType === 'svip'"><span class="cmp-check">✓</span> 8折</template>
            <template v-else><span class="cmp-check">✓</span> 9折</template>
          </div>
        </div>
        <div class="vip-compare-row">
          <div class="vip-compare-col plan-col-free"><span class="cmp-remove">✕</span> 赠送ZS币</div>
          <div class="vip-compare-col plan-col-vip">
            <span class="cmp-check">✓</span> +{{ currentPlanType === 'svip' ? svipBonusZs : vipBonusZs }}
          </div>
        </div>
        <div class="vip-compare-row">
          <div class="vip-compare-col plan-col-free"><span class="cmp-remove">✕</span> 生成次数</div>
          <div class="vip-compare-col plan-col-vip"><span class="cmp-check">✓</span> 无限生成</div>
        </div>
        <div class="vip-compare-row">
          <div class="vip-compare-col plan-col-free"><span class="cmp-remove">✕</span> 专属客服</div>
          <div class="vip-compare-col plan-col-vip"><span class="cmp-check">✓</span> 专属客服</div>
        </div>
      </div>

      <!-- Current VIP status info -->
      <div v-if="auth.isVipEffective.value" class="vip-current-status">
        <el-tag type="warning" size="small" v-if="auth.isVip.value">VIP 会员</el-tag>
        <el-tag type="danger" size="small" v-else-if="auth.isSvip.value">SVIP 会员</el-tag>
        <span class="vip-expiry-text">
          有效期至：{{ formatDate(auth.vipExpiresAt.value) }}
          <template v-if="currentPlanType === 'svip' && auth.isVip.value">
            （续费升级为SVIP）
          </template>
          <template v-else>
            （续费延长有效期）
          </template>
        </span>
      </div>

      <!-- Payment QR Code Section -->
      <div v-if="!paymentQrUrl" class="vip-pay-start">
        <el-button type="warning" size="large" class="vip-pay-btn" @click="createAndShowPayment" :loading="isCreatingPayment">
          <el-icon style="margin-right:6px"><Coin /></el-icon>
          微信支付 · ¥{{ currentPlanPrice }}
        </el-button>
      </div>

      <div v-else class="vip-pay-section">
        <div class="vip-pay-title">微信扫码支付</div>
        <img :src="paymentQrUrl" alt="微信支付二维码" class="vip-qr-img" />
        <div class="vip-pay-hint">
          <el-icon style="margin-right:4px"><WarningFilled /></el-icon>
          请使用微信扫描二维码完成支付
        </div>
        <div class="vip-pay-amount">
          支付金额：<strong style="color:#e6a23c; font-size:22px;">¥{{ currentPlanPrice }}</strong>
        </div>
        <div class="vip-pay-status" v-if="paymentStatus === 'pending'">
          <el-icon class="is-loading"><Loading /></el-icon>
          等待支付...
        </div>
        <div class="vip-pay-status success" v-else-if="paymentStatus === 'paid'">
          <el-icon><CircleCheck /></el-icon>
          支付成功！会员已开通
        </div>
        <div class="vip-pay-status error" v-else-if="paymentStatus === 'expired'">
          <el-icon><WarningFilled /></el-icon>
          订单已过期，请重新下单
        </div>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { Coin, WarningFilled, Loading, CircleCheck, CircleCheckFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getAuth } from '../composables/useAuth'
import { request } from '../api'

const auth = getAuth()

const vipDialogVisible = ref(false)

// ========== Plan Info ==========
const vipPrice = ref(29)
const vipBonusZs = ref(3900)
const svipPrice = ref(89)
const svipBonusZs = ref(10000)

async function loadPlanInfo() {
  try {
    const plans: any = await request('/api/payment/vip/plans')
    vipPrice.value = plans.vip?.price ?? 29
    vipBonusZs.value = plans.vip?.bonus_zs ?? 3900
    svipPrice.value = plans.svip?.price ?? 89
    svipBonusZs.value = plans.svip?.bonus_zs ?? 10000
  } catch {
    // use defaults
  }
}

const currentPlanType = ref('vip')
const currentPlanPrice = computed(() => currentPlanType.value === 'svip' ? svipPrice.value : vipPrice.value)

const paymentQrUrl = ref('')
const paymentStatus = ref('') // pending / paid / expired
const orderNo = ref('')
const isCreatingPayment = ref(false)
let paymentTimer: ReturnType<typeof setInterval> | null = null

function switchPlan(plan: string) {
  if (paymentQrUrl.value) return // 支付进行中，不允许切换
  currentPlanType.value = plan
}

function openVipDialog() {
  vipDialogVisible.value = true
  currentPlanType.value = 'vip'
  paymentQrUrl.value = ''
  paymentStatus.value = ''
  orderNo.value = ''
}

function handleDialogClose() {
  stopPolling()
  paymentQrUrl.value = ''
  paymentStatus.value = ''
  orderNo.value = ''
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '--'
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

async function createAndShowPayment() {
  if (isCreatingPayment.value) return
  isCreatingPayment.value = true
  try {
    const order = await request<{
      order_no: string
      code_url: string
      amount_rmb: number
      plan_type: string
      bonus_zs: number
    }>('/api/payment/vip/create', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...auth._authHeaders(),
      },
      body: JSON.stringify({ plan_type: currentPlanType.value }),
    })

    orderNo.value = order.order_no
    paymentStatus.value = 'pending'
    paymentQrUrl.value = `https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=${encodeURIComponent(order.code_url)}`

    startPolling(order.order_no)
  } catch (e: any) {
    ElMessage.error(e.message || '创建订单失败')
  } finally {
    isCreatingPayment.value = false
  }
}

function startPolling(orderNoStr: string) {
  stopPolling()
  paymentTimer = setInterval(async () => {
    try {
      const res = await request<{
        status: string
        paid_at?: string
        bonus_zs?: number
      }>(`/api/payment/vip/order/${orderNoStr}`, {
        headers: { ...auth._authHeaders() },
      })

      if (res.status === 'paid') {
        paymentStatus.value = 'paid'
        stopPolling()
        ElMessage.success('🎉 支付成功！会员已开通')

        await auth.fetchMe()

        setTimeout(() => {
          vipDialogVisible.value = false
        }, 5000)
      } else if (res.status === 'expired') {
        paymentStatus.value = 'expired'
        stopPolling()
        ElMessage.warning('订单已过期，请重新下单')
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

onMounted(() => {
  loadPlanInfo()
})

onUnmounted(() => {
  stopPolling()
})

defineExpose({
  openVipDialog,
})
</script>

<style scoped>
/* VIP Dialog Styles */
:deep(.vip-dialog) {
  overflow: hidden;
}
:deep(.vip-dialog .el-dialog__body) {
  padding: 0;
}

.vip-body {
  padding: 16px 12px;
  overflow-x: hidden;
  box-sizing: border-box;
}

/* Plan Tabs */
.vip-plan-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 14px;
}

.vip-plan-tab {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 6px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
}

.vip-plan-tab:hover {
  background: rgba(255, 255, 255, 0.06);
}

.vip-plan-tab.active {
  background: rgba(230, 162, 60, 0.08);
  border-color: rgba(230, 162, 60, 0.4);
}

.vip-plan-check {
  position: absolute;
  top: 6px;
  right: 6px;
  font-size: 16px;
  color: #22c55e;
}

.vip-plan-name {
  font-size: 13px;
  font-weight: 700;
  color: #ddd;
  margin-bottom: 4px;
}

.vip-plan-name.hot {
  color: #fbbf24;
}

.vip-plan-price {
  font-size: 24px;
  font-weight: 800;
  color: #e6a23c;
}

.vip-plan-price.svip {
  color: #f59e0b;
}

.vip-plan-unit {
  font-size: 10px;
  color: #999;
  margin-top: 2px;
}

.vip-plan-bonus {
  margin-top: 4px;
  font-size: 11px;
  color: #22c55e;
  font-weight: 600;
  padding: 2px 8px;
  background: rgba(34, 197, 94, 0.1);
  border-radius: 4px;
}

/* Features Comparison */
.vip-compare {
  margin-bottom: 14px;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.vip-compare-header {
  display: flex;
  font-weight: 800;
  font-size: 13px;
}

.vip-compare-header .plan-col-free {
  color: #94a3b8;
  padding: 8px;
  background: rgba(100, 116, 139, 0.1);
}

.vip-compare-header .plan-col-vip {
  color: #d8b4fe;
  padding: 8px;
  background: rgba(124, 58, 237, 0.18);
}

.vip-compare-row {
  display: flex;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.vip-compare-col {
  flex: 1;
  padding: 6px;
  font-size: 12px;
  color: #ccc;
  word-break: break-word;
  box-sizing: border-box;
}

.plan-col-free {
  border-right: 1px solid rgba(255, 255, 255, 0.05);
  background: rgba(100, 116, 139, 0.05);
}

.plan-col-vip {
  background: rgba(124, 58, 237, 0.14);
}

.cmp-check {
  color: #22c55e;
  font-weight: 700;
  margin-right: 4px;
}

.cmp-remove {
  color: #ef4444;
  font-weight: 700;
  margin-right: 4px;
}

/* Current VIP Status */
.vip-current-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(230, 162, 60, 0.06);
  border-radius: 8px;
  margin-bottom: 14px;
  font-size: 12px;
  color: #ccc;
  flex-wrap: wrap;
}

.vip-expiry-text {
  color: #999;
  font-size: 11px;
}

/* Payment Section */
.vip-pay-start {
  display: flex;
  justify-content: center;
  padding: 8px 0 4px;
}

.vip-pay-btn {
  width: 100%;
  font-size: 15px;
  font-weight: 700;
  padding: 12px;
  border-radius: 8px;
}

.vip-pay-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.02);
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.vip-pay-title {
  font-size: 15px;
  font-weight: 700;
  color: #07c160;
  margin-bottom: 2px;
}

.vip-qr-img {
  width: 160px;
  height: 160px;
  border-radius: 8px;
  border: 2px solid #07c160;
  padding: 4px;
}

.vip-pay-hint {
  display: flex;
  align-items: center;
  font-size: 12px;
  color: #999;
  margin-top: 2px;
}

.vip-pay-amount {
  font-size: 13px;
  color: #ccc;
  margin-top: 2px;
}

.vip-pay-status {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: #e6a23c;
  margin-top: 4px;
  padding: 6px 12px;
  background: rgba(230, 162, 60, 0.08);
  border-radius: 8px;
  max-width: 100%;
  box-sizing: border-box;
}

.vip-pay-status.success {
  color: #22c55e;
  background: rgba(34, 197, 94, 0.08);
}

.vip-pay-status.error {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.08);
}
</style>