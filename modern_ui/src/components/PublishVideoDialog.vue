<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="$emit('update:visible', $event)"
    :title="publishMode === 'progress' ? `📤 正在发布到 ${platformLabel}` : `📤 发布到 ${platformLabel}`"
    :close-on-click-modal="false"
    top="8vh"
    width="60%"
    class="publish-dialog"
    destroy-on-close
    :before-close="handleClose"
  >
    <!-- 发布进度模式 -->
    <div v-if="publishMode === 'progress'" class="progress-mode">
      <!-- 进度标题 -->
      <div class="progress-header">
        <div class="progress-platform-icon">{{ currentPlatform?.icon }}</div>
        <div class="progress-title">
          <h3>{{ progressMessage || `正在发布到${platformLabel}...` }}</h3>
          <el-progress
            :percentage="Math.round(publishProgress)"
            :status="publishStatus === 'success' ? 'success' : publishStatus === 'failed' ? 'exception' : undefined"
            :stroke-width="8"
            style="max-width:400px;margin-top:8px;"
          />
        </div>
      </div>

      <!-- 步骤列表 -->
      <div class="progress-steps">
        <div
          v-for="(step, idx) in publishSteps"
          :key="step.key"
          class="progress-step"
          :class="{
            'is-completed': stepIndex > idx,
            'is-active': stepIndex === idx && publishStatus !== 'success' && publishStatus !== 'failed',
            'is-error': stepIndex === idx && publishStatus === 'failed',
            'is-waiting': stepIndex < idx
          }"
        >
          <div class="step-icon">
            <el-icon v-if="stepIndex > idx || (stepIndex >= idx && publishStatus === 'success')"><CircleCheck /></el-icon>
            <el-icon v-else-if="stepIndex === idx && publishStatus === 'failed'" class="error-icon"><CircleClose /></el-icon>
            <el-icon v-else-if="stepIndex === idx" class="loading-icon"><Loading /></el-icon>
            <span v-else class="step-number">{{ idx + 1 }}</span>
          </div>
          <div class="step-content">
            <div class="step-label">{{ step.label }}</div>
            <div class="step-desc" v-if="stepIndex === idx && stepMessage">{{ stepMessage }}</div>
          </div>
        </div>
      </div>

      <!-- 二维码扫码区域（登录步骤时显示） -->
      <div v-if="showQRCode" class="qr-login-area">
        <div class="qr-card">
          <div class="qr-title">📱 请使用{{ platformLabel }}App扫码登录</div>
          <div class="qr-image-wrap">
            <img :src="qrImageData" class="qr-image" alt="扫码登录" />
          </div>
          <div class="qr-tip">{{ qrTip || '打开抖音App扫一扫登录' }}</div>
          <div class="qr-actions">
            <el-button size="small" @click="refreshQRCode" :disabled="qrRefreshing">
              {{ qrRefreshing ? '刷新中...' : '🔄 二维码已失效？点击刷新' }}
            </el-button>
          </div>
        </div>
      </div>

      <!-- 发布结果 -->
      <div v-if="publishStatus === 'success'" class="publish-result success-result">
        <el-result icon="success" title="发布成功！" :sub-title="`视频已成功发布到${platformLabel}`">
          <template #extra>
            <el-link v-if="platformUrl" :href="platformUrl" target="_blank" type="primary" style="font-size:16px;">
              🔗 查看视频
            </el-link>
          </template>
        </el-result>
      </div>
      <div v-else-if="publishStatus === 'failed'" class="publish-result fail-result">
        <el-result icon="error" title="发布失败" :sub-title="errorMessage || '请稍后重试'">
          <template #extra>
            <el-button type="primary" @click="retryPublish">重新发布</el-button>
          </template>
        </el-result>
      </div>
    </div>

    <!-- 编辑模式 / 登录检测模式 -->
    <div v-else class="publish-layout">
      <!-- 登录检测/扫码覆盖层（在编辑模式中显示） -->
      <div v-if="loginCheckActive" class="login-overlay">
        <div v-if="loginStatus === 'checking'" class="login-loading">
          <el-icon class="loading-icon" :size="32"><Loading /></el-icon>
          <p>正在检测登录状态...</p>
        </div>
        <div v-else-if="loginStatus === 'need_qr'" class="login-qr-content">
          <div class="qr-card">
            <div class="qr-title">📱 请使用{{ platformLabel }}App扫码登录</div>
            <div class="qr-image-wrap">
              <img v-if="qrImageData" :src="qrImageData" class="qr-image" alt="扫码登录" />
              <div v-else class="qr-loading">
                <el-icon class="loading-icon" :size="32"><Loading /></el-icon>
                <p>正在获取二维码...</p>
              </div>
            </div>
            <div class="qr-tip">{{ qrTip || `打开${platformLabel}App扫一扫登录` }}</div>
            <div class="qr-actions">
              <el-button size="small" @click="refreshQRCode" :disabled="qrRefreshing">
                {{ qrRefreshing ? '刷新中...' : '🔄 二维码已失效？点击刷新' }}
              </el-button>
            </div>
          </div>
        </div>
      </div>
      <!-- 左侧：视频预览 -->
      <div class="publish-left">
        <div class="publish-section-title">🎬 视频预览</div>
        <div class="publish-video-wrap">
          <video
            v-if="videoUrl"
            :src="videoUrl"
            controls
            muted
            playsinline
            preload="metadata"
            class="publish-video"
          />
          <div v-else class="publish-video-empty">
            <div style="font-size:32px;">🎞️</div>
            <div class="small muted">暂无视频</div>
          </div>
        </div>

        <!-- 封面设置 -->
        <div class="cover-section">
          <div class="publish-section-title">🎨 封面设置</div>
          <div class="cover-row">
            <div class="cover-item">
              <div class="cover-label">竖屏封面 (3:4)</div>
              <div class="cover-upload-wrap">
                <img v-if="frameSrc" :src="frameSrc" class="cover-preview" />
                <div v-else class="cover-placeholder">
                  <el-icon style="font-size:28px;color:#999;"><VideoCamera /></el-icon>
                  <span class="small muted">自动截取第一帧</span>
                </div>
              </div>
            </div>
            <div class="cover-item">
              <div class="cover-label">横屏封面 (4:3)</div>
              <div class="cover-upload-wrap landscape">
                <img v-if="frameSrc" :src="frameSrc" class="cover-preview" />
                <div v-else class="cover-placeholder">
                  <el-icon style="font-size:28px;color:#999;"><VideoCamera /></el-icon>
                  <span class="small muted">自动截取第一帧</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 已绑定账号 -->
        <div class="bound-accounts" v-if="boundAccounts.length > 0">
          <div class="publish-section-title">🔗 已绑定账号</div>
          <div class="account-chips">
            <el-tag
              v-for="acc in boundAccounts"
              :key="acc.id"
              :type="acc.status === 'active' ? 'success' : 'info'"
              size="small"
              closable
              @close="handleUnbindAccount(acc.id)"
            >
              {{ platformIcon(acc.platform) }} {{ acc.account_name || acc.platform }}
            </el-tag>
          </div>
        </div>
      </div>

      <!-- 右侧：发布配置 -->
      <div class="publish-right">
        <div class="publish-section-title">📝 发布配置</div>

        <el-form label-position="top" class="publish-form">
          <el-form-item label="视频标题">
            <div class="title-input-row">
              <el-input v-model="publishTitle" placeholder="请输入视频标题" maxlength="100" show-word-limit />
              <el-button
                type="primary"
                size="small"
                :loading="aiLoading"
                :disabled="!publishText"
                @click="handleAIGenerate"
                class="ai-btn"
              >
                <el-icon><MagicStick /></el-icon>
                {{ aiLoading ? '生成中' : 'AI生成' }}
              </el-button>
            </div>
          </el-form-item>

          <el-form-item label="文案内容">
            <el-input
              v-model="publishText"
              type="textarea"
              :rows="8"
              placeholder="请输入文案内容"
              maxlength="1200"
              show-word-limit
            />
          </el-form-item>

          <el-form-item label="话题标签">
            <el-input
              v-model="publishTopics"
              placeholder="多个话题用逗号分隔，如：AI技术,数字人,短视频"
            />
          </el-form-item>

          <!-- 选择发布平台 -->
          <div class="publish-platform-select">
            <div class="publish-section-title">📤 选择发布平台</div>
            <div class="publish-platform-buttons">
              <el-button
                v-for="p in publishPlatforms"
                :key="p.key"
                :type="selectedPlatform === p.key ? p.type : 'default'"
                size="large"
                class="publish-platform-btn"
                @click="selectedPlatform = p.key"
                :plain="selectedPlatform !== p.key"
              >
                <span style="font-size:20px;margin-right:4px;">{{ p.icon }}</span>
                {{ p.label }}
              </el-button>
            </div>
          </div>
        </el-form>
      </div>
    </div>

    <!-- 底部按钮 -->
    <template #footer>
      <div class="publish-footer">
        <!-- 进度模式底部按钮 -->
        <template v-if="publishMode === 'progress'">
          <div class="publish-actions" style="width:100%;justify-content:center;">
            <el-button v-if="publishStatus === 'success' || publishStatus === 'failed'" type="primary" @click="closeDialog">
              关闭
            </el-button>
            <el-button v-else @click="cancelPublish" :disabled="publishStatus === 'success'">
              取消发布
            </el-button>
          </div>
        </template>

        <!-- 编辑模式底部按钮 -->
        <template v-else>
          <div class="publish-status" v-if="publishStatus">
            <el-tag :type="publishSuccess ? 'success' : 'danger'" effect="dark">
              {{ publishSuccess ? '✅ 发布成功！' : '❌ 发布失败：' + publishStatus }}
            </el-tag>
          </div>
          <div class="publish-actions">
            <el-button @click="$emit('update:visible', false)" :disabled="publishing">取消</el-button>
            <el-button
              type="primary"
              @click="handlePublish"
              :loading="publishing"
              :disabled="!publishTitle || !publishText"
            >
              {{ publishing ? '发布中...' : `🚀 发布到 ${platformLabel}` }}
            </el-button>
          </div>
        </template>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { VideoCamera, MagicStick, CircleCheck, CircleClose, Loading } from '@element-plus/icons-vue'
import { generatePublishPrepare, startPublish, createPublishWS, listPublishAccounts, deletePublishAccount } from '../api'
import type { PublishStartRequest, AccountInfo } from '../api'

const publishPlatforms = [
  { key: 'douyin', label: '抖音', icon: '🎵', type: 'danger' as const },
  { key: 'kuaishou', label: '快手', icon: '📹', type: 'primary' as const },
  { key: 'xiaohongshu', label: '小红书', icon: '📕', type: 'warning' as const },
  { key: 'shipinhao', label: '视频号', icon: '💚', type: 'success' as const },
]

const props = defineProps<{
  visible: boolean
  platform: string
  videoUrl: string
  videoPath?: string  // 服务端视频文件路径
  initialTitle: string
  initialText: string
  initialTopics: string
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  'publish-success': [sessionId: string]
}>()

const selectedPlatform = ref('douyin')
const currentPlatform = computed(() => publishPlatforms.find(p => p.key === selectedPlatform.value))

const platformLabel = computed(() => {
  const map: Record<string, string> = {
    douyin: '抖音',
    kuaishou: '快手',
    xiaohongshu: '小红书',
    shipinhao: '视频号',
  }
  return map[selectedPlatform.value] || selectedPlatform.value
})

const publishTitle = ref('')
const publishText = ref('')
const publishTopics = ref('')

// 封面 - 自动截取视频第一帧
const frameSrc = ref<string>('')

const aiLoading = ref(false)
const publishing = ref(false)
const publishStatus = ref('')
const publishSuccess = ref(false)

// ====== 发布进度相关 ======
const publishMode = ref<'edit' | 'progress'>('edit')
const publishProgress = ref(0)
const stepIndex = ref(0)
const progressMessage = ref('')
const errorMessage = ref('')
const platformUrl = ref('')
const sessionId = ref('')
const stepMessage = ref('')
let ws: WebSocket | null = null

const publishSteps = ref([
  { key: 'launching', label: '打开平台' },
  { key: 'logging_in', label: '登录检测' },
  { key: 'uploading', label: '上传视频' },
  { key: 'filling', label: '填写信息' },
  { key: 'cover', label: '设置封面' },
  { key: 'publishing', label: '发布确认' },
])

const stepOrder = ['launching', 'logging_in', 'uploading', 'filling', 'cover', 'publishing', 'complete']

// ====== 二维码登录相关 ======
const showQRCode = ref(false)
const qrImageData = ref('')
const qrTip = ref('')
const qrRefreshing = ref(false)

// ====== 登录检测（编辑模式内覆盖层） ======
const loginCheckActive = ref(false)  // 是否显示登录覆盖层
const loginStatus = ref<'idle' | 'checking' | 'need_qr' | 'success' | 'failed'>('idle')

async function refreshQRCode() {
  if (!sessionId.value || qrRefreshing.value) return
  qrRefreshing.value = true
  try {
    // 发送刷新二维码请求到后端
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ action: 'refresh_qrcode', session_id: sessionId.value }))
    }
    qrTip.value = '正在刷新二维码...'
  } catch {
    qrTip.value = '刷新失败，请稍后重试'
  } finally {
    setTimeout(() => { qrRefreshing.value = false }, 2000)
  }
}

// ====== 已绑定账号 ======
const boundAccounts = ref<AccountInfo[]>([])

// 对话框关闭时清理
watch(() => props.visible, (val) => {
  if (val) {
    selectedPlatform.value = props.platform || 'douyin'
    publishTitle.value = props.initialTitle
    publishText.value = props.initialText
    publishTopics.value = props.initialTopics
    frameSrc.value = ''
    publishing.value = false
    publishStatus.value = ''
    publishSuccess.value = false
    publishMode.value = 'edit'
    publishProgress.value = 0
    stepIndex.value = 0
    progressMessage.value = ''
    errorMessage.value = ''
    platformUrl.value = ''
    stepMessage.value = ''
    // 重置二维码状态
    showQRCode.value = false
    qrImageData.value = ''
    qrTip.value = ''
    qrRefreshing.value = false

    nextTick(() => captureVideoFrame())
    // 加载已绑定账号
    loadBoundAccounts()
  } else {
    // 关闭对话框时断开WS
    disconnectWS()
  }
})

onUnmounted(() => disconnectWS())

function platformIcon(plat: string): string {
  const map: Record<string, string> = {
    douyin: '🎵',
    kuaishou: '📹',
    xiaohongshu: '📕',
    shipinhao: '💚',
  }
  return map[plat] || '📱'
}

async function loadBoundAccounts() {
  try {
    const res = await listPublishAccounts()
    boundAccounts.value = res.accounts || []
  } catch {
    boundAccounts.value = []
  }
}

async function handleUnbindAccount(accountId: number) {
  try {
    await ElMessageBox.confirm('确定要解绑该平台账号吗？', '确认', { type: 'warning' })
    await deletePublishAccount(accountId)
    ElMessage.success('已解绑')
    boundAccounts.value = boundAccounts.value.filter(a => a.id !== accountId)
  } catch {
    // 取消操作
  }
}

function handleClose(done: () => void) {
  if (publishMode.value === 'progress' && publishStatus.value !== 'success' && publishStatus.value !== 'failed') {
    ElMessageBox.confirm('发布正在进行中，确定要离开吗？', '提示', { type: 'warning' })
      .then(() => { disconnectWS(); done() })
      .catch(() => {})
  } else {
    disconnectWS()
    done()
  }
}

function closeDialog() {
  disconnectWS()
  emit('update:visible', false)
}

function disconnectWS() {
  if (ws) {
    ws.onclose = null
    ws.close()
    ws = null
  }
}

/** 截取视频第一帧作为封面 */
function captureVideoFrame() {
  if (!props.videoUrl) return
  const video = document.createElement('video')
  if (props.videoUrl.startsWith('http')) {
    video.crossOrigin = 'anonymous'
  }
  video.src = props.videoUrl
  video.muted = true
  video.playsInline = true
  video.preload = 'auto'
  video.currentTime = 0.01

  let done = false
  function capture() {
    if (done) return
    done = true
    if (video.readyState < 2) return
    const w = video.videoWidth
    const h = video.videoHeight
    if (!w || !h) return
    const canvas = document.createElement('canvas')
    canvas.width = w
    canvas.height = h
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.drawImage(video, 0, 0, w, h)
    frameSrc.value = canvas.toDataURL('image/jpeg', 0.9)
    video.remove()
    canvas.remove()
  }
  video.oncanplay = capture
  video.onseeked = capture
}

async function handleAIGenerate() {
  const text = publishText.value?.trim()
  if (!text) {
    ElMessage.warning('没有可用的文案，无法生成标题和话题')
    return
  }
  aiLoading.value = true
  try {
    const res = await generatePublishPrepare(text)
    if (res.title) {
      publishTitle.value = res.title
    }
    if (res.topics && res.topics.length > 0) {
      publishTopics.value = res.topics.join(' ')
    }
    ElMessage.success('✅ 标题和话题已自动生成！')
  } catch (e: any) {
    ElMessage.error(`生成失败：${e?.message || '请检查LLM配置'}`)
  } finally {
    aiLoading.value = false
  }
}

/** 处理发布事件 - 对接后端 API */
async function handlePublish() {
  if (!publishTitle.value || !publishText.value) {
    ElMessage.warning('请填写标题和文案')
    return
  }
  publishing.value = true
  publishStatus.value = ''
  publishSuccess.value = false

  try {
    // 解析话题标签（逗号/空格分隔）
    const topicsStr = publishTopics.value.trim()
    const topics = topicsStr
      ? topicsStr.split(/[,，\s]+/).filter(t => t).map(t => t.startsWith('#') ? t : `#${t}`)
      : []

    // 推导视频文件路径: 优先使用 props.videoPath, 其次从 videoUrl 截取
    // Playwright 的 set_input_files() 只接受本地文件系统路径，不支持 HTTP URL
    let finalVideoPath = props.videoPath || ''
    if (!finalVideoPath && props.videoUrl) {
      const url = props.videoUrl
      const API_FILES_PREFIX = '/api/files/'
      if (url.startsWith(API_FILES_PREFIX)) {
        // /api/files/temp/uploads/xxx/xxx.mp4 -> temp/uploads/xxx/xxx.mp4
        finalVideoPath = decodeURIComponent(url.slice(API_FILES_PREFIX.length))
      } else if (url.startsWith('http')) {
        // http://localhost:8000/api/files/temp/uploads/xxx/xxx.mp4
        // 提取路径部分，去掉 /api/files/ 前缀
        try {
          const parsed = new URL(url)
          const pathname = parsed.pathname  // /api/files/temp/uploads/xxx/xxx.mp4
          if (pathname.startsWith(API_FILES_PREFIX)) {
            finalVideoPath = decodeURIComponent(pathname.slice(API_FILES_PREFIX.length))
          } else {
            finalVideoPath = decodeURIComponent(pathname)
          }
        } catch {
          // 如果 URL 解析失败，直接用原始路径（后端也有兜底解析）
          finalVideoPath = url
        }
      }
    }

    // 1. 第一步：先检测登录（停留在编辑模式，显示登录覆盖层）
    loginCheckActive.value = true
    loginStatus.value = 'checking'
    qrImageData.value = ''
    qrTip.value = '正在检测登录状态...'

    // 2. 启动发布任务（后端会在内部检测登录，如果未登录则生成二维码）
    const data: PublishStartRequest = {
      platform: selectedPlatform.value,
      video_path: finalVideoPath,
      title: publishTitle.value,
      text: publishText.value,
      topics: topics,
      portrait_cover: frameSrc.value || undefined,
    }

    const res = await startPublish(data)
    sessionId.value = res.session_id

    // 3. 连接 WebSocket 接收实时状态
    connectWS(res.session_id)

    // 4. 启动轮询作为兜底
    setTimeout(() => pollStatus(res.session_id), 3000)

  } catch (e: any) {
    loginCheckActive.value = false
    loginStatus.value = 'idle'
    publishStatus.value = e?.message || '发布启动失败'
    publishSuccess.value = false
    ElMessage.error(`发布启动失败：${e?.message || ''}`)
  } finally {
    publishing.value = false
  }
}

/** 登录成功后切换到进度模式继续发布 */
function proceedToPublishAfterLogin() {
  loginCheckActive.value = false
  loginStatus.value = 'idle'
  publishMode.value = 'progress'
  publishProgress.value = 10
  stepIndex.value = 0
  progressMessage.value = '登录成功，继续发布中...'
}

function connectWS(sid: string) {
  disconnectWS()
  try {
    ws = createPublishWS(sid)

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        handleWSMessage(msg)
      } catch (e) {
        console.warn('WS message parse error:', e)
      }
    }

    ws.onerror = () => {
      console.warn('Publish WS error')
    }

    ws.onclose = () => {
      // 如果发布还没完成，尝试轮询状态
      if (publishStatus.value !== 'success' && publishStatus.value !== 'failed') {
        pollStatus(sid)
      }
    }
  } catch (e) {
    console.warn('WS connection failed, fallback to polling:', e)
    pollStatus(sid)
  }
}

function handleWSMessage(msg: any) {
  const stepMap: Record<string, number> = {
    launching: 0,
    logging_in: 1,
    uploading: 2,
    filling: 3,
    cover: 4,
    publishing: 5,
    complete: 6,
  }

  if (msg.type === 'progress') {
    // 如果当前在登录检测模式，收到进度事件说明已跳过登录，切换到进度模式
    if (loginCheckActive.value || publishMode.value !== 'progress') {
      loginCheckActive.value = false
      loginStatus.value = 'idle'
      publishMode.value = 'progress'
    }
    publishProgress.value = msg.progress || 0
    progressMessage.value = msg.message || ''
    stepMessage.value = ''
    if (msg.step && stepMap[msg.step] !== undefined) {
      stepIndex.value = stepMap[msg.step]
    }
  } else if (msg.type === 'complete') {
    publishProgress.value = 100
    stepIndex.value = stepOrder.length - 1
    publishStatus.value = 'success'
    publishSuccess.value = true
    platformUrl.value = msg.platform_url || ''
    progressMessage.value = msg.message || '发布成功！'
    ElMessage.success(msg.message || '发布成功！')
  } else if (msg.type === 'error') {
    publishStatus.value = 'failed'
    errorMessage.value = msg.message || '发布失败'
    progressMessage.value = msg.message
    ElMessage.error(msg.message || '发布失败')
  } else if (msg.type === 'qrcode') {
    // 接收到二维码图片——在登录检测覆盖层显示
    showQRCode.value = true
    qrImageData.value = msg.image || ''
    qrTip.value = msg.message || '请使用App扫码登录'
    if (loginCheckActive.value) {
      // 编辑模式覆盖层中显示二维码
      loginStatus.value = 'need_qr'
    } else {
      // 进度模式中显示二维码（兼容旧逻辑）
      progressMessage.value = msg.message || '请扫码登录'
      stepIndex.value = 1
      stepMessage.value = '等待扫码...'
    }
  } else if (msg.type === 'qrcode_waiting') {
    // 更新等待提示
    qrTip.value = msg.message || '等待扫码...'
    stepMessage.value = msg.message
  } else if (msg.type === 'qrcode_expired') {
    // 二维码过期，提示刷新
    qrTip.value = msg.message || '二维码已过期'
    stepMessage.value = '二维码已过期，请刷新'
  } else if (msg.type === 'need_login') {
    // 需要扫码登录 (旧版兼容)
    progressMessage.value = msg.message || '请扫码登录'
    stepIndex.value = 1
    stepMessage.value = '等待扫码...'
  } else if (msg.type === 'login_success') {
    showQRCode.value = false
    qrImageData.value = ''
    stepMessage.value = `已登录：${msg.account_name || ''}`
    ElMessage.success(`✅ ${msg.message || '登录成功'}`)
    if (loginCheckActive.value) {
      // 在编辑模式覆盖层中登录成功，切换到进度模式继续发布
      proceedToPublishAfterLogin()
    }
  } else if (msg.type === 'cancelled') {
    publishStatus.value = 'failed'
    errorMessage.value = '用户取消了发布'
    progressMessage.value = '发布已取消'
  }
}

async function pollStatus(sid: string) {
  try {
    const { getPublishStatus } = await import('../api')
    const interval = setInterval(async () => {
      try {
        const status = await getPublishStatus(sid)
        
        // 如果当前在登录检测模式，收到进度说明已跳过登录，切换到进度模式
        if (loginCheckActive.value || publishMode.value !== 'progress') {
          if (status.current_step && status.current_step !== 'launching') {
            loginCheckActive.value = false
            loginStatus.value = 'idle'
            publishMode.value = 'progress'
          }
        }
        
        if (status.status === 'success') {
          clearInterval(interval)
          publishProgress.value = 100
          stepIndex.value = stepOrder.length - 1
          publishStatus.value = 'success'
          publishSuccess.value = true
          platformUrl.value = status.platform_url || ''
          progressMessage.value = status.message || '发布成功！'
          ElMessage.success('发布成功！')
        } else if (status.status === 'failed') {
          clearInterval(interval)
          publishStatus.value = 'failed'
          errorMessage.value = status.error || '发布失败'
          progressMessage.value = status.message
        } else {
          publishProgress.value = status.progress || 0
          progressMessage.value = status.message || ''
          const stepMap: Record<string, number> = {
            launching: 0, logging_in: 1, uploading: 2,
            filling: 3, cover: 4, publishing: 5, complete: 6,
          }
          if (status.current_step && stepMap[status.current_step] !== undefined) {
            stepIndex.value = stepMap[status.current_step]
          }
        }
      } catch {
        clearInterval(interval)
      }
    }, 2000)
  } catch {}
}

function cancelPublish() {
  if (ws && sessionId.value) {
    ws.send('cancel')
  }
  publishStatus.value = 'failed'
  errorMessage.value = '用户取消了发布'
  progressMessage.value = '发布已取消'
  disconnectWS()
}

function retryPublish() {
  publishMode.value = 'edit'
  publishStatus.value = ''
  publishSuccess.value = false
  publishProgress.value = 0
  stepIndex.value = 0
  errorMessage.value = ''
  platformUrl.value = ''
}
</script>

<style scoped>
.publish-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  height: calc(80vh - 140px);
  min-height: 400px;
  position: relative;
}

.publish-left,
.publish-right {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.publish-left {
  overflow-y: auto;
  overflow-x: hidden;
}

@media (max-width: 768px) {
  .publish-layout {
    grid-template-columns: 1fr;
  }
}

.publish-left,
.publish-right {
  min-width: 0;
  min-height: 0;
}

.publish-section-title {
  font-weight: 700;
  font-size: 14px;
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--line, rgba(255,255,255,0.1));
}

.publish-video-wrap {
  width: 100%;
  background: #000;
  border-radius: 10px;
  overflow: hidden;
  margin-bottom: 12px;
  flex-shrink: 0;
}

.publish-video {
  display: block;
  width: 100%;
  max-height: 30vh;
  object-fit: contain;
}

.publish-video-empty {
  padding: 60px 20px;
  text-align: center;
  color: var(--muted, #888);
}

.publish-platform-select {
  margin-top: 8px;
  flex-shrink: 0;
}

.publish-platform-buttons {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

/* 覆盖el-button默认样式 */
.publish-platform-btn.el-button {
  box-sizing: border-box;
  width: 100%;
  margin: 0 !important;
  font-weight: 700;
  letter-spacing: 1px;
  border: 2px solid transparent;
  padding-inline: 0 !important;
}

.publish-form {
  flex: 1;
  overflow-y: auto;
  padding-right: 4px;
  min-height: 0;
}

.cover-row {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 12px;
}

.cover-item {
  display: grid;
  gap: 6px;
}

.cover-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text, #ccc);
}

.cover-upload-wrap {
  height: 200px;
  aspect-ratio: 3/4;
  border: 2px dashed rgba(255,255,255,0.15);
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255,255,255,0.03);
  transition: border-color 0.2s;
}
.cover-upload-wrap:hover {
  border-color: var(--el-color-primary);
}

.cover-upload-wrap.landscape {
  height: 200px;
  aspect-ratio: 4/3;
}

.cover-preview {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.cover-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.cover-section {
  margin-top: 8px;
  flex-shrink: 0;
}

.publish-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.publish-actions {
  display: flex;
  gap: 10px;
  margin-left: auto;
}

.publish-status {
  flex: 1;
  text-align: left;
}

.title-input-row {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  width: 100%;
}
.title-input-row .el-input {
  flex: 1;
}
.ai-btn {
  flex-shrink: 0;
  min-width: 80px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 2px;
  font-weight: 700;
}

/* ====== 发布进度模式 ====== */
.progress-mode {
  padding: 20px 40px;
  min-height: 400px;
}

.progress-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}

.progress-platform-icon {
  font-size: 48px;
  line-height: 1;
}

.progress-title h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.progress-steps {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 24px;
}

.progress-step {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 8px;
  transition: all 0.3s;
}

.progress-step.is-active {
  background: rgba(64,158,255,0.08);
}

.progress-step.is-error {
  background: rgba(245,108,108,0.08);
}

.progress-step.is-completed {
  opacity: 0.7;
}

.step-icon {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 18px;
}

.step-icon .el-icon {
  font-size: 20px;
}

.step-icon .loading-icon {
  animation: rotating 1.5s linear infinite;
  color: var(--el-color-primary);
}

.step-icon .error-icon {
  color: var(--el-color-danger);
}

.step-number {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: rgba(255,255,255,0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
}

.progress-step.is-completed .step-number {
  background: var(--el-color-success);
  color: #fff;
}

.step-content {
  flex: 1;
}

.step-label {
  font-weight: 600;
  font-size: 14px;
}

.step-desc {
  font-size: 12px;
  color: var(--muted, #888);
  margin-top: 4px;
}

.publish-result {
  margin-top: 8px;
}

.bound-accounts {
  margin-top: 16px;
}

.account-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

  /* ====== 编辑模式登录覆盖层 ====== */
  .login-overlay {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0,0,0,0.75);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 100;
    border-radius: 8px;
  }

  .login-loading {
    text-align: center;
    color: #fff;
  }

  .login-loading p {
    margin-top: 12px;
    font-size: 15px;
  }

  .login-qr-content {
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .login-qr-content .qr-card {
    background: var(--el-bg-color, #1a1a2e);
  }

  .qr-loading {
    text-align: center;
    color: #999;
    padding: 40px 20px;
  }

  .qr-loading p {
    margin-top: 8px;
    font-size: 13px;
  }

  /* ====== 二维码扫码区域 ====== */
  .qr-login-area {
    display: flex;
    justify-content: center;
    margin: 16px 0 24px;
  }

  .qr-card {
    width: 280px;
    padding: 24px;
    border-radius: 12px;
    border: 1px solid var(--line, rgba(255,255,255,0.12));
    background: rgba(255,255,255,0.03);
    text-align: center;
  }

  .qr-title {
    font-size: 15px;
    font-weight: 600;
    margin-bottom: 16px;
  }

  .qr-image-wrap {
    width: 200px;
    height: 200px;
    margin: 0 auto 12px;
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #fff;
    padding: 8px;
  }

  .qr-image {
    width: 100%;
    height: 100%;
    object-fit: contain;
    display: block;
  }

  .qr-tip {
    font-size: 13px;
    color: var(--muted, #888);
    margin-bottom: 12px;
  }

  .qr-actions {
    margin-top: 4px;
  }

  @keyframes rotating {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
