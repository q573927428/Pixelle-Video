<template>
  <div class="form-section-wrapper">
    <div class="form-section">
      <div class="form-section-title" style="display:flex;justify-content:space-between;align-items:center;">
        <span>📝 字幕配置</span>
        <div style="display:flex;align-items:center;gap:6px;">
          <span style="font-size:13px;font-weight:400;">开关</span>
          <el-switch
            :model-value="enabled"
            @update:model-value="$emit('update:enabled', $event)"
          />
        </div>
      </div>
      <div class="form-section-body" v-if="enabled">
        <!-- 预制字幕样式 -->
        <div style="margin-bottom:14px;">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
            <span style="font-size:13px;font-weight:500;color:var(--el-color-primary);">🎨 预制字幕样式</span>
            <el-tag size="small" type="info" effect="plain">点击切换</el-tag>
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
            <div
              v-for="preset in presetStyles"
              :key="preset.name"
              @click="applyPreset(preset)"
              style="display:flex;align-items:center;gap:8px;padding:8px 10px;border-radius:6px;border:1px solid var(--el-border-color-light);cursor:pointer;transition:all 0.2s;"
              @mouseenter="(e) => { (e.currentTarget as HTMLElement).style.borderColor = 'var(--el-color-primary)'; (e.currentTarget as HTMLElement).style.background = 'var(--el-fill-color-light)'; }"
              @mouseleave="(e) => { (e.currentTarget as HTMLElement).style.borderColor = 'var(--el-border-color-light)'; (e.currentTarget as HTMLElement).style.background = 'transparent'; }"
            >
              <!-- 风格预览：小画布 -->
              <div style="flex-shrink:0;width:36px;height:24px;border-radius:4px;overflow:hidden;display:flex;align-items:center;justify-content:center;position:relative;background:#1a1a2e;">
                <span style="font-size:10px;font-weight:bold;z-index:1;line-height:1;"
                  :style="{
                    color: preset.preview.fontColor,
                    textShadow: preset.preview.borderWidth > 0 ? `0 0 0 ${preset.preview.borderColor}, 0 0 1px ${preset.preview.borderColor}` : 'none',
                  }"
                >字</span>
                <div v-if="preset.preview.bgAlpha > 0" style="position:absolute;inset:2px 2px;border-radius:2px;pointer-events:none;"
                  :style="{ background: preset.preview.bgColor, opacity: preset.preview.bgAlpha }"
                ></div>
              </div>
              <span style="font-size:12px;font-weight:500;white-space:nowrap;">{{ preset.name }}</span>
            </div>
          </div>
        </div>
        <el-collapse v-model="activeNames">
          <el-collapse-item name="subtitle-basic">
            <template #title>
              <span style="font-size:13px;font-weight:500;color:var(--el-color-primary);">📐 普通设置</span>
            </template>
            <el-form-item label="文字大小">
              <el-slider v-model="localConfig.font_size" :min="22" :max="96" :step="2" show-input />
            </el-form-item>
            <el-form-item label="文字颜色">
              <el-color-picker v-model="localConfig.font_color" show-alpha />
            </el-form-item>
            <el-form-item label="文字间距">
              <el-slider v-model="localConfig.letter_spacing" :min="0" :max="50" :step="1" show-input />
            </el-form-item>
            <el-divider style="margin:8px 0;" />
            <el-form-item label="文字边框粗细">
              <el-slider v-model="localConfig.font_border_width" :min="0" :max="10" :step="1" show-input />
            </el-form-item>
            <el-form-item label="文字边框颜色">
              <el-color-picker v-model="localConfig.font_border_color" show-alpha />
            </el-form-item>
            <el-divider style="margin:8px 0;" />
            <el-form-item label="位置 X">
              <el-slider v-model="localConfig.position_x" :min="-500" :max="500" :step="10" show-input />
            </el-form-item>
            <el-form-item label="位置 Y">
              <el-slider v-model="localConfig.position_y" :min="-1700" :max="100" :step="10" show-input />
            </el-form-item>
          </el-collapse-item>
          <div style="height:15px;"></div>
          <el-collapse-item name="subtitle-advanced">
            <template #title>
              <span style="font-size:13px;font-weight:500;color:var(--el-color-primary);">⚙️ 高级设置</span>
            </template>
            <el-form-item label="最大宽度">
              <el-slider v-model="localConfig.max_width" :min="100" :max="1980" :step="20" show-input />
            </el-form-item>
            <el-divider style="margin:8px 0;" />
            <el-form-item label="背景颜色">
              <el-color-picker v-model="localConfig.background_color" show-alpha />
            </el-form-item>
            <el-form-item label="背景透明度">
              <el-slider v-model="localConfig.background_opacity" :min="0" :max="1.0" :step="0.1" show-input />
            </el-form-item>
            <el-form-item label="背景内边距">
              <el-input v-model="localConfig.background_padding" placeholder="例如：10 20（上下 左右） 或 10 20 10 20（上 右 下 左）" />
              <small>例如：10 20（上下 左右） 或 10 20 10 20（上 右 下 左）</small>
            </el-form-item>
            <el-form-item label="背景圆角">
              <el-input-number v-model="localConfig.background_radius" :min="0" :max="50" :step="2" style="width:100%;" />
            </el-form-item>
          </el-collapse-item>
        </el-collapse>

        <!-- 实时字幕样式预览 Canvas -->
        <div style="margin-top:14px;">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
            <span style="font-size:12px;color:var(--el-text-color-secondary);">🎬 实时字幕样式预览</span>
            <el-tag size="small" type="info" effect="plain">仅用于样式参考</el-tag>
          </div>
          <div style="position:relative;border-radius:8px;overflow:hidden;background:#1a1a2e;">
            <canvas
              ref="previewCanvasRef"
              :width="CANVAS_PREVIEW_WIDTH"
              :height="CANVAS_PREVIEW_HEIGHT"
              style="width:100%;height:auto;display:block;"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, reactive } from 'vue'
import type { SubtitleConfig } from '../types'

const props = defineProps<{
  enabled: boolean
  config: SubtitleConfig
  previewText?: string
}>()

const emit = defineEmits<{
  (e: 'update:enabled', val: boolean): void
  (e: 'update:config', val: SubtitleConfig): void
}>()

// 将 props.config 转为本地响应式副本，深度监听并 emit
const localConfig = reactive<SubtitleConfig>({ ...props.config })

watch(
  () => props.config,
  (val) => {
    if (val) {
      Object.assign(localConfig, val)
    }
  },
  { deep: true }
)

// 深度 watch localConfig 变化，emit 回父组件
watch(
  () => ({ ...localConfig }),
  (val) => {
    emit('update:config', val as SubtitleConfig)
  },
  { deep: true }
)

const activeNames = ref<string[]>([])

// ===== 预制字幕样式 =====
interface PresetPreview {
  fontColor: string
  borderColor: string
  borderWidth: number
  bgColor: string
  bgAlpha: number
}

interface PresetStyle {
  name: string
  config: Partial<SubtitleConfig>
  preview: PresetPreview
}

const presetStyles: PresetStyle[] = [
  {
    name: '经典白字',
    config: {
      font_color: '#FFFFFF',
      font_border_color: '#000000',
      font_border_width: 2,
      background_opacity: 0,
    },
    preview: { fontColor: '#FFFFFF', borderColor: '#000000', borderWidth: 2, bgColor: '#000000', bgAlpha: 0 },
  },
  {
    name: '黑底白字',
    config: {
      font_color: '#FFFFFF',
      background_color: '#000000',
      background_opacity: 0.8,
      background_padding: '10 20',
      background_radius: 15,
      font_border_width: 0,
    },
    preview: { fontColor: '#FFFFFF', borderColor: '#000000', borderWidth: 0, bgColor: '#000000', bgAlpha: 0.8 },
  },
  {
    name: '黄字黑边',
    config: {
      font_color: '#FFD700',
      font_border_color: '#000000',
      font_border_width: 3,
      background_opacity: 0,
    },
    preview: { fontColor: '#FFD700', borderColor: '#000000', borderWidth: 3, bgColor: '#000000', bgAlpha: 0 },
  },
  {
    name: '柔和阴影',
    config: {
      font_color: '#FFFFFF',
      background_color: '#1a1a2e',
      background_opacity: 0.7,
      background_padding: '8 16',
      background_radius: 15,
      font_border_width: 0,
    },
    preview: { fontColor: '#FFFFFF', borderColor: '#000000', borderWidth: 0, bgColor: '#1a1a2e', bgAlpha: 0.7 },
  },
  {
    name: '蓝底白字',
    config: {
      font_color: '#FFFFFF',
      background_color: '#1890ff',
      background_opacity: 0.9,
      background_padding: '10 20',
      background_radius: 15,
      font_border_width: 0,
    },
    preview: { fontColor: '#FFFFFF', borderColor: '#000000', borderWidth: 0, bgColor: '#1890ff', bgAlpha: 0.9 },
  },
  {
    name: '霓虹光效',
    config: {
      font_color: '#00FFCC',
      font_border_color: '#00FFCC',
      font_border_width: 1,
      background_color: '#000000',
      background_opacity: 0.6,
      background_padding: '6 14',
      background_radius: 15,
    },
    preview: { fontColor: '#00FFCC', borderColor: '#00FFCC', borderWidth: 1, bgColor: '#000000', bgAlpha: 0.6 },
  },
  {
    name: '简约灰调',
    config: {
      font_color: '#CCCCCC',
      font_border_width: 0,
      background_opacity: 0,
    },
    preview: { fontColor: '#CCCCCC', borderColor: '#000000', borderWidth: 0, bgColor: '#000000', bgAlpha: 0 },
  },
  {
    name: '电影字幕',
    config: {
      font_color: '#FFFFFF',
      background_color: '#000000',
      background_opacity: 0.75,
      background_padding: '6 16',
      background_radius: 15,
      font_border_color: '#333333',
      font_border_width: 1,
    },
    preview: { fontColor: '#FFFFFF', borderColor: '#333333', borderWidth: 1, bgColor: '#000000', bgAlpha: 0.75 },
  },
]

function applyPreset(preset: PresetStyle) {
  Object.assign(localConfig, {
    ...localConfig,
    ...preset.config,
  })
}

// === 实时字幕预览 Canvas ===
const previewCanvasRef = ref<HTMLCanvasElement | null>(null)
const CANVAS_PREVIEW_WIDTH = 360
const CANVAS_PREVIEW_HEIGHT = 640

function hexToRgba(hex: string, alpha: number): string {
  const h = hex.replace('#', '')
  const r = parseInt(h.substring(0, 2), 16)
  const g = parseInt(h.substring(2, 4), 16)
  const b = parseInt(h.substring(4, 6), 16)
  return `rgba(${r},${g},${b},${alpha})`
}

function renderSubtitlePreview() {
  const canvas = previewCanvasRef.value
  if (!canvas) return
  const cfg = localConfig
  if (!cfg) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const scaleX = CANVAS_PREVIEW_WIDTH / 1080
  const scaleY = CANVAS_PREVIEW_HEIGHT / 1920
  const scale = Math.min(scaleX, scaleY)

  ctx.clearRect(0, 0, CANVAS_PREVIEW_WIDTH, CANVAS_PREVIEW_HEIGHT)
  ctx.fillStyle = '#1a1a2e'
  ctx.fillRect(0, 0, CANVAS_PREVIEW_WIDTH, CANVAS_PREVIEW_HEIGHT)

  let rawText = (props.previewText || '').trim()
  if (!rawText || rawText.length === 0) {
    rawText = '这是一个字幕样式预览'
  }
  if (rawText.length > 3) {
    const sentences = rawText.split(/(?<=[。！？；，、，.!?;\s])/)
    rawText = sentences[0] || rawText
  }
  const demoText = rawText.replace(/[。！？；，、：；“”''—…（）【】《》〈〉.!?,;:()\[\]{}<>""''\-]/g, '')

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

  ctx.font = `${fontSize}px "PingFang SC", "Microsoft YaHei", sans-serif`
  ctx.textBaseline = 'middle'

  const borderWidth = Math.round((cfg.font_border_width || 0) * scale)
  const borderColor = cfg.font_border_color || '#000000'
  const letterSpacing = Math.round((cfg.letter_spacing || 0) * scale)

  const ctxSafe = ctx as CanvasRenderingContext2D
  function getLineWidth(txt: string): number {
    if (!txt) return 0
    if (letterSpacing > 0 && txt.length > 1) {
      return ctxSafe.measureText(txt).width + letterSpacing * (txt.length - 1)
    }
    return ctxSafe.measureText(txt).width
  }

  const lines: string[] = []
  let curLine = ''
  for (const char of demoText) {
    const test = curLine + char
    if (getLineWidth(test) > maxWidth && curLine) {
      lines.push(curLine)
      curLine = char
    } else {
      curLine = test
    }
  }
  if (curLine) lines.push(curLine)

  const lineHeight = Math.round(fontSize * 1.2)
  const lineWidths = lines.map(l => getLineWidth(l))
  const maxLineWidth = Math.max(...lineWidths)
  const bgWidth = maxLineWidth + padL + padR
  const bgHeight = lines.length * lineHeight + padT + padB

  const baseX = CANVAS_PREVIEW_WIDTH / 2 + offsetX
  const baseY = CANVAS_PREVIEW_HEIGHT - 100 * scale + offsetY
  const bgX = baseX - bgWidth / 2
  const bgY = baseY - bgHeight

  ctxSafe.clearRect(0, 0, CANVAS_PREVIEW_WIDTH, CANVAS_PREVIEW_HEIGHT)
  ctxSafe.fillStyle = '#1a1a2e'
  ctxSafe.fillRect(0, 0, CANVAS_PREVIEW_WIDTH, CANVAS_PREVIEW_HEIGHT)

  const bgAlpha = Math.max(0, Math.min(1, cfg.background_opacity))
  ctxSafe.fillStyle = hexToRgba(cfg.background_color, bgAlpha)
  const r = Math.min(radius, bgHeight / 2, bgWidth / 2)
  if (r > 0) {
    ctxSafe.beginPath()
    ctxSafe.moveTo(bgX + r, bgY)
    ctxSafe.lineTo(bgX + bgWidth - r, bgY)
    ctxSafe.quadraticCurveTo(bgX + bgWidth, bgY, bgX + bgWidth, bgY + r)
    ctxSafe.lineTo(bgX + bgWidth, bgY + bgHeight - r)
    ctxSafe.quadraticCurveTo(bgX + bgWidth, bgY + bgHeight, bgX + bgWidth - r, bgY + bgHeight)
    ctxSafe.lineTo(bgX + r, bgY + bgHeight)
    ctxSafe.quadraticCurveTo(bgX, bgY + bgHeight, bgX, bgY + bgHeight - r)
    ctxSafe.lineTo(bgX, bgY + r)
    ctxSafe.quadraticCurveTo(bgX, bgY, bgX + r, bgY)
    ctxSafe.closePath()
    ctxSafe.fill()
  } else {
    ctxSafe.fillRect(bgX, bgY, bgWidth, bgHeight)
  }

  ctxSafe.fillStyle = cfg.font_color || '#FFFFFF'
  // 每行垂直居中：与后端 Pillow 公式 line_y = bgY + (padT+padB)/2 + lineHeight/2 + i*lineHeight 一致
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    const y = bgY + (padT + padB) / 2 + lineHeight / 2 + i * lineHeight
    const lineWidth = getLineWidth(line)
    const startX = bgX + (bgWidth - lineWidth) / 2
    if (letterSpacing > 0 && line.length > 1) {
      let currentX = startX
      for (const char of line) {
        if (borderWidth > 0) {
          ctxSafe.strokeStyle = borderColor
          ctxSafe.lineWidth = borderWidth
          ctxSafe.lineJoin = 'round'
          ctxSafe.miterLimit = 2
          ctxSafe.strokeText(char, currentX, y)
        }
        ctxSafe.fillText(char, currentX, y)
        currentX += ctxSafe.measureText(char).width + letterSpacing
      }
    } else {
      if (borderWidth > 0) {
        ctxSafe.strokeStyle = borderColor
        ctxSafe.lineWidth = borderWidth
        ctxSafe.lineJoin = 'round'
        ctxSafe.miterLimit = 2
        ctxSafe.strokeText(line, startX, y)
      }
      ctxSafe.fillText(line, startX, y)
    }
  }
}

// 监听字幕配置变化，重新渲染预览 Canvas
watch(
  () => [
    localConfig.font_size,
    localConfig.font_color,
    localConfig.position_x,
    localConfig.position_y,
    localConfig.max_width,
    localConfig.letter_spacing,
    localConfig.background_color,
    localConfig.background_opacity,
    localConfig.background_padding,
    localConfig.background_radius,
    localConfig.font_border_width,
    localConfig.font_border_color,
    props.previewText,
  ],
  () => {
    nextTick(renderSubtitlePreview)
  },
  { immediate: true, deep: true }
)
</script>

<style scoped>
/* 样式与父组件保持一致，无需额外样式 */
</style>
