<template>
  <div class="tool-page">
    <div class="page-header">
      <span class="page-icon">🤖</span>
      <div>
        <h3 class="page-title">数字人</h3>
        <p class="page-desc">角色图 + 商品图 + 口播合成</p>
      </div>
    </div>
    <div class="page-layout">
      <div class="page-form">
        <DigitalHumanForm
          :form="digitalForm"
          :tts-workflows="ttsWorkflows"
          :tts-voices="ttsVoices"
          :bgm-list="bgmFiles"
          @upload="handleUpload"
          @select-history="openHistory"
        />
      </div>
      <div class="page-generate">
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">🚀 生成</h3>
            <el-tag :type="running ? 'warning' : 'info'" effect="dark">{{ running ? '生成中' : '就绪' }}</el-tag>
          </div>
        <div class="card-body">
            <!-- ZS币费用预览 - 单次模式 -->
            <div v-if="!running && estimatedSeconds > 0" class="cost-preview">
              <div class="cost-row">
                <span>文案字数</span>
                <span><strong>{{ (digitalForm.goods_text || '').replace(/[。！？；，、：；“”''—…（）【】《》〈〉.!?,;:()\[\]{}<>""''\-/\s]/g, '').length }}</strong> 字</span>
              </div>
              <div class="cost-row">
                <span>预估时长</span>
                <span><strong>{{ estimatedSeconds }}</strong> 秒</span>
              </div>
              <div class="cost-row" style="font-size:11px;color:#888;">
                <span>扣费说明</span>
                <span>按实际视频时长 × 5 ZS币/秒 结算，多退少补</span>
              </div>
              <div v-if="auth.userDiscount.value < 100" class="cost-row" style="color:#22c55e;font-size:12px;">
                <span>会员折扣</span>
                <span><strong>{{ auth.userDiscount.value / 10 }}折</strong>（原价 <s style="color:#888;">{{ estimatedOriginalCost }}</s> ZS币）</span>
              </div>
              <div class="cost-row">
                <span>预估消耗</span>
                <span><strong style="color:#fbbf24;">{{ estimatedCost }}</strong> ZS币（预冻结）</span>
              </div>
              <div class="cost-row">
                <span>当前余额</span>
                <span :style="{ color: auth.zsBalance.value >= estimatedCost ? '#22c55e' : '#ef4444' }">
                  <strong>{{ auth.zsBalance.value }}</strong> ZS币
                  <span v-if="auth.zsBalance.value < estimatedCost" style="margin-left:4px;">⚠️ 不足</span>
                </span>
              </div>
            </div>
            <el-button type="primary" size="large" style="width:100%;height:48px;font-weight:900;" :loading="running" :disabled="!running && estimatedSeconds > 0 && auth.zsBalance.value < estimatedCost" @click="generate">
              {{ running ? '正在生成...' : estimatedSeconds > 0 && auth.zsBalance.value < estimatedCost ? 'ZS币不足，请充值' : '开始生成 - 🤖 数字人' }}
            </el-button>
              <div style="margin:18px 0;">
              <div class="small muted" style="padding:8px 12px;background:rgba(255,255,255,0.04);border-radius:8px;display:flex;justify-content:space-between;align-items:center;">
                <span>{{ statusText }}</span>
                <span v-if="elapsedTime" style="font-weight:600;white-space:nowrap;margin-left:12px;" :style="{ color: running ? 'var(--el-color-warning)' : 'var(--el-color-success)' }">⏱ {{ elapsedTime }}</span>
              </div>
            </div>
            <div v-if="submitted" style="margin:12px 0;padding:12px;background:rgba(64,158,255,0.08);border:1px solid rgba(64,158,255,0.2);border-radius:8px;">
              <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
                <span style="font-size:14px;color:var(--el-color-primary);flex:1;">
                  ✅ 任务已提交，可以关闭网页。可在「任务中心」查看，成功后可以在「历史记录」查看。
                </span>
                <el-button size="small" type="danger" plain @click="cancelAllTasks">一键取消全部</el-button>
              </div>
            </div>

            <!-- 单次模式结果 -->
            <template v-if="result.video_url">
              <video class="result-video" controls :src="result.video_url" />
              <div style="display:flex;gap:8px;margin-top:8px;flex-wrap:wrap;">
                <el-button size="small" plain @click="copyText">📋 复制文案</el-button>
                <el-button size="small" type="primary" plain @click="downloadVideo(result.video_url)">⬇️ 下载视频</el-button>
              </div>
            </template>

            <!-- 网感预览（开启字幕/标题/名片且不在运行/提交状态时显示） -->
            <div v-else-if="(digitalForm.subtitle_enabled || digitalForm.title_overlay_config.enabled || digitalForm.business_card_config.enabled) && !running && !submitted" class="preview-sticky-wrap">
              <div class="preview-sticky-inner">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
                  <span style="font-size:12px;color:var(--el-text-color-secondary);">🎬 实时字幕样式预览</span>
                </div>
                <canvas
                  ref="previewCanvasRef"
                  :width="canvasWidth"
                  :height="canvasHeight"
                  style="width:100%;height:auto;max-height:auto;object-fit:contain;border-radius:8px;border:1px solid rgba(255,255,255,0.12);background:#000;"
                />
                <el-button
                  v-if="digitalForm.subtitle_enabled && digitalForm.goods_text.trim()"
                  type="info"
                  size="small"
                  @click="handleSubtitlePreview"
                  :loading="subtitlePreviewLoading"
                  style="width:100%;"
                >
                  {{ subtitlePreviewLoading ? '生成字幕预览...' : '📺 预览字幕效果' }}
                </el-button>
                <video v-if="subtitlePreviewUrl" :src="subtitlePreviewUrl" controls style="width:100%;height:auto;max-height:auto;object-fit:contain;background:#000;border-radius:8px;margin-top:8px;" />
              </div>
            </div>

            <!-- 空预览占位 -->
            <div v-else class="empty-preview">
              <div><div style="font-size:38px;margin-bottom:10px;">🎞️</div><div>生成结果将在这里预览</div></div>
            </div>
            
          </div>
        </div>
      </div>
    </div>
    <HistoryDialog v-model="historyVisible" :loading="historyLoading" :records="historyRecords" :filter-category="historyFilterCategory" @select="onHistorySelect" @delete="refreshHistory" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { DigitalForm } from '../types'
import { request, filePreviewUrl, getUserUploads, cancelTask } from '../api'
import { useTaskRunner } from '../composables/useTaskRunner'
import { useResources } from '../composables/useResources'
import { getAuth } from '../composables/useAuth'
import DigitalHumanForm from '../components/DigitalHumanForm.vue'
import HistoryDialog from '../components/HistoryDialog.vue'

const { running, progress, statusText, result, submitTask, currentTaskId, submitted, cancelCurrentTask } = useTaskRunner()
const { ttsWorkflows, ttsVoices, bgmFiles, handleUpload: uploadResource, loadT: refreshTaskList } = useResources()

const auth = getAuth()

// ZS币计费：根据文案字数自动计算预估时长（1秒=4字，计入语速因子）
const estimatedSeconds = computed(() => {
  let text = digitalForm.value.goods_text?.trim() || ''
  const speed = digitalForm.value.tts_speed || 1.0
  if (!text && digitalForm.value.mode === 'digital' && digitalForm.value.goods_title?.trim()) {
    // 带货模式：填了标题没填文案 → AI会生成约60字文案
    text = digitalForm.value.goods_title
    // AI生成约60字，取标题字数与60字较大值
    const cleanTitle = text.replace(/[。！？；，、：；“”''—…（）【】《》〈〉.!?,;:()\[\]{}<>""''\-/\s]/g, '')
    return Math.ceil(Math.max(cleanTitle.length, 60) / 4 / speed) || 0
  }
  if (!text) return 0
  // 去掉标点只算有效字数
  const cleanText = text.replace(/[。！？；，、：；“”''—…（）【】《》〈〉.!?,;:()\[\]{}<>""''\-/\s]/g, '')
  return Math.ceil(cleanText.length / 4 / speed) || 0
})
const estimatedCost = computed(() => {
  const baseCost = estimatedSeconds.value * 5
  const discount = auth.userDiscount.value
  if (discount < 100) {
    return Math.max(1, Math.floor(baseCost * discount / 100))
  }
  return baseCost
})
// 原价（无折扣时显示）
const estimatedOriginalCost = computed(() => estimatedSeconds.value * 5)

/**
 * 根据用户角色返回视频合成工作流路径：
 * - 普通用户 → digital_combination.json
 * - VIP/SVIP/Admin → digital_combination_new.json
 */
function getVideoWorkflowPath(): string {
  if (auth.isVip.value || auth.isSvip.value || auth.isAdmin.value) {
    return 'workflows/runninghub/digital_combination_new.json'
  }
  return 'workflows/runninghub/digital_combination.json'
}

const digitalForm = ref<DigitalForm>({
  mode: 'customize',
  character_asset: null, goods_asset: null, goods_title: '', goods_text: '',
  workflow_config: {
    first_workflow_path: 'workflows/runninghub/digital_image.json',
    second_workflow_path: getVideoWorkflowPath(),//根据角色选择视频生成工作流
    third_workflow_path: 'workflows/runninghub/digital_customize.json',//这个是把商品和人物融合在一起，人物拿着商品图片
    api_image_workflow: '', api_video_workflow: '', api_video_params: {},
  },
  tts_inference_mode: 'comfyui', tts_engine: 'edge_tts', tts_voice: 'zh-CN-YunjianNeural',
  tts_speed: 1.2, tts_workflow: 'runninghub/tts_index2.json', ref_audio: '', voxcpm_cfg: 2.0,
  voxcpm_normalize: false, voxcpm_denoise: false,
  voxcpm_control_instruction: '', voxcpm_use_prompt_text: false,
  voxcpm_prompt_text: '担心海关查验会把你的心爱宝贝弄坏。真实情况是，海关比你想象的要专业，但也确实会有痕迹。',
  image_service_mode: 'runninghub', image_api_model: '',
  video_service_mode: 'runninghub', video_api_model: '',
  video_api_params: { duration: 10, resolution: '1280x720', aspect_ratio: '9:16', negative_prompt: '', watermark: false },
  // 字幕配置
  subtitle_enabled: false,
  subtitle_config: {
    enabled: false,
    font_size: 56,
    font_color: '#FFFFFF',
    font_family: 'NotoSansSC-Bold',
    font_weight: 400,
    position_x: 0,
    position_y: -390,
    max_width: 900,
    letter_spacing: 3,
    background_color: '#000000',
    background_opacity: 0,
    background_padding: '15 25',
    background_radius: 20,
    font_border_width: 1,
    font_border_color: '#000000',
  },
  // ===== 网感剪辑相关配置（默认全部开启） =====
  internet_clip_enabled: true,
  title_overlay_config: {
    enabled: false,
    text: '爆款视频标题预览效果',
    font_size: 76,
    font_color: '#FF69B4',
    font_weight: 700,
    position_x: 0,
    position_y: -1600,
    display_mode: 'duration',
    duration_seconds: 2,
  },
  business_card_config: {
    enabled: false,
    title: '创始人 & CEO',
    subtitle: '专注AI视频生成',
    display_mode: 'duration',
    duration_seconds: 2,
  },
  bgm_config: {
    enabled: false,
    selected_bgm: null,
    volume: 15,
    custom_bgm: null,
  },
  pip_mix_config: {
    enabled: false,
    overlay_video: null,
    overlay_image: null,
    position_x: 0,
    position_y: 0,
    width: 320,
    height: 568,
    opacity: 1.0,
  },
})

const elapsedTime = ref('')
let startTime = 0
let timerHandle: ReturnType<typeof setInterval> | null = null

function formatElapsed(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  if (h > 0) return `${h}时${m}分${s}秒`
  if (m > 0) return `${m}分${s}秒`
  return `${s}秒`
}

function startTimer() {
  stopTimer()
  startTime = Date.now()
  elapsedTime.value = '0秒'
  timerHandle = setInterval(() => {
    const elapsed = Math.floor((Date.now() - startTime) / 1000)
    elapsedTime.value = formatElapsed(elapsed)
  }, 1000)
}

function stopTimer() {
  if (timerHandle) {
    clearInterval(timerHandle)
    timerHandle = null
  }
}

// 监听 running 状态：开始生成时启动计时器，结束生成时停止
// 当任务结束（running 从 true → false）时，刷新共享任务列表供 TaskCenterView 同步更新，
// 同时刷新用户信息（包括 ZS 币余额），以便 UserMenu 实时显示最新余额
watch(running, (val, oldVal) => {
  if (val) {
    startTimer()
  } else if (oldVal) {
    // running 从 true → false，说明任务已结束（完成/失败/取消）
    stopTimer()
    refreshTaskList()
    // 任务结束后刷新用户信息（ZS币余额），包括手动取消场景
    auth.fetchMe().catch(() => {})
  } else {
    stopTimer()
  }
})

// 监听 submitted 状态：任务提交成功后（预扣款发生），立即刷新余额
watch(submitted, (val) => {
  if (val) {
    auth.fetchMe().catch(() => {})
  }
})

onUnmounted(() => {
  stopTimer()
})

const historyVisible = ref(false)
const historyLoading = ref(false)
const historyRecords = ref<any[]>([])
const historyFilterCategory = ref<string | undefined>(undefined)

const subtitlePreviewLoading = ref(false)
const subtitlePreviewUrl = ref('')

// === 实时字幕预览 Canvas ===
const previewCanvasRef = ref<HTMLCanvasElement | null>(null)
// Canvas 基础宽度（固定），高度根据上传图片比例动态计算
const CANVAS_BASE_WIDTH = 540
const canvasWidth = ref(CANVAS_BASE_WIDTH)
const canvasHeight = ref(960) // 默认 9:16

/** 根据 bgImage 更新 Canvas 尺寸，使宽高比与图片一致 */
function updateCanvasSizeFromImage() {
  if (bgImage && bgImage.naturalWidth > 0 && bgImage.naturalHeight > 0) {
    const imgW = bgImage.naturalWidth
    const imgH = bgImage.naturalHeight
    canvasWidth.value = CANVAS_BASE_WIDTH
    canvasHeight.value = Math.round(CANVAS_BASE_WIDTH * (imgH / imgW))
  } else {
    // 无图片时使用默认 9:16
    canvasWidth.value = CANVAS_BASE_WIDTH
    canvasHeight.value = Math.round(CANVAS_BASE_WIDTH * (16 / 9))
  }
}

function hexToRgba(hex: string, alpha: number): string {
  const h = hex.replace('#', '')
  const r = parseInt(h.substring(0, 2), 16)
  const g = parseInt(h.substring(2, 4), 16)
  const b = parseInt(h.substring(4, 6), 16)
  return `rgba(${r},${g},${b},${alpha})`
}

// 预加载背景图片（使用任务图片或默认图片）
let bgImage: HTMLImageElement | null = null
/** 记录已加载失败的URL，避免重复加载 */
let failedImageUrls: Set<string> = new Set()

/** 根据 character_asset 或默认图片加载背景 */
function loadBackgroundImage() {
  const assetPath = digitalForm.value.character_asset
  const imgUrl = assetPath ? filePreviewUrl(assetPath) : '/videos/0000010.jpg'
  // URL 没变且图片已加载，说明只是 canvas DOM 被重建（开关切换），直接在新 canvas 上重绘
  if (bgImage && bgImage.dataset.src === imgUrl) {
    renderPreview()
    return
  }
  // 如果该 URL 之前已加载失败，不再重试
  if (failedImageUrls.has(imgUrl)) return
  bgImage = null // 清除旧图片，避免闪烁显示旧图
  const img = new Image()
  img.crossOrigin = 'anonymous'
  img.dataset.src = imgUrl
  img.onload = () => {
    bgImage = img
    // 从失败集合中移除（之前失败现在成功了）
    failedImageUrls.delete(imgUrl)
    updateCanvasSizeFromImage()
    // 使用 nextTick 确保 Vue 已更新 canvas 的 width/height 属性后再渲染，
    // 避免 canvas 属性变更导致画布被清空后无人重新渲染
    nextTick(() => renderPreview())
  }
  img.onerror = () => {
    // 记录失败 URL 到集合中，避免后续重复加载
    failedImageUrls.add(imgUrl)
    console.warn('[SubtitlePreview] 背景图片加载失败:', imgUrl)
    bgImage = null
    // 即使背景加载失败也渲染预览（使用深色背景）
    nextTick(() => renderPreview())
  }
  img.src = imgUrl
}

/**
 * 以 object-fit: contain 方式绘制背景图到 Canvas
 * 保持图片原始宽高比，居中显示，不足部分填充黑色
 */
function drawBackgroundContain(ctx: CanvasRenderingContext2D, img: HTMLImageElement, canvasW: number, canvasH: number) {
  const imgRatio = img.naturalWidth / img.naturalHeight
  const canvasRatio = canvasW / canvasH
  let drawW: number, drawH: number, drawX: number, drawY: number
  if (imgRatio > canvasRatio) {
    // 图片更宽 → 适配画布宽度，上下留黑边
    drawW = canvasW
    drawH = canvasW / imgRatio
    drawX = 0
    drawY = (canvasH - drawH) / 2
  } else {
    // 图片更高 → 适配画布高度，左右留黑边
    drawH = canvasH
    drawW = canvasH * imgRatio
    drawX = (canvasW - drawW) / 2
    drawY = 0
  }
  ctx.drawImage(img, drawX, drawY, drawW, drawH)
}

function renderPreview() {
  const canvas = previewCanvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const cw = canvasWidth.value
  const ch = canvasHeight.value
  const scale = Math.min(cw / 1080, ch / 1920)

  ctx.clearRect(0, 0, cw, ch)

  // 绘制视频帧作为背景（如果有）
  if (bgImage) {
    drawBackgroundContain(ctx, bgImage, cw, ch)
  } else {
    ctx.fillStyle = '#1a1a2e'
    ctx.fillRect(0, 0, cw, ch)
    loadBackgroundImage()
  }

  const c = ctx as CanvasRenderingContext2D

  // ============ 1. 绘制字幕 ============
  if (digitalForm.value.subtitle_enabled) {
    const cfg = digitalForm.value.subtitle_config
    if (cfg) {
      let rawText = digitalForm.value.goods_text?.trim() || '这是一个字幕样式预览'
      if (rawText.length > 3) {
        const sentences = rawText.split(/(?<=[。！？；，、，.!?;\s])/)
        rawText = sentences[0] || rawText
      }
      const text = rawText.replace(/[。！？；，、：；“”''—…（）【】《》〈〉.!?,;:()\[\]{}<>""''\-]/g, '')

      const fontSize = Math.round(cfg.font_size * scale)
      const maxWidth = Math.round(cfg.max_width * scale)
      const offsetX = Math.round(cfg.position_x * scale)
      const offsetY = Math.round(cfg.position_y * scale)
      const radius = Math.round(cfg.background_radius * scale)

      const padParts = (cfg.background_padding || '10 20').split(' ').map(Number)
      let padT = 10, padR = 20, padB = 10, padL = 20
      if (padParts.length === 1) { padT = padR = padB = padL = padParts[0] }
      else if (padParts.length === 2) { padT = padB = padParts[0]; padR = padL = padParts[1] }
      else if (padParts.length === 4) { padT = padParts[0]; padR = padParts[1]; padB = padParts[2]; padL = padParts[3] }
      padT = Math.round(padT * scale); padR = Math.round(padR * scale)
      padB = Math.round(padB * scale); padL = Math.round(padL * scale)

      c.font = `${cfg.font_weight || 600} ${fontSize}px "PingFang SC", "Microsoft YaHei", sans-serif`
      c.textBaseline = 'middle'

      const letterSpacing = Math.round((cfg.letter_spacing || 0) * scale)

      function getLineWidth(txt: string): number {
        if (!txt) return 0
        if (letterSpacing > 0 && txt.length > 1) {
          return c.measureText(txt).width + letterSpacing * (txt.length - 1)
        }
        return c.measureText(txt).width
      }

      const lines: string[] = []
      let currentLine = ''
      for (const char of text) {
        const test = currentLine + char
        if (getLineWidth(test) > maxWidth && currentLine) {
          lines.push(currentLine)
          currentLine = char
        } else {
          currentLine = test
        }
      }
      if (currentLine) lines.push(currentLine)

      const metrics = c.measureText('中')
      const approximateAscent = metrics.actualBoundingBoxAscent || fontSize * 0.8
      const approximateDescent = metrics.actualBoundingBoxDescent || fontSize * 0.2
      const lineHeight = approximateAscent + approximateDescent

      const maxLineWidth = Math.max(...lines.map(l => getLineWidth(l)))
      const bgWidth = maxLineWidth + padL + padR
      const bgHeight = lines.length * lineHeight + padT + padB

      const baseX = cw / 2 + offsetX
      const baseY = ch - Math.round(50 * scale) + offsetY
      const bgX = baseX - bgWidth / 2
      const bgY = baseY - bgHeight

      const bgAlpha = Math.max(0, Math.min(1, cfg.background_opacity))
      c.fillStyle = hexToRgba(cfg.background_color, bgAlpha)

      const r = Math.min(radius, bgHeight / 2, bgWidth / 2)
      if (r > 0) {
        c.beginPath()
        c.moveTo(bgX + r, bgY)
        c.lineTo(bgX + bgWidth - r, bgY)
        c.quadraticCurveTo(bgX + bgWidth, bgY, bgX + bgWidth, bgY + r)
        c.lineTo(bgX + bgWidth, bgY + bgHeight - r)
        c.quadraticCurveTo(bgX + bgWidth, bgY + bgHeight, bgX + bgWidth - r, bgY + bgHeight)
        c.lineTo(bgX + r, bgY + bgHeight)
        c.quadraticCurveTo(bgX, bgY + bgHeight, bgX, bgY + bgHeight - r)
        c.lineTo(bgX, bgY + r)
        c.quadraticCurveTo(bgX, bgY, bgX + r, bgY)
        c.closePath()
        c.fill()
      } else {
        c.fillRect(bgX, bgY, bgWidth, bgHeight)
      }

      const borderWidth = Math.round((cfg.font_border_width || 0) * scale)
      const borderColor = cfg.font_border_color || '#000000'

      c.fillStyle = cfg.font_color || '#FFFFFF'
      const yCorrection = (approximateAscent + approximateDescent - fontSize) / 2
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i]
        const y = bgY + (padT + padB) / 2 + lineHeight / 2 + i * lineHeight + yCorrection + 2
        const lineWidth = getLineWidth(line)
        const startX = bgX + (bgWidth - lineWidth) / 2
        if (letterSpacing > 0 && line.length > 1) {
          let currentX = startX
          for (const char of line) {
            if (borderWidth > 0) {
              c.strokeStyle = borderColor
              c.lineWidth = borderWidth
              c.lineJoin = 'round'
              c.miterLimit = 2
              c.strokeText(char, currentX, y)
            }
            c.fillText(char, currentX, y)
            currentX += c.measureText(char).width + letterSpacing
          }
        } else {
          if (borderWidth > 0) {
            c.strokeStyle = borderColor
            c.lineWidth = borderWidth
            c.lineJoin = 'round'
            c.miterLimit = 2
            c.strokeText(line, startX, y)
          }
          c.fillText(line, startX, y)
        }
      }
    }
  }

  // ============ 2. 绘制标题叠加 ============
  if (digitalForm.value.title_overlay_config.enabled) {
    const titleCfg = digitalForm.value.title_overlay_config
    const titleText = titleCfg.text || '爆款推荐'
    if (titleText) {
      const fontSize = Math.round(titleCfg.font_size * scale)
      const offsetX = Math.round(titleCfg.position_x * scale)
      const offsetY = Math.round(titleCfg.position_y * scale)

      c.font = `${titleCfg.font_weight || 700} ${fontSize}px "PingFang SC", "Microsoft YaHei", sans-serif`
      c.textBaseline = 'middle'
      c.textAlign = 'center'

      const metrics = c.measureText(titleText)
      const ascent = metrics.actualBoundingBoxAscent || fontSize * 0.8
      const descent = metrics.actualBoundingBoxDescent || fontSize * 0.2
      const tH = ascent + descent

      const centerX = cw / 2 + offsetX
      const centerY = offsetY < 0 ? ch + offsetY : offsetY
      const y = centerY + (ascent - descent) / 2

      // 描边（黑色边框提升可读性）
      const borderWidth = Math.max(1, Math.round(2 * scale))
      c.strokeStyle = '#000000'
      c.lineWidth = borderWidth
      c.lineJoin = 'round'
      c.miterLimit = 2
      c.strokeText(titleText, centerX, y)

      c.fillStyle = titleCfg.font_color || '#FFFFFF'
      c.fillText(titleText, centerX, y)
    }
  }

  // ============ 3. 绘制个人名片（左侧中间靠下位置） ============
  if (digitalForm.value.business_card_config.enabled) {
    const cardCfg = digitalForm.value.business_card_config
    const cardTitle = cardCfg.title || '创始人 & CEO'
    const cardSubtitle = cardCfg.subtitle || ''

    const cardW = Math.round(380 * scale)
    const cardH = Math.round(cardSubtitle ? 160 * scale : 100 * scale)
    // 左侧中间靠下位置：左边距 20px，Y 在画布约 65% 处
    const cardX = Math.round(20 * scale)
    const cardY = Math.round(ch * 0.65) - Math.round(cardH / 2)

    // 半透明背景
    c.fillStyle = 'rgba(0, 0, 0, 0.7)'
    const cardRadius = Math.round(16 * scale)
    c.beginPath()
    c.moveTo(cardX + cardRadius, cardY)
    c.lineTo(cardX + cardW - cardRadius, cardY)
    c.quadraticCurveTo(cardX + cardW, cardY, cardX + cardW, cardY + cardRadius)
    c.lineTo(cardX + cardW, cardY + cardH - cardRadius)
    c.quadraticCurveTo(cardX + cardW, cardY + cardH, cardX + cardW - cardRadius, cardY + cardH)
    c.lineTo(cardX + cardRadius, cardY + cardH)
    c.quadraticCurveTo(cardX, cardY + cardH, cardX, cardY + cardH - cardRadius)
    c.lineTo(cardX, cardY + cardRadius)
    c.quadraticCurveTo(cardX, cardY, cardX + cardRadius, cardY)
    c.closePath()
    c.fill()

    // 头像占位符
    const avatarSize = Math.round(70 * scale)
    const avatarX = cardX + Math.round(20 * scale)
    const avatarY = cardY + (cardH - avatarSize) / 2
    c.fillStyle = '#409EFF'
    c.beginPath()
    c.arc(avatarX + avatarSize / 2, avatarY + avatarSize / 2, avatarSize / 2, 0, Math.PI * 2)
    c.fill()
    c.fillStyle = '#FFFFFF'
    c.font = `${Math.round(30 * scale)}px sans-serif`
    c.textAlign = 'center'
    c.textBaseline = 'middle'
    c.fillText('👤', avatarX + avatarSize / 2, avatarY + avatarSize / 2)

    // 头衔文字
    const textX = avatarX + avatarSize + Math.round(16 * scale)
    const titleFontSize = Math.round(24 * scale)
    c.font = `600 ${titleFontSize}px "PingFang SC", "Microsoft YaHei", sans-serif`
    c.textAlign = 'left'
    c.textBaseline = 'middle'
    c.fillStyle = '#FFFFFF'
    c.fillText(cardTitle, textX, cardY + (cardSubtitle ? cardH * 0.32 : cardH / 2))

    // 辅语
    if (cardSubtitle) {
      const subFontSize = Math.round(18 * scale)
      c.font = `400 ${subFontSize}px "PingFang SC", "Microsoft YaHei", sans-serif`
      c.fillStyle = 'rgba(255,255,255,0.8)'
      c.fillText(cardSubtitle, textX, cardY + cardH * 0.68)
    }
  }
}

// 监听角色图片切换：实时更新 Canvas 背景
watch(
  () => digitalForm.value.character_asset,
  () => {
    const hasPreview = digitalForm.value.subtitle_enabled || digitalForm.value.title_overlay_config.enabled || digitalForm.value.business_card_config.enabled
    if (hasPreview && previewCanvasRef.value) {
      loadBackgroundImage()
    }
  }
)

// 监听网感开关变化，确保开启时加载背景
watch(
  () => digitalForm.value.internet_clip_enabled,
  (enabled) => {
    if (enabled && previewCanvasRef.value) {
      loadBackgroundImage()
    }
  }
)

// 取消生成任务后重新渲染 Canvas
watch(
  () => ({ running: running.value, submitted: submitted.value }),
  (newVal, oldVal) => {
    // 从生成中/已提交状态恢复到空闲状态时，重新渲染 Canvas
    const wasBusy = oldVal.running || oldVal.submitted
    const isIdle = !newVal.running && !newVal.submitted
    const hasPreview = digitalForm.value.subtitle_enabled || digitalForm.value.title_overlay_config.enabled || digitalForm.value.business_card_config.enabled
    if (wasBusy && isIdle && hasPreview && previewCanvasRef.value) {
      nextTick(() => renderPreview())
    }
  },
  { immediate: false }
)

  // 监听字幕/标题/名片开关及参数变化：实时更新预览
  watch(
    () => ({
      // 字幕
      subtitle_enabled: digitalForm.value.subtitle_enabled,
      fz: digitalForm.value.subtitle_config.font_size,
      fc: digitalForm.value.subtitle_config.font_color,
      fw: digitalForm.value.subtitle_config.font_weight,
      px: digitalForm.value.subtitle_config.position_x,
      py: digitalForm.value.subtitle_config.position_y,
      mw: digitalForm.value.subtitle_config.max_width,
      ls: digitalForm.value.subtitle_config.letter_spacing,
      bc: digitalForm.value.subtitle_config.background_color,
      bo: digitalForm.value.subtitle_config.background_opacity,
      bp: digitalForm.value.subtitle_config.background_padding,
      br: digitalForm.value.subtitle_config.background_radius,
      bw: digitalForm.value.subtitle_config.font_border_width,
      bclr: digitalForm.value.subtitle_config.font_border_color,
      // 标题
      title_enabled: digitalForm.value.title_overlay_config.enabled,
      title_text: digitalForm.value.title_overlay_config.text,
      title_fontSize: digitalForm.value.title_overlay_config.font_size,
      title_fontColor: digitalForm.value.title_overlay_config.font_color,
      title_fontWeight: digitalForm.value.title_overlay_config.font_weight,
      title_px: digitalForm.value.title_overlay_config.position_x,
      title_py: digitalForm.value.title_overlay_config.position_y,
      // 名片
      card_enabled: digitalForm.value.business_card_config.enabled,
      card_title: digitalForm.value.business_card_config.title,
      card_subtitle: digitalForm.value.business_card_config.subtitle,
    }),
    () => {
      const hasPreview = digitalForm.value.subtitle_enabled || digitalForm.value.title_overlay_config.enabled || digitalForm.value.business_card_config.enabled
      if (hasPreview) {
        // 确保 canvas 存在且加载背景图
        nextTick(() => {
          if (previewCanvasRef.value) {
            loadBackgroundImage()
          }
        })
      }
    },
    { deep: true, immediate: true }
  )

async function handleSubtitlePreview() {
  const text = digitalForm.value.goods_text?.trim()
  if (!text) {
    ElMessage.warning('请填写口播文案')
    return
  }
  subtitlePreviewLoading.value = true
  subtitlePreviewUrl.value = ''
  try {
    // 根据上传的图片实际宽高比，自适应 video_width/video_height
    let videoWidth = 1080
    let videoHeight = 1920
    if (bgImage && bgImage.naturalWidth > 0 && bgImage.naturalHeight > 0) {
      const imgW = bgImage.naturalWidth
      const imgH = bgImage.naturalHeight
      // 保持短边至少 1080px，长边按比例等比放大
      if (imgW >= imgH) {
        // 横图或方图：以高度为基准 1920px
        videoHeight = 1920
        videoWidth = Math.round(1920 * (imgW / imgH))
      } else {
        // 竖图：以宽度为基准 1080px
        videoWidth = 1080
        videoHeight = Math.round(1080 * (imgH / imgW))
      }
    }
    // 粗略估算音频时长：中文约 4 字/秒，取平均值
    const estimatedDuration = Math.max(text.length / 4, 3)
    const payload = {
      text,
      audio_duration: estimatedDuration,
      video_width: videoWidth,
      video_height: videoHeight,
       subtitle_config: {
         enabled: true,
         font_size: digitalForm.value.subtitle_config.font_size,
         font_color: digitalForm.value.subtitle_config.font_color,
         font_family: digitalForm.value.subtitle_config.font_family,
         font_weight: digitalForm.value.subtitle_config.font_weight,
         position_x: digitalForm.value.subtitle_config.position_x,
         position_y: digitalForm.value.subtitle_config.position_y,
         max_width: digitalForm.value.subtitle_config.max_width,
         letter_spacing: digitalForm.value.subtitle_config.letter_spacing,
         background_color: digitalForm.value.subtitle_config.background_color,
         background_opacity: digitalForm.value.subtitle_config.background_opacity,
         background_padding: digitalForm.value.subtitle_config.background_padding,
         background_radius: digitalForm.value.subtitle_config.background_radius,
         font_border_width: digitalForm.value.subtitle_config.font_border_width,
         font_border_color: digitalForm.value.subtitle_config.font_border_color,
       },
       // 标题叠加配置
       title_overlay_config: {
         enabled: digitalForm.value.title_overlay_config.enabled,
         text: digitalForm.value.title_overlay_config.text,
         font_size: digitalForm.value.title_overlay_config.font_size,
         font_color: digitalForm.value.title_overlay_config.font_color,
         font_weight: digitalForm.value.title_overlay_config.font_weight,
         position_x: digitalForm.value.title_overlay_config.position_x,
         position_y: digitalForm.value.title_overlay_config.position_y,
         display_mode: digitalForm.value.title_overlay_config.display_mode,
         duration_seconds: digitalForm.value.title_overlay_config.duration_seconds,
       },
       // 个人名片配置
       business_card_config: {
         enabled: digitalForm.value.business_card_config.enabled,
         title: digitalForm.value.business_card_config.title,
         subtitle: digitalForm.value.business_card_config.subtitle,
         display_mode: digitalForm.value.business_card_config.display_mode,
         duration_seconds: digitalForm.value.business_card_config.duration_seconds,
       },
       // BGM 配置
       bgm_config: {
         enabled: digitalForm.value.bgm_config.enabled,
         selected_bgm: digitalForm.value.bgm_config.selected_bgm,
         volume: digitalForm.value.bgm_config.volume,
         custom_bgm: digitalForm.value.bgm_config.custom_bgm,
       },
    }
    const res: any = await request('/api/pipelines/digital-human/subtitle-preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (res.success && res.preview_video_url) {
      subtitlePreviewUrl.value = res.preview_video_url
      ElMessage.success('字幕预览生成成功')
    } else {
      ElMessage.warning(res.message || '字幕预览生成失败')
    }
  } catch (e: any) {
    ElMessage.error(`字幕预览失败：${e.message}`)
  } finally {
    subtitlePreviewLoading.value = false
  }
}

const currentAssets = computed<string[]>(() => {
  return [digitalForm.value.character_asset, digitalForm.value.goods_asset, digitalForm.value.ref_audio].filter((x): x is string => !!x)
})


async function handleUpload(rawFile: File, category: string, target?: string) {
  const result = await uploadResource(rawFile, category, target)
  if (result) {
    if (target === 'digital_character') digitalForm.value.character_asset = result.path
    else if (target === 'digital_goods') digitalForm.value.goods_asset = result.path
    else if (target === 'digital_ref_audio') digitalForm.value.ref_audio = result.path
    else if (category === 'ref_audio') digitalForm.value.ref_audio = result.path
  }
}

async function refreshHistory() {
  try {
    const res = await getUserUploads(historyFilterCategory.value || '')
    historyRecords.value = res.records || []
  } catch (_) {
    historyRecords.value = []
  }
}

async function openHistory(category: string) {
  historyFilterCategory.value = category
  await refreshHistory()
  historyVisible.value = true
}

function onHistorySelect(record: any) {
  const cat = historyFilterCategory.value || record.category || 'misc'
  if (cat === 'ref_audio') digitalForm.value.ref_audio = record.path
  else if (cat === 'character_image') digitalForm.value.character_asset = record.path
  else if (cat === 'goods_image') digitalForm.value.goods_asset = record.path
  historyVisible.value = false
  historyFilterCategory.value = undefined
  ElMessage.success(`已选择：${record.name}`)
}

function buildPayload(): Record<string, any> {
  const payload: Record<string, any> = {}
  payload.character_assets = digitalForm.value.character_asset ? [digitalForm.value.character_asset] : []
  payload.goods_assets = digitalForm.value.goods_asset ? [digitalForm.value.goods_asset] : []
  payload.mode = digitalForm.value.mode
  payload.goods_title = digitalForm.value.goods_title
  payload.goods_text = digitalForm.value.goods_text
  payload.estimated_seconds = estimatedSeconds.value
  payload.workflow_config = { ...digitalForm.value.workflow_config }
  // 根据用户角色动态设置视频合成工作流路径
  payload.workflow_config.second_workflow_path = getVideoWorkflowPath()
  payload.tts_inference_mode = digitalForm.value.tts_inference_mode
  payload.tts_engine = digitalForm.value.tts_engine
  payload.tts_voice = digitalForm.value.tts_voice
  payload.tts_speed = digitalForm.value.tts_speed
  payload.tts_workflow = digitalForm.value.tts_workflow
  payload.ref_audio = digitalForm.value.ref_audio
  payload.voxcpm_cfg = digitalForm.value.voxcpm_cfg
  payload.voxcpm_normalize = digitalForm.value.voxcpm_normalize
  payload.voxcpm_denoise = digitalForm.value.voxcpm_denoise
  payload.voxcpm_control_instruction = digitalForm.value.voxcpm_control_instruction
  payload.voxcpm_use_prompt_text = digitalForm.value.voxcpm_use_prompt_text
  payload.voxcpm_prompt_text = digitalForm.value.voxcpm_prompt_text
  payload.image_service_mode = digitalForm.value.image_service_mode
  payload.image_api_model = digitalForm.value.image_api_model
  payload.video_service_mode = digitalForm.value.video_service_mode
  payload.video_api_model = digitalForm.value.video_api_model
  payload.video_api_params = { ...digitalForm.value.video_api_params }

  if (digitalForm.value.image_service_mode === 'api' && digitalForm.value.image_api_model) {
    payload.workflow_config.api_image_workflow = digitalForm.value.image_api_model
  }
  if (digitalForm.value.video_service_mode === 'api' && digitalForm.value.video_api_model) {
    payload.workflow_config.api_video_workflow = digitalForm.value.video_api_model
  }

  // ===== 字幕配置 =====
   payload.subtitle_config = {
     enabled: digitalForm.value.subtitle_enabled,
     font_size: digitalForm.value.subtitle_config.font_size,
     font_color: digitalForm.value.subtitle_config.font_color,
     font_family: digitalForm.value.subtitle_config.font_family,
     font_weight: digitalForm.value.subtitle_config.font_weight,
     position_x: digitalForm.value.subtitle_config.position_x,
     position_y: digitalForm.value.subtitle_config.position_y,
     max_width: digitalForm.value.subtitle_config.max_width,
     letter_spacing: digitalForm.value.subtitle_config.letter_spacing,
     background_color: digitalForm.value.subtitle_config.background_color,
     background_opacity: digitalForm.value.subtitle_config.background_opacity,
     background_padding: digitalForm.value.subtitle_config.background_padding,
     background_radius: digitalForm.value.subtitle_config.background_radius,
     font_border_width: digitalForm.value.subtitle_config.font_border_width,
     font_border_color: digitalForm.value.subtitle_config.font_border_color,
   }

  // ===== 标题叠加配置 =====
   payload.title_overlay_config = {
     enabled: digitalForm.value.title_overlay_config.enabled,
     text: digitalForm.value.title_overlay_config.text,
     font_size: digitalForm.value.title_overlay_config.font_size,
     font_color: digitalForm.value.title_overlay_config.font_color,
     font_weight: digitalForm.value.title_overlay_config.font_weight,
     position_x: digitalForm.value.title_overlay_config.position_x,
     position_y: digitalForm.value.title_overlay_config.position_y,
     display_mode: digitalForm.value.title_overlay_config.display_mode,
     duration_seconds: digitalForm.value.title_overlay_config.duration_seconds,
   }

  // ===== 个人名片配置 =====
   payload.business_card_config = {
     enabled: digitalForm.value.business_card_config.enabled,
     title: digitalForm.value.business_card_config.title,
     subtitle: digitalForm.value.business_card_config.subtitle,
     display_mode: digitalForm.value.business_card_config.display_mode,
     duration_seconds: digitalForm.value.business_card_config.duration_seconds,
   }

  // ===== BGM 配置 =====
   payload.bgm_config = {
     enabled: digitalForm.value.bgm_config.enabled,
     selected_bgm: digitalForm.value.bgm_config.selected_bgm,
     volume: digitalForm.value.bgm_config.volume,
     custom_bgm: digitalForm.value.bgm_config.custom_bgm,
   }

  // 🔍 调试：打印 payload 中字幕配置，便于在浏览器 Console 排查
  // eslint-disable-next-line no-console
  console.log('[DigitalHuman] 提交 payload 字幕配置:', {
    subtitle_enabled_switch: digitalForm.value.subtitle_enabled,
    payload_subtitle_config: payload.subtitle_config,
  })

  return payload
}


async function generate() {
  // ZS币余额校验
  if (estimatedSeconds.value > 0 && auth.zsBalance.value < estimatedCost.value) {
    ElMessage.warning(`ZS币不足（当前 ${auth.zsBalance.value}，需要 ${estimatedCost.value}），请先充值`)
    return
  }

  // 克隆声音模式必须上传参考音频
  if (digitalForm.value.tts_inference_mode === 'comfyui' && !digitalForm.value.ref_audio) {
    ElMessage.warning('克隆声音模式，请上传参考音频'); return
  }

  if (!digitalForm.value.character_asset) { ElMessage.warning('请上传角色图片'); return }

  if (digitalForm.value.mode === 'digital' && !digitalForm.value.goods_asset) { ElMessage.warning('请上传商品图片'); return }

  const payload = buildPayload()
  payload.mode = digitalForm.value.mode
  payload.goods_text = digitalForm.value.goods_text
  payload.goods_title = digitalForm.value.goods_title

  try {
    const auth = getAuth()
    const usage = await auth.fetchUsage()
    if (!usage.is_unlimited && usage.remaining <= 0) {
      ElMessage.warning('今日生成次数已用完，请明天再试或升级会员')
      return
    }
  } catch (e: any) {
    console.warn('查询每日使用量失败，跳过前端预检', e)
  }

  await submitTask('/api/pipelines/digital-human/async', payload)
}

async function cancelAllTasks() {
  if (currentTaskId.value) {
    await cancelCurrentTask()
  }
}

/** 一键复制文案 */
function copyText() {
  const text = digitalForm.value.goods_text?.trim()
  if (!text) {
    ElMessage.warning('没有可复制的文案')
    return
  }
  navigator.clipboard.writeText(text).then(() => {
    ElMessage.success('文案已复制到剪贴板')
  }).catch(() => {
    ElMessage.error('复制失败，请手动复制')
  })
}

/** 一键下载视频 */
function downloadVideo(url: string) {
  if (!url) {
    ElMessage.warning('没有可下载的视频')
    return
  }
  // 从 URL 中提取文件名，或使用默认名称
  const fileName = url.split('/').pop() || `digital_human_${Date.now()}.mp4`
  const link = document.createElement('a')
  link.href = url
  link.download = fileName
  link.target = '_blank'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  ElMessage.success('正在下载视频...')
}
</script>

<style scoped>
.preview-sticky-wrap {
  margin-bottom: 12px;
}
.page-generate {
  position: sticky;
  top: 20px;
  align-self: start;
  z-index: 10;
}

.cost-preview {
  padding: 12px;
  background: rgba(255,255,255,0.04);
  border-radius: 8px;
  margin-bottom: 12px;
  border: 1px solid rgba(255,255,255,0.08);
}

.cost-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  padding: 4px 0;
  color: #ccc;
}

:deep(.el-table) {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: rgba(255,255,255,0.04);
  --el-table-row-hover-bg-color: rgba(255,255,255,0.06);
  --el-table-border-color: rgba(255,255,255,0.08);
  --el-table-text-color: rgba(255,255,255,0.85);
  --el-table-header-text-color: rgba(255,255,255,0.6);
}
:deep(.el-table__body tr.current-row > td) {
  background: transparent;
}
:deep(.el-table__inner-wrapper::before) {
  display: none;
}
:deep(.el-table__header-wrapper tr th) {
  border-bottom: 1px solid rgba(255,255,255,0.08);
}
:deep(.el-table__body tr td) {
  border-bottom: 1px solid rgba(255,255,255,0.04);
}
</style>