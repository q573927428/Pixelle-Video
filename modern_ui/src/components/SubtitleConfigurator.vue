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
          <div style="display:flex;gap:6px;flex-wrap:nowrap;">
            <div
              v-for="preset in presetStyles"
              :key="preset.name"
              @click="applyPreset(preset)"
              :style="{
                display:'flex',
                alignItems:'center',
                justifyContent:'center',
                width:'42px',
                height:'38px',
                borderRadius:'6px',
                border: selectedPresetName === preset.name ? '2px solid var(--el-color-primary)' : '1px solid var(--el-border-color-light)',
                cursor:'pointer',
                transition:'all 0.2s',
                position:'relative',
                background:'#1a1a2e',
                boxShadow: selectedPresetName === preset.name ? '0 0 8px rgba(64,158,255,0.5)' : 'none',
              }"
              @mouseenter="(e) => { if (selectedPresetName !== preset.name) { (e.currentTarget as HTMLElement).style.borderColor = 'var(--el-color-primary)'; (e.currentTarget as HTMLElement).style.boxShadow = '0 0 4px rgba(64,158,255,0.3)'; } }"
              @mouseleave="(e) => { if (selectedPresetName !== preset.name) { (e.currentTarget as HTMLElement).style.borderColor = 'var(--el-border-color-light)'; (e.currentTarget as HTMLElement).style.boxShadow = 'none'; } }"
              :title="preset.name"
            >
              <span style="font-size:16px;font-weight:bold;z-index:1;line-height:1;"
                :style="{
                  color: preset.preview.fontColor,
                  textShadow: preset.preview.borderWidth > 0 ? `0 0 0 ${preset.preview.borderColor}, 0 0 1px ${preset.preview.borderColor}` : 'none',
                }"
              >字</span>
              <div v-if="preset.preview.bgAlpha > 0" style="position:absolute;inset:2px;border-radius:3px;pointer-events:none;"
                :style="{ background: preset.preview.bgColor, opacity: preset.preview.bgAlpha }"
              ></div>
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
            <el-form-item label="文字粗细">
              <el-slider v-model="localConfig.font_weight" :min="100" :max="900" :step="100" show-input />
            </el-form-item>
            <el-form-item label="文字字体">
              <el-input v-model="localConfig.font_family" placeholder="如: NotoSansSC-Bold" style="width:260px;" />
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

// 当前选中的预设名称，默认选中第一个
const selectedPresetName = ref<string>('经典白字')

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
      font_border_width: 1,
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
      font_border_width: 1,
    },
    preview: { fontColor: '#FFFFFF', borderColor: '#000000', borderWidth: 0, bgColor: '#1a1a2e', bgAlpha: 0.7 },
  },
  {
    name: '蓝底白字',
    config: {
      font_color: '#FFFFFF',
      background_color: '#1890ff',
      background_opacity: 0.9,
      font_border_width: 1,
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
    },
    preview: { fontColor: '#00FFCC', borderColor: '#00FFCC', borderWidth: 1, bgColor: '#000000', bgAlpha: 0.6 },
  },
  {
    name: '简约灰调',
    config: {
      font_color: '#CCCCCC',
      font_border_width: 1,
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
      font_border_color: '#333333',
      font_border_width: 1,
    },
    preview: { fontColor: '#FFFFFF', borderColor: '#333333', borderWidth: 1, bgColor: '#000000', bgAlpha: 0.75 },
  },
]

function applyPreset(preset: PresetStyle) {
  selectedPresetName.value = preset.name
  Object.assign(localConfig, {
    ...localConfig,
    ...preset.config,
  })
}

</script>

<style scoped>
/* 样式与父组件保持一致，无需额外样式 */
</style>
