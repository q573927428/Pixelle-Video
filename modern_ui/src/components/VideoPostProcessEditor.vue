<template>
  <div class="vppe-root">
    <div class="vppe-layout">
      <!-- 第一列：视频编辑配置 -->
      <div class="vppe-col vppe-col-config">
        <div class="vppe-config-header">
          <span class="vppe-config-title">🎬 视频编辑</span>
        </div>
        <div class="vppe-config-tabs">
          <el-tag v-for="tab in configTabs" :key="tab.key"
            :type="activeTab === tab.key ? 'primary' : 'info'"
            :effect="activeTab === tab.key ? 'dark' : 'plain'"
            @click="activeTab = tab.key" style="cursor:pointer;margin:2px;">
            {{ tab.label }}
          </el-tag>
        </div>
        <div class="vppe-config-body">
          <div v-show="activeTab === 'subtitle'" class="vppe-tab-content">
            <SubtitleConfigurator :enabled="config.subtitle_enabled" :config="config.subtitle_config" :preview-text="taskText"
              @update:enabled="config.subtitle_enabled = $event"
              @update:config="config.subtitle_config = $event" />
          </div>
          <div v-show="activeTab === 'title'" class="vppe-tab-content">
            <TitleOverlayConfigurator :enabled="config.title_overlay_config.enabled" :config="config.title_overlay_config"
              @update:enabled="config.title_overlay_config.enabled = $event"
              @update:config="config.title_overlay_config = $event" />
          </div>
          <div v-show="activeTab === 'card'" class="vppe-tab-content">
            <BusinessCardConfigurator :enabled="config.business_card_config.enabled" :config="config.business_card_config"
              @update:enabled="config.business_card_config.enabled = $event"
              @update:config="config.business_card_config = $event" />
          </div>
          <div v-show="activeTab === 'bgm'" class="vppe-tab-content">
            <BgmConfigurator :enabled="config.bgm_config.enabled" :config="config.bgm_config" :bgm-list="bgmList"
              @update:enabled="config.bgm_config.enabled = $event"
              @update:config="config.bgm_config = $event"
              @upload="handleBgmUpload" @select-history="handleBgmHistory" />
          </div>
          <div v-show="activeTab === 'pip'" class="vppe-tab-content">
            <PipMixConfigurator :enabled="config.pip_mix_config.enabled" :config="config.pip_mix_config"
              @update:enabled="config.pip_mix_config.enabled = $event"
              @update:config="config.pip_mix_config = $event"
              @upload="handlePiPUpload" @select-history="handlePiPHistory" />
          </div>
        </div>
      </div>

      <!-- 第二列：视频 + Canvas 叠加预览 -->
      <div class="vppe-col vppe-col-preview">
        <div class="vppe-preview-header">
          <span class="vppe-preview-title">🎬 实时预览</span>
        </div>
        <div class="vppe-preview-video-wrap">
          <div v-if="taskVideoUrl" class="vppe-overlay-container" ref="overlayContainerRef">
            <video ref="previewVideoRef" :src="taskVideoUrl" controls muted playsinline preload="metadata" class="vppe-overlay-video" @loadedmetadata="onVideoLoaded" />
            <canvas ref="previewCanvasRef" class="vppe-overlay-canvas" :width="canvasWidth" :height="canvasHeight" />
          </div>
          <div v-else class="vppe-preview-video-empty">
            <div><div style="font-size:38px;margin-bottom:10px;">🎞️</div><div>无视频源</div></div>
          </div>
          <div style="display:flex;gap:8px;margin-top:8px;">
            <el-button type="info" size="small" @click="handleSubtitlePreview" :loading="subtitlePreviewLoading" style="width:100%;">
              {{ subtitlePreviewLoading ? '生成字幕预览...' : '📺 生成预览视频' }}
            </el-button>
            <el-button type="primary" size="small" style="width:100%;" @click="handleApplyEffects" :loading="applyLoading" :disabled="!hasAnyEffectEnabled">
              {{ applyLoading ? '应用处理中...' : '🚀 生成编辑后视频' }}
            </el-button>
          </div>
        </div>
        
      </div>

      <!-- 第三列 -->
      <div class="vppe-col vppe-col-result">
        <div class="vppe-result-header"><span class="vppe-result-title">🎞️ 预览结果</span></div>
        <div v-if="taskVideoUrl" class="vppe-apply-section">
          <div class="vppe-applied-video">
            <div class="vppe-overlay-container" style="margin-top:6px;" v-if="appliedVideoUrl">
              <video :src="appliedVideoUrl" controls class="vppe-overlay-video" />
            </div>
            <div class="vppe-overlay-container" style="margin-top:6px;" v-else-if="subtitlePreviewUrl">
              <video :src="subtitlePreviewUrl" controls class="vppe-overlay-video" />
            </div>
            <div v-else class="vppe-preview-video-empty">
              <div><div style="font-size:38px;margin-bottom:10px;">🎞️</div><div>暂未生成预览视频</div></div>
            </div>
            <div style="display:flex;gap:8px;margin-top:8px;" v-if="subtitlePreviewUrl">
              <el-button size="small" type="primary" plain @click="handleDownload(appliedVideoUrl)">⬇️ 下载视频</el-button>
              <el-button size="small" type="success" @click="openPublishDialog" :disabled="!appliedVideoUrl && !taskVideoUrl">📤 发布</el-button>
            </div>
          </div>
        </div>
      </div>

    </div>

    <!-- 发布弹窗 -->
    <PublishVideoDialog
      v-model:visible="publishDialogVisible"
      :platform="publishPlatform"
      :video-url="appliedVideoUrl || taskVideoUrl || ''"
      :initial-title="publishTitle"
      :initial-text="publishTextForPublish"
      :initial-topics="publishTopics"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { request, loadResources } from '../api'
import SubtitleConfigurator from './SubtitleConfigurator.vue'
import TitleOverlayConfigurator from './TitleOverlayConfigurator.vue'
import BusinessCardConfigurator from './BusinessCardConfigurator.vue'
import BgmConfigurator from './BgmConfigurator.vue'
import PipMixConfigurator from './PipMixConfigurator.vue'
import PublishVideoDialog from './PublishVideoDialog.vue'
import type { SubtitleConfig, TitleOverlayConfig, BusinessCardConfig, BgmConfig, PipMixConfig } from '../types'

const props = defineProps<{
  taskVideoUrl?: string
  taskVideoPath?: string
  taskText: string
  taskId: string
}>()

const bgmList = ref<{ name: string; path: string; source: string }[]>([])

// ===== 发布相关状态 =====
const publishTitle = ref('')
const publishTopics = ref('')
const publishDialogVisible = ref(false)
const publishPlatform = ref('douyin')

const publishTextForPublish = computed(() => {
  // 组合文案+话题
  const text = props.taskText || ''
  const topics = publishTopics.value
  if (!topics) return text
  const topicTags = topics.split(/[,，]/).map((t: string) => t.trim()).filter(Boolean).map((t: string) => `#${t}`).join(' ')
  return text + '\n\n' + topicTags
})

function openPublishDialog() {
  publishDialogVisible.value = true
}

async function loadBgmList() {
  try {
    const res = await loadResources()
    bgmList.value = res.bgmFiles
  } catch (_) {
    bgmList.value = []
  }
}

const configTabs = [
  { key: 'subtitle', label: '📝 字幕' },
  { key: 'title', label: '📌 标题' },
  // { key: 'card', label: '👤 个人名片' },
  { key: 'bgm', label: '🎵 背景音乐' },
  // { key: 'pip', label: '🖼️ 画中画' },
]
const activeTab = ref('subtitle')

const config = reactive({
  subtitle_enabled: true,
  subtitle_config: { enabled: true, font_size: 56, font_color: '#FFFFFF', font_family: 'NotoSansSC-Bold', font_weight: 400, position_x: 0, position_y: -390, max_width: 900, letter_spacing: 3, background_color: '#000000', background_opacity: 0, background_padding: '15 25', background_radius: 20, font_border_width: 1, font_border_color: '#000000' } as SubtitleConfig,
  title_overlay_config: { enabled: true, text: '爆款视频标题预览效果', font_size: 76, font_color: '#FF69B4', font_weight: 700, position_x: 0, position_y: -1600, max_width: 900, font_border_width: 2, font_border_color: '#000000', text_align: 'center', display_mode: 'duration', duration_seconds: 2 } as TitleOverlayConfig,
  business_card_config: { enabled: false, title: '创始人 & CEO', subtitle: '专注AI视频生成', display_mode: 'duration', duration_seconds: 2 } as BusinessCardConfig,
  bgm_config: { enabled: true, selected_bgm: null, volume: 15, custom_bgm: null } as BgmConfig,
  pip_mix_config: { enabled: false, overlay_video: null, overlay_image: null, position_x: 0, position_y: 0, width: 320, height: 568, opacity: 1.0 } as PipMixConfig,
})

const hasAnyEffectEnabled = computed(() =>
  config.subtitle_enabled || config.title_overlay_config.enabled || config.business_card_config.enabled
)

// ===== Canvas叠加渲染（视频 + 字幕/标题/名片） =====
const overlayContainerRef = ref<HTMLDivElement | null>(null)
const previewVideoRef = ref<HTMLVideoElement | null>(null)
const previewCanvasRef = ref<HTMLCanvasElement | null>(null)

// 设计基准分辨率
const DESIGN_W = 1080
const DESIGN_H = 1920

// Canvas实际像素尺寸
const canvasWidth = ref(DESIGN_W)
const canvasHeight = ref(DESIGN_H)

// 视频的实际分辨率（通过 loadedmetadata 获取）
let videoNaturalW = DESIGN_W
let videoNaturalH = DESIGN_H

function onVideoLoaded() {
  const video = previewVideoRef.value
  if (video && video.videoWidth > 0 && video.videoHeight > 0) {
    videoNaturalW = video.videoWidth
    videoNaturalH = video.videoHeight
    // 设置Canvas尺寸与视频分辨率一致，避免缩放失真
    canvasWidth.value = videoNaturalW
    canvasHeight.value = videoNaturalH
  }
  nextTick(() => renderOverlay())
}

function hexToRgba(hex: string, alpha: number): string {
  const h = hex.replace('#', '')
  const r = parseInt(h.substring(0, 2), 16)
  const g = parseInt(h.substring(2, 4), 16)
  const b = parseInt(h.substring(4, 6), 16)
  return `rgba(${r},${g},${b},${alpha})`
}

function renderOverlay() {
  const canvas = previewCanvasRef.value
  const video = previewVideoRef.value
  if (!canvas || !video) return

  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const cw = canvasWidth.value   // 视频实际宽度
  const ch = canvasHeight.value  // 视频实际高度

  // 清除画布（透明底色）
  ctx.clearRect(0, 0, cw, ch)

  // 从设计基准到实际视频的缩放比例
  const scaleX = cw / DESIGN_W
  const scaleY = ch / DESIGN_H
  const scale = Math.min(scaleX, scaleY)

  const c = ctx

  // ============ 1. 字幕 ============
  if (config.subtitle_enabled) {
    const cfg = config.subtitle_config
    if (cfg) {
      let rawText = props.taskText?.trim() || '字幕预览'
      if (rawText.length > 3) {
        const sentences = rawText.split(/(?<=[。！？；，、，.!?;\s])/)
        rawText = sentences[0] || rawText
      }
      const text = rawText.replace(/[。！？；，、：；“”''—…（）【】《》〈〉.!?,;:()\[\]{}<>""''\-]/g, '')

      const fontSize = Math.round(cfg.font_size * scale)
      const maxWidth = Math.round(cfg.max_width * scale)
      const offsetX = Math.round(cfg.position_x * scaleX)
      const offsetY = Math.round(cfg.position_y * scaleY)
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
        } else { currentLine = test }
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
        const startX = bgX + (bgWidth - lineWidth) / 2 + 10
        if (letterSpacing > 0 && line.length > 1) {
          let currentX = startX
          for (const char of line) {
            if (borderWidth > 0) { c.strokeStyle = borderColor; c.lineWidth = borderWidth; c.lineJoin = 'round'; c.miterLimit = 2; c.strokeText(char, currentX, y) }
            c.fillText(char, currentX, y)
            currentX += c.measureText(char).width + letterSpacing
          }
        } else {
          if (borderWidth > 0) { c.strokeStyle = borderColor; c.lineWidth = borderWidth; c.lineJoin = 'round'; c.miterLimit = 2; c.strokeText(line, startX, y) }
          c.fillText(line, startX, y)
        }
      }
    }
  }

  // ============ 2. 标题叠加 ============
  if (config.title_overlay_config.enabled) {
    const titleCfg = config.title_overlay_config
    const titleText = titleCfg.text || '爆款推荐'
    if (titleText) {
      const fontSize = Math.round(titleCfg.font_size * scale)
      const offsetX = Math.round(titleCfg.position_x * scaleX)
      const offsetY = Math.round(titleCfg.position_y * scaleY)

      c.font = `${titleCfg.font_weight || 700} ${fontSize}px "PingFang SC", "Microsoft YaHei", sans-serif`
      c.textBaseline = 'middle'
      c.textAlign = 'left'

      const titles = titleText.split('\n').filter((t: string) => t.trim())
      if (titles.length === 0) return

      // 计算每行宽度
      const maxWidth = Math.round((titleCfg.max_width || 900) * scale)
      const letterSpacing = 5 // 标题也增加一点字间距

      function getLineWidth(txt: string): number {
        if (!txt) return 0
        if (letterSpacing > 0 && txt.length > 1) {
          return c.measureText(txt).width + letterSpacing * (txt.length - 1)
        }
        return c.measureText(txt).width
      }

      // 对每行做宽度截断
      const allLines: string[] = []
      for (const line of titles) {
        let currentLine = ''
        for (const char of line) {
          const test = currentLine + char
          if (getLineWidth(test) > maxWidth && currentLine) {
            allLines.push(currentLine)
            currentLine = char
          } else {
            currentLine = test
          }
        }
        if (currentLine) allLines.push(currentLine)
      }

      const metrics = c.measureText('中')
      const ascent = metrics.actualBoundingBoxAscent || fontSize * 0.8
      const descent = metrics.actualBoundingBoxDescent || fontSize * 0.2
      const lineHeight = ascent + descent
      const textHeight = allLines.length * lineHeight

      const centerX = cw / 2 + offsetX
      const centerY = offsetY < 0 ? ch + offsetY : offsetY

      // 计算整体文本宽度
      const maxLineWidth = Math.max(...allLines.map((l: string) => getLineWidth(l)))

      // 计算背景区域（自动计算背景尺寸，半透明黑色背景提升可读性）
      const pad = Math.round(15 * scale)
      const bgWidth = maxLineWidth + pad * 2
      const bgHeight = textHeight + pad * 2
      const bgX = centerX - bgWidth / 2
      const bgY = centerY - bgHeight / 2

      // 绘制半透明背景
      c.fillStyle = 'rgba(0,0,0,0.5)'
      const br = Math.min(Math.round(8 * scale), bgHeight / 2, bgWidth / 2)
      if (br > 0) {
        c.beginPath()
        c.moveTo(bgX + br, bgY)
        c.lineTo(bgX + bgWidth - br, bgY)
        c.quadraticCurveTo(bgX + bgWidth, bgY, bgX + bgWidth, bgY + br)
        c.lineTo(bgX + bgWidth, bgY + bgHeight - br)
        c.quadraticCurveTo(bgX + bgWidth, bgY + bgHeight, bgX + bgWidth - br, bgY + bgHeight)
        c.lineTo(bgX + br, bgY + bgHeight)
        c.quadraticCurveTo(bgX, bgY + bgHeight, bgX, bgY + bgHeight - br)
        c.lineTo(bgX, bgY + br)
        c.quadraticCurveTo(bgX, bgY, bgX + br, bgY)
        c.closePath()
        c.fill()
      } else {
        c.fillRect(bgX, bgY, bgWidth, bgHeight)
      }

      // 逐行绘制文字（支持对齐方式）
      const textAlign = titleCfg.text_align || 'center'
      const borderWidth = Math.round((titleCfg.font_border_width || 2) * scale)
      const borderColor = titleCfg.font_border_color || '#000000'
      c.fillStyle = titleCfg.font_color || '#FFFFFF'
      const yCorrection = (ascent + descent - fontSize) / 2

      for (let i = 0; i < allLines.length; i++) {
        const line = allLines[i]
        const lineWidth = getLineWidth(line)
        let lineX: number
        if (textAlign === 'left') {
          lineX = bgX + pad + 5
        } else if (textAlign === 'right') {
          lineX = bgX + bgWidth - lineWidth - pad - 5
        } else {
          lineX = bgX + (bgWidth - lineWidth) / 2 + 5
        }
        const lineY = bgY + pad + lineHeight / 2 + i * lineHeight + yCorrection

        if (letterSpacing > 0 && line.length > 1) {
          let currentX = lineX
          for (const char of line) {
            if (borderWidth > 0) {
              c.strokeStyle = borderColor
              c.lineWidth = borderWidth
              c.lineJoin = 'round'
              c.miterLimit = 2
              c.strokeText(char, currentX, lineY)
            }
            c.fillText(char, currentX, lineY)
            currentX += c.measureText(char).width + letterSpacing
          }
        } else {
          if (borderWidth > 0) {
            c.strokeStyle = borderColor
            c.lineWidth = borderWidth
            c.lineJoin = 'round'
            c.miterLimit = 2
            c.strokeText(line, lineX, lineY)
          }
          c.fillText(line, lineX, lineY)
        }
      }
    }
  }

  // ============ 3. 个人名片 ============
  if (config.business_card_config.enabled) {
    const cardCfg = config.business_card_config
    const cardTitle = cardCfg.title || '创始人 & CEO'
    const cardSubtitle = cardCfg.subtitle || ''

    const cardW = Math.round(380 * scale)
    const cardH = Math.round(cardSubtitle ? 160 * scale : 100 * scale)
    const cardX = Math.round(20 * scaleX)
    const cardY = Math.round(ch * 0.65) - Math.round(cardH / 2)

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

    const avatarSize = Math.round(70 * scale)
    const avatarX = cardX + Math.round(20 * scale)
    const avatarY = cardY + (cardH - avatarSize) / 2
    c.fillStyle = '#409EFF'
    c.beginPath()
    c.arc(avatarX + avatarSize / 2, avatarY + avatarSize / 2, avatarSize / 2, 0, Math.PI * 2)
    c.fill()
    c.fillStyle = '#FFFFFF'
    c.font = `${Math.round(30 * scale)}px sans-serif`
    c.textAlign = 'center'; c.textBaseline = 'middle'
    c.fillText('👤', avatarX + avatarSize / 2, avatarY + avatarSize / 2)

    const textX = avatarX + avatarSize + Math.round(16 * scale)
    const titleFontSize = Math.round(24 * scale)
    c.font = `600 ${titleFontSize}px "PingFang SC", "Microsoft YaHei", sans-serif`
    c.textAlign = 'left'; c.textBaseline = 'middle'
    c.fillStyle = '#FFFFFF'
    c.fillText(cardTitle, textX, cardY + (cardSubtitle ? cardH * 0.32 : cardH / 2))

    if (cardSubtitle) {
      const subFontSize = Math.round(18 * scale)
      c.font = `400 ${subFontSize}px "PingFang SC", "Microsoft YaHei", sans-serif`
      c.fillStyle = 'rgba(255,255,255,0.8)'
      c.fillText(cardSubtitle, textX, cardY + cardH * 0.68)
    }
  }
}

// 配置变化时重新渲染Canvas
watch(
  () => ({
    subtitle_enabled: config.subtitle_enabled,
    fz: config.subtitle_config.font_size, fc: config.subtitle_config.font_color,
    fw: config.subtitle_config.font_weight, px: config.subtitle_config.position_x,
    py: config.subtitle_config.position_y, mw: config.subtitle_config.max_width,
    ls: config.subtitle_config.letter_spacing, bc: config.subtitle_config.background_color,
    bo: config.subtitle_config.background_opacity, bp: config.subtitle_config.background_padding,
    br: config.subtitle_config.background_radius, bw: config.subtitle_config.font_border_width,
    bclr: config.subtitle_config.font_border_color,
    title_enabled: config.title_overlay_config.enabled,
    title_text: config.title_overlay_config.text,
    title_fontSize: config.title_overlay_config.font_size,
    title_fontColor: config.title_overlay_config.font_color,
    title_fontWeight: config.title_overlay_config.font_weight,
    title_px: config.title_overlay_config.position_x,
    title_py: config.title_overlay_config.position_y,
    card_enabled: config.business_card_config.enabled,
    card_title: config.business_card_config.title,
    card_subtitle: config.business_card_config.subtitle,
  }),
  () => {
    if (config.subtitle_enabled || config.title_overlay_config.enabled || config.business_card_config.enabled) {
      nextTick(() => renderOverlay())
    }
  },
  { deep: true, immediate: true }
)

// 视频播放过程中持续重绘（保持字幕帧与视频同步）
let animFrameId: number | null = null
function startOverlayLoop() {
  stopOverlayLoop()
  const video = previewVideoRef.value
  if (!video) return
  function loop() {
    if (config.subtitle_enabled || config.title_overlay_config.enabled || config.business_card_config.enabled) {
      renderOverlay()
    }
    animFrameId = requestAnimationFrame(loop)
  }
  animFrameId = requestAnimationFrame(loop)
}
function stopOverlayLoop() {
  if (animFrameId !== null) { cancelAnimationFrame(animFrameId); animFrameId = null }
}

onMounted(() => {
  loadBgmList()
  const video = previewVideoRef.value
  if (video) {
    video.addEventListener('play', startOverlayLoop)
    video.addEventListener('pause', () => { if (animFrameId) renderOverlay() })
    video.addEventListener('seeked', () => renderOverlay())
  }
})
onUnmounted(() => {
  stopOverlayLoop()
  const video = previewVideoRef.value
  if (video) {
    video.removeEventListener('play', startOverlayLoop)
    video.removeEventListener('pause', () => {})
    video.removeEventListener('seeked', () => {})
  }
})

// ===== 字幕预览生成 =====
const subtitlePreviewLoading = ref(false)
const subtitlePreviewUrl = ref('')
async function handleSubtitlePreview() {
  const text = props.taskText?.trim()
  if (!text) { ElMessage.warning('该任务没有可用的文案'); return }
  subtitlePreviewLoading.value = true; subtitlePreviewUrl.value = ''
  try {
    const res: any = await request('/api/pipelines/digital-human/subtitle-preview', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text, audio_duration: Math.max(text.length / 4, 3), video_width: 1080, video_height: 1920,
        video_path: props.taskVideoPath || '',
        subtitle_config: { enabled: config.subtitle_enabled, font_size: config.subtitle_config.font_size, font_color: config.subtitle_config.font_color, font_family: config.subtitle_config.font_family, font_weight: config.subtitle_config.font_weight, position_x: config.subtitle_config.position_x, position_y: config.subtitle_config.position_y, max_width: config.subtitle_config.max_width, letter_spacing: config.subtitle_config.letter_spacing, background_color: config.subtitle_config.background_color, background_opacity: config.subtitle_config.background_opacity, background_padding: config.subtitle_config.background_padding, background_radius: config.subtitle_config.background_radius, font_border_width: config.subtitle_config.font_border_width, font_border_color: config.subtitle_config.font_border_color },
        title_overlay_config: { enabled: config.title_overlay_config.enabled, text: config.title_overlay_config.text, font_size: config.title_overlay_config.font_size, font_color: config.title_overlay_config.font_color, font_weight: config.title_overlay_config.font_weight, position_x: config.title_overlay_config.position_x, position_y: config.title_overlay_config.position_y, max_width: config.title_overlay_config.max_width, font_border_width: config.title_overlay_config.font_border_width, font_border_color: config.title_overlay_config.font_border_color, text_align: config.title_overlay_config.text_align, display_mode: config.title_overlay_config.display_mode, duration_seconds: config.title_overlay_config.duration_seconds },
        business_card_config: { enabled: config.business_card_config.enabled, title: config.business_card_config.title, subtitle: config.business_card_config.subtitle, display_mode: config.business_card_config.display_mode, duration_seconds: config.business_card_config.duration_seconds },
        bgm_config: { enabled: config.bgm_config.enabled, selected_bgm: config.bgm_config.selected_bgm, volume: config.bgm_config.volume, custom_bgm: config.bgm_config.custom_bgm },
      }),
    })
    if (res.success && res.preview_video_url) { subtitlePreviewUrl.value = res.preview_video_url; ElMessage.success('预览视频生成成功') }
    else { ElMessage.warning(res.message || '预览视频生成失败') }
  } catch (e: any) { ElMessage.error(`预览失败：${e.message}`) }
  finally { subtitlePreviewLoading.value = false }
}

// ===== 应用到实际视频 =====
const applyLoading = ref(false)
const appliedVideoUrl = ref('')
async function handleApplyEffects() {
  if (!props.taskVideoPath && !props.taskVideoUrl) { ElMessage.warning('没有可用的任务视频'); return }
  if (!props.taskText?.trim()) { ElMessage.warning('任务没有文案，无法生成字幕'); return }
  applyLoading.value = true; appliedVideoUrl.value = ''
  try {
    const res: any = await request('/api/pipelines/digital-human/apply-effects', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        video_path: props.taskVideoPath || props.taskVideoUrl, goods_text: props.taskText,
        subtitle_config: { enabled: config.subtitle_enabled, font_size: config.subtitle_config.font_size, font_color: config.subtitle_config.font_color, font_family: config.subtitle_config.font_family, font_weight: config.subtitle_config.font_weight, position_x: config.subtitle_config.position_x, position_y: config.subtitle_config.position_y, max_width: config.subtitle_config.max_width, letter_spacing: config.subtitle_config.letter_spacing, background_color: config.subtitle_config.background_color, background_opacity: config.subtitle_config.background_opacity, background_padding: config.subtitle_config.background_padding, background_radius: config.subtitle_config.background_radius, font_border_width: config.subtitle_config.font_border_width, font_border_color: config.subtitle_config.font_border_color },
        title_overlay_config: { enabled: config.title_overlay_config.enabled, text: config.title_overlay_config.text, font_size: config.title_overlay_config.font_size, font_color: config.title_overlay_config.font_color, font_weight: config.title_overlay_config.font_weight, position_x: config.title_overlay_config.position_x, position_y: config.title_overlay_config.position_y, max_width: config.title_overlay_config.max_width, font_border_width: config.title_overlay_config.font_border_width, font_border_color: config.title_overlay_config.font_border_color, text_align: config.title_overlay_config.text_align, display_mode: config.title_overlay_config.display_mode, duration_seconds: config.title_overlay_config.duration_seconds },
        business_card_config: { enabled: config.business_card_config.enabled, title: config.business_card_config.title, subtitle: config.business_card_config.subtitle, display_mode: config.business_card_config.display_mode, duration_seconds: config.business_card_config.duration_seconds },
        bgm_config: { enabled: config.bgm_config.enabled, selected_bgm: config.bgm_config.selected_bgm, volume: config.bgm_config.volume, custom_bgm: config.bgm_config.custom_bgm },
      }),
    })
    if (res.success && res.video_url) { appliedVideoUrl.value = res.video_url; ElMessage.success('效果应用成功！') }
    else { ElMessage.warning(res.message || '效果应用失败') }
  } catch (e: any) { ElMessage.error(`处理失败：${e.message}`) }
  finally { applyLoading.value = false }
}

function handleCopyText() {
  const text = props.taskText?.trim()
  if (!text) { ElMessage.warning('没有可复制的文案'); return }
  navigator.clipboard.writeText(text).then(() => ElMessage.success('文案已复制到剪贴板')).catch(() => ElMessage.error('复制失败'))
}
function handleDownload(url: string) {
  if (!url) { ElMessage.warning('没有可下载的视频'); return }
  const a = document.createElement('a'); a.href = url; a.download = url.split('/').pop() || `video_${Date.now()}.mp4`; a.target = '_blank'
  document.body.appendChild(a); a.click(); document.body.removeChild(a)
}
function handleBgmUpload(f: File, c: string, t: string) { ElMessage.info('BGM上传功能请在数字人页面使用') }
function handleBgmHistory(c: string) { ElMessage.info('历史记录功能请在数字人页面使用') }
function handlePiPUpload(f: File, c: string, t: string) { ElMessage.info('画中画上传功能请在数字人页面使用') }
function handlePiPHistory(c: string) { ElMessage.info('历史记录功能请在数字人页面使用') }
</script>

<style scoped>
.vppe-root { width: 100%; }
.vppe-layout { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; min-height: 400px; }
@media (max-width: 1400px) { .vppe-layout { grid-template-columns: 1fr 1fr; } }
@media (max-width: 800px) { .vppe-layout { grid-template-columns: 1fr; } }
.vppe-col { min-width: 0; display: flex; flex-direction: column; }

/* 第一列 */
.vppe-col-config { border: 1px solid var(--line, rgba(255,255,255,0.1)); border-radius: 12px; background: rgba(2, 6, 23, 0.3); overflow: hidden; }
.vppe-config-header { padding: 12px 14px; border-bottom: 1px solid var(--line, rgba(255,255,255,0.1)); background: rgba(15, 23, 42, 0.4); }
.vppe-config-title { font-weight: 700; font-size: 15px; }
.vppe-config-tabs { padding: 10px 12px 6px; display: flex; flex-wrap: wrap; gap: 2px; border-bottom: 1px solid var(--line, rgba(255,255,255,0.06)); }
.vppe-config-body { flex: 1; overflow-y: auto; padding: 12px; max-height: 500px; }
.vppe-tab-content { animation: fadeIn 0.2s ease; }
@keyframes fadeIn { from { opacity: 0.5; } to { opacity: 1; } }

/* 第二列：视频 + Canvas 叠加 */
.vppe-col-preview { border: 1px solid var(--line, rgba(255,255,255,0.1)); border-radius: 12px; background: rgba(2, 6, 23, 0.3); overflow: hidden; }
.vppe-preview-header { padding: 12px 14px; border-bottom: 1px solid var(--line, rgba(255,255,255,0.1)); background: rgba(15, 23, 42, 0.4); }
.vppe-preview-title { font-weight: 700; font-size: 15px; }
.vppe-preview-video-wrap { padding: 12px; flex: 1; }
.vppe-preview-actions { padding: 0 12px 12px; }
.vppe-preview-hint { padding: 8px 12px 12px; text-align: center; }

/* 叠加容器 - 视频 + Canvas 绝对定位叠放 */
.vppe-overlay-container {
  position: relative;
  width: 100%;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
}
.vppe-overlay-video {
  display: block;
  width: 100%;
  height: auto;
  max-height: 65vh;
  object-fit: contain;
}
.vppe-overlay-canvas {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none; /* 让点击穿透到视频控件 */
}

.vppe-preview-video-empty { padding: 60px 12px; text-align: center; color: var(--muted, #888); }

/* 第三列 */
.vppe-col-result { border: 1px solid var(--line, rgba(255,255,255,0.1)); border-radius: 12px; background: rgba(2, 6, 23, 0.3); overflow: hidden; }
.vppe-result-header { padding: 12px 14px; border-bottom: 1px solid var(--line, rgba(255,255,255,0.1)); background: rgba(15, 23, 42, 0.4); }
.vppe-result-title { font-weight: 700; font-size: 15px; }
.vppe-result-video { padding: 12px; position: relative; }
.vppe-result-empty { padding: 40px 12px; text-align: center; color: var(--muted, #888); }
.vppe-apply-section { padding: 0 12px 12px; }
.vppe-apply-header { font-weight: 600; font-size: 14px; margin-bottom: 8px; }
.vppe-applied-video { margin-top: 4px; }

</style>
