<template>
  <!-- VIP Purchase Dialog -->
  <el-dialog v-model="vipDialogVisible" title="🌟 升级 VIP 会员" width="340px" class="vip-dialog" append-to-body @closed="handleDialogClose">
    <div class="vip-body">
      <!-- Plan Tabs: VIP / SVIP -->
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
          <div class="vip-plan-price">¥688</div>
          <div class="vip-plan-unit">/ 每年</div>
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
          <template v-if="auth.isVip.value && currentPlanType === 'svip' && upgradePriceForCurrentDialog !== null">
            <div class="vip-plan-price svip" style="font-size:18px;">补差价 ¥{{ upgradePriceForCurrentDialog }}</div>
            <div class="vip-plan-unit" style="text-decoration:line-through; color:#666;">原价 ¥1588/年</div>
          </template>
          <template v-else>
            <div class="vip-plan-price svip">¥1588</div>
            <div class="vip-plan-unit">/ 每年 · 无限制</div>
          </template>
        </div>
      </div>

      <!-- Features Comparison -->
      <div class="vip-compare">
        <div class="vip-compare-header">
          <div class="vip-compare-col plan-col-free">免费用户</div>
          <div class="vip-compare-col plan-col-vip">{{ currentPlanType === 'svip' ? 'SVIP 会员' : 'VIP 会员' }}</div>
        </div>
        <div class="vip-compare-row">
          <div class="vip-compare-col plan-col-free"><span class="cmp-remove">✕</span> 每日 1 次</div>
          <div class="vip-compare-col plan-col-vip">
            <template v-if="currentPlanType === 'svip'"><span class="cmp-check">✓</span> 无限制</template>
            <template v-else><span class="cmp-check">✓</span> 每天 10 次</template>
          </div>
        </div>
        <div class="vip-compare-row vip-compare-row-word">
          <div class="vip-compare-col plan-col-free">
            文案最多 <strong class="text-free">150</strong> 字
            <div class="word-duration">生成视频时长约30秒</div>
          </div>
          <div class="vip-compare-col plan-col-vip">
            文案最多 <strong class="text-vip">368</strong> 字
            <div class="word-duration">生成视频时长约80秒</div>
          </div>
        </div>
        <div class="vip-compare-row">
          <div class="vip-compare-col plan-col-free"><span class="cmp-remove">✕</span> 添加字幕</div>
          <div class="vip-compare-col plan-col-vip"><span class="cmp-check">✓</span> 添加字幕</div>
        </div>
        <div class="vip-compare-row">
          <div class="vip-compare-col plan-col-free">基础模板</div>
          <div class="vip-compare-col plan-col-vip">全部模板</div>
        </div>
        <div class="vip-compare-row">
          <div class="vip-compare-col plan-col-free">720p 高清画质</div>
          <div class="vip-compare-col plan-col-vip">1080P 高清画质</div>
        </div>
        <div class="vip-compare-row">
          <div class="vip-compare-col plan-col-free">标准队列</div>
          <div class="vip-compare-col plan-col-vip">优先队列</div>
        </div>
        <div class="vip-compare-row">
          <div class="vip-compare-col plan-col-free"><span class="cmp-remove">✕</span> 专属客服</div>
          <div class="vip-compare-col plan-col-vip"><span class="cmp-check">✓</span> 专属客服</div>
        </div>
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
        <!-- 状态提示 -->
        <div class="vip-pay-status" v-if="paymentStatus === 'pending'">
          <el-icon class="is-loading"><Loading /></el-icon>
          等待支付...
        </div>
        <div class="vip-pay-status success" v-else-if="paymentStatus === 'paid'">
          <el-icon><CircleCheck /></el-icon>
          支付成功！VIP 已开通
        </div>
        <div class="vip-pay-status error" v-else-if="paymentStatus === 'expired'">
          <el-icon><WarningFilled /></el-icon>
          订单已过期，请重新下单
        </div>
      </div>
    </div>
  </el-dialog>

  <!-- Upgrade to SVIP Dialog -->
  <el-dialog v-model="upgradeDialogVisible" title="🚀 升级到 SVIP 会员" width="340px" class="vip-dialog" append-to-body @closed="handleUpgradeDialogClose">
    <div class="vip-body">
      <!-- 报价信息 -->
      <div v-if="upgradeQuote" class="upgrade-quote-section">
        <div class="upgrade-quote-icon">⬆️</div>
        <div class="upgrade-quote-title">升级方案</div>

        <div class="upgrade-detail-row">
          <span class="upgrade-detail-label">当前身份</span>
          <el-tag type="warning" size="small">VIP 会员</el-tag>
        </div>
        <div class="upgrade-detail-row">
          <span class="upgrade-detail-label">VIP 剩余天数</span>
          <span class="upgrade-detail-value">{{ upgradeQuote.vip_remaining_days }} 天</span>
        </div>
        <div class="upgrade-detail-row">
          <span class="upgrade-detail-label">目标身份</span>
          <el-tag type="danger" size="small">SVIP 会员</el-tag>
        </div>

        <div class="upgrade-divider"></div>

        <div class="upgrade-price-area">
          <div class="upgrade-original-price" v-if="upgradeQuote.mode === 'upgrade'">
            SVIP 原价 <s>¥{{ upgradeQuote.original_price }}</s>
          </div>
          <div class="upgrade-need-pay">
            <template v-if="upgradeQuote.mode === 'upgrade'">
              只需补差价 <strong class="upgrade-price-num">¥{{ upgradeQuote.need_pay }}</strong>
            </template>
            <template v-else>
              需支付 <strong class="upgrade-price-num">¥{{ upgradeQuote.need_pay }}</strong>
            </template>
          </div>
          <div class="upgrade-new-expiry" v-if="upgradeQuote.new_expiry">
            升级后到期 {{ new Date(upgradeQuote.new_expiry).toLocaleDateString('zh-CN') }}
          </div>
          <div class="upgrade-tip" v-if="upgradeQuote.mode === 'upgrade'">
            💡 已使用的 VIP 时长按日均价折算，只需补剩余天数的差价。VIP 剩余天数自动转为 SVIP。
          </div>
        </div>
      </div>

      <!-- Payment QR Code -->
      <div v-if="!upgradePaymentQrUrl" class="vip-pay-start">
        <el-button type="danger" size="large" class="vip-pay-btn" @click="createUpgradePayment" :loading="isCreatingUpgradePayment">
          <el-icon style="margin-right:6px"><Coin /></el-icon>
          微信支付 · ¥{{ upgradeQuote?.need_pay || '--' }}
        </el-button>
      </div>

      <div v-else class="vip-pay-section">
        <div class="vip-pay-title">微信扫码支付</div>
        <img :src="upgradePaymentQrUrl" alt="微信支付二维码" class="vip-qr-img" />
        <div class="vip-pay-hint">
          <el-icon style="margin-right:4px"><WarningFilled /></el-icon>
          请使用微信扫描二维码完成支付
        </div>
        <div class="vip-pay-amount">
          支付金额：<strong style="color:#e6a23c; font-size:22px;">¥{{ upgradeQuote?.need_pay }}</strong>
        </div>
        <div class="vip-pay-status" v-if="upgradePaymentStatus === 'pending'">
          <el-icon class="is-loading"><Loading /></el-icon>
          等待支付...
        </div>
        <div class="vip-pay-status success" v-else-if="upgradePaymentStatus === 'paid'">
          <el-icon><CircleCheck /></el-icon>
          支付成功！已升级为 SVIP
        </div>
        <div class="vip-pay-status error" v-else-if="upgradePaymentStatus === 'expired'">
          <el-icon><WarningFilled /></el-icon>
          订单已过期，请重新操作
        </div>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, onUnmounted } from 'vue'
import { Coin, WarningFilled, Loading, CircleCheck, CircleCheckFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getAuth } from '../composables/useAuth'
import { request } from '../api'

const auth = getAuth()

const vipDialogVisible = ref(false)
const upgradeDialogVisible = ref(false)

// ========== VIP Purchase Logic ==========

const currentPlanType = ref('vip')
const upgradePriceForCurrentDialog = ref<number | null>(null)
const currentPlanPrice = computed(() => {
  if (auth.isVip.value && currentPlanType.value === 'svip' && upgradePriceForCurrentDialog.value !== null) {
    return upgradePriceForCurrentDialog.value
  }
  return currentPlanType.value === 'svip' ? 1588 : 688
})
const paymentQrUrl = ref('')
const paymentStatus = ref('') // pending / paid / expired
const orderNo = ref('')
const isCreatingPayment = ref(false)
let paymentTimer: ReturnType<typeof setInterval> | null = null

function switchPlan(plan: string) {
  if (paymentQrUrl.value) return // 支付进行中，不允许切换
  currentPlanType.value = plan
  upgradePriceForCurrentDialog.value = null

  // 如果当前用户是 VIP 且切到 SVIP，查询补差价
  if (plan === 'svip' && auth.isVip.value) {
    request<{ need_pay: number }>('/api/payment/upgrade-quote', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...auth._authHeaders(),
      },
      body: JSON.stringify({ target_plan: 'svip' }),
    }).then(res => {
      upgradePriceForCurrentDialog.value = res.need_pay
    }).catch(() => {
      // 查询失败则显示全价
    })
  }
}

function openVipDialog() {
  vipDialogVisible.value = true
  currentPlanType.value = 'vip'
  paymentQrUrl.value = ''
  paymentStatus.value = ''
  orderNo.value = ''
  upgradePriceForCurrentDialog.value = null
}

function handleDialogClose() {
  stopPolling()
  paymentQrUrl.value = ''
  paymentStatus.value = ''
  orderNo.value = ''
}

async function createAndShowPayment() {
  if (isCreatingPayment.value) return
  isCreatingPayment.value = true
  try {
    const order = await request<{
      order_no: string
      code_url: string
      amount: number
      plan_type: string
      plan_name: string
    }>('/api/payment/create', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...auth._authHeaders(),
      },
      body: JSON.stringify({ plan_type: currentPlanType.value }),
    })

    orderNo.value = order.order_no
    currentPlanType.value = order.plan_type
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
        vip_expires_at?: string
      }>(`/api/payment/order/${orderNoStr}`, {
        headers: { ...auth._authHeaders() },
      })

      if (res.status === 'paid') {
        paymentStatus.value = 'paid'
        stopPolling()
        ElMessage.success('🎉 支付成功！VIP 已自动开通')

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

// ========== Upgrade to SVIP Logic ==========

interface UpgradeQuote {
  need_pay: number
  mode: string
  vip_remaining_days: number
  extra_svip_days: number
  original_price: number
  new_expiry: string | null
}

const upgradeQuote = ref<UpgradeQuote | null>(null)
const upgradePaymentQrUrl = ref('')
const upgradePaymentStatus = ref('')
const upgradeOrderNo = ref('')
const isCreatingUpgradePayment = ref(false)
let upgradePaymentTimer: ReturnType<typeof setInterval> | null = null

function openUpgradeDialog() {
  upgradeDialogVisible.value = true
  upgradePaymentQrUrl.value = ''
  upgradePaymentStatus.value = ''
  upgradeOrderNo.value = ''

  request<UpgradeQuote>('/api/payment/upgrade-quote', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...auth._authHeaders(),
    },
    body: JSON.stringify({ target_plan: 'svip' }),
  }).then(quote => {
    upgradeQuote.value = quote
  }).catch((e: any) => {
    ElMessage.error(e.message || '获取升级报价失败')
    upgradeDialogVisible.value = false
  })
}

function handleUpgradeDialogClose() {
  stopUpgradePolling()
  upgradeQuote.value = null
  upgradePaymentQrUrl.value = ''
  upgradePaymentStatus.value = ''
  upgradeOrderNo.value = ''
}

async function createUpgradePayment() {
  if (isCreatingUpgradePayment.value) return
  isCreatingUpgradePayment.value = true
  try {
    const order = await request<{
      order_no: string
      code_url: string
      amount: number
      plan_type: string
      plan_name: string
    }>('/api/payment/create', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...auth._authHeaders(),
      },
      body: JSON.stringify({ plan_type: 'svip' }),
    })

    upgradeOrderNo.value = order.order_no
    upgradePaymentStatus.value = 'pending'
    upgradePaymentQrUrl.value = `https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=${encodeURIComponent(order.code_url)}`

    startUpgradePolling(order.order_no)
  } catch (e: any) {
    ElMessage.error(e.message || '创建升级订单失败')
  } finally {
    isCreatingUpgradePayment.value = false
  }
}

function startUpgradePolling(orderNoStr: string) {
  stopUpgradePolling()
  upgradePaymentTimer = setInterval(async () => {
    try {
      const res = await request<{
        status: string
        paid_at?: string
        vip_expires_at?: string
      }>(`/api/payment/order/${orderNoStr}`, {
        headers: { ...auth._authHeaders() },
      })

      if (res.status === 'paid') {
        upgradePaymentStatus.value = 'paid'
        stopUpgradePolling()
        ElMessage.success('🎉 升级成功！您已升级为 SVIP 会员')

        await auth.fetchMe()

        setTimeout(() => {
          upgradeDialogVisible.value = false
        }, 5000)
      } else if (res.status === 'expired') {
        upgradePaymentStatus.value = 'expired'
        stopUpgradePolling()
        ElMessage.warning('订单已过期，请重新操作')
      }
    } catch {
      // 忽略轮询错误
    }
  }, 3000)
}

function stopUpgradePolling() {
  if (upgradePaymentTimer) {
    clearInterval(upgradePaymentTimer)
    upgradePaymentTimer = null
  }
}

onUnmounted(() => {
  stopPolling()
  stopUpgradePolling()
})

defineExpose({
  openVipDialog,
  openUpgradeDialog,
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
  padding: 10px 6px;
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
  font-size: 22px;
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

.text-free {
  color: #94a3b8;
}

.text-vip {
  color: #d8b4fe;
  font-size: 14px;
}

.vip-compare-row-word {
  background: rgba(124, 58, 237, 0.04);
}

.word-duration {
  font-size: 10px;
  color: #888;
  margin-top: 2px;
  line-height: 1.2;
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

/* Upgrade Dialog Styles */
.upgrade-quote-section {
  padding: 4px 0;
}

.upgrade-quote-icon {
  text-align: center;
  font-size: 36px;
  margin-bottom: 6px;
}

.upgrade-quote-title {
  text-align: center;
  font-size: 15px;
  font-weight: 700;
  color: #ddd;
  margin-bottom: 14px;
}

.upgrade-detail-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.upgrade-detail-label {
  font-size: 12px;
  color: #999;
}

.upgrade-detail-value {
  font-size: 12px;
  color: #ddd;
  font-weight: 600;
}

.upgrade-detail-value.highlight {
  color: #22c55e;
  font-weight: 700;
}

.upgrade-divider {
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(139, 92, 246, 0.4), transparent);
  margin: 14px 0;
}

.upgrade-price-area {
  text-align: center;
  padding: 6px 0;
}

.upgrade-original-price {
  font-size: 12px;
  color: #888;
  margin-bottom: 6px;
}

.upgrade-original-price s {
  color: #666;
}

.upgrade-need-pay {
  font-size: 15px;
  color: #ddd;
  margin-bottom: 6px;
}

.upgrade-price-num {
  color: #e6a23c;
  font-size: 24px;
  font-weight: 800;
  margin-left: 6px;
}

.upgrade-new-expiry {
  font-size: 11px;
  color: #888;
  margin-top: 4px;
}

.upgrade-tip {
  margin-top: 10px;
  padding: 8px 10px;
  background: rgba(139, 92, 246, 0.08);
  border-radius: 8px;
  font-size: 11px;
  color: #a78bfa;
  line-height: 1.4;
  text-align: left;
}
</style>