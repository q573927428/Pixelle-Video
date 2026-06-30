<template>
  <div class="form-section-wrapper">
    <div class="form-section">
      <div class="form-section-title" style="display:flex;justify-content:space-between;align-items:center;">
        <span>📌 标题叠加</span>
        <div style="display:flex;align-items:center;gap:6px;">
          <span style="font-size:13px;font-weight:400;">开关</span>
          <el-switch
            :model-value="enabled"
            @update:model-value="$emit('update:enabled', $event)"
          />
        </div>
      </div>
      <div class="form-section-body" v-if="enabled">
        <el-form-item label="标题文字">
          <el-input
            v-model="localConfig.text"
            type="textarea"
            :rows="3"
            placeholder="输入标题文字，每行一行（支持多行）"
            :maxlength="200"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="显示时长">
          <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
            <el-radio-group v-model="localConfig.display_mode">
              <el-radio-button value="full">全视频时长</el-radio-button>
              <el-radio-button value="duration">指定秒数</el-radio-button>
            </el-radio-group>
            <el-input-number v-if="localConfig.display_mode === 'duration'" v-model="localConfig.duration_seconds" :min="1" :max="60" :step="1" />
          </div>
        </el-form-item>

        <!-- 预制标题样式 -->
        <div style="margin-bottom:14px;">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
            <span style="font-size:13px;font-weight:500;color:var(--el-color-primary);">🎨 标题样式</span>
            <el-tag size="small" type="info" effect="plain">点击切换</el-tag>
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
            <div
              v-for="preset in presetStyles"
              :key="preset.name"
              @click="applyPreset(preset)"
              style="display:flex;align-items:center;gap:8px;padding:8px 10px;border-radius:6px;border:1px solid var(--el-border-color-light);cursor:pointer;transition:all 0.2s;position:relative;background:#1a1a2e;"
              @mouseenter="(e) => { (e.currentTarget as HTMLElement).style.borderColor = 'var(--el-color-primary)'; (e.currentTarget as HTMLElement).style.background = 'var(--el-fill-color-light)'; }"
              @mouseleave="(e) => { (e.currentTarget as HTMLElement).style.borderColor = 'var(--el-border-color-light)'; (e.currentTarget as HTMLElement).style.background = '#1a1a2e'; }"
            >
              <div style="flex-shrink:0;width:48px;height:28px;border-radius:4px;overflow:hidden;display:flex;align-items:center;justify-content:center;">
                <span style="font-size:11px;font-weight:bold;line-height:1;z-index:1;"
                  :style="{
                    color: preset.preview.fontColor,
                    textShadow: preset.preview.borderWidth > 0 ? `0 0 1px ${preset.preview.borderColor}, 0 0 1px ${preset.preview.borderColor}` : 'none',
                  }"
                >T</span>
              </div>
              <span style="font-size:12px;font-weight:500;white-space:nowrap;">{{ preset.name }}</span>
            </div>
          </div>
        </div>

        <!-- 高级设置折叠 -->
        <el-collapse v-model="advancedOpen">
          <el-collapse-item name="title-advanced">
            <template #title>
              <span style="font-size:13px;font-weight:500;color:var(--el-color-primary);">⚙️ 高级设置</span>
            </template>
            <el-form-item label="文字大小">
              <el-slider v-model="localConfig.font_size" :min="24" :max="120" :step="2" show-input />
            </el-form-item>
            <el-form-item label="文字颜色">
              <el-color-picker v-model="localConfig.font_color" show-alpha />
            </el-form-item>
            <el-form-item label="文字粗细">
              <el-slider v-model="localConfig.font_weight" :min="100" :max="900" :step="100" show-input />
            </el-form-item>
            <el-divider style="margin:8px 0;" />
            <el-form-item label="文字边框粗细">
              <el-slider v-model="localConfig.font_border_width" :min="0" :max="10" :step="1" show-input />
            </el-form-item>
            <el-form-item label="文字边框颜色">
              <el-color-picker v-model="localConfig.font_border_color" show-alpha />
            </el-form-item>
            <el-divider style="margin:8px 0;" />
            <el-form-item label="文字背景颜色">
              <el-color-picker v-model="localConfig.background_color" />
            </el-form-item>
            <el-form-item label="背景透明度">
              <el-slider v-model="localConfig.background_opacity" :min="0" :max="100" :step="5" show-input />
            </el-form-item>
            <el-form-item label="背景内边距">
              <el-input v-model="localConfig.background_padding" placeholder="如: 12px 24px" style="width:200px;" />
            </el-form-item>
            <el-form-item label="背景圆角">
              <el-slider v-model="localConfig.background_radius" :min="0" :max="50" :step="2" show-input />
            </el-form-item>
            <el-divider style="margin:8px 0;" />
            <el-form-item label="文字对齐">
              <el-radio-group v-model="localConfig.text_align">
                <el-radio-button value="left">左对齐</el-radio-button>
                <el-radio-button value="center">居中</el-radio-button>
                <el-radio-button value="right">右对齐</el-radio-button>
              </el-radio-group>
            </el-form-item>
            <el-divider style="margin:8px 0;" />
            <el-form-item label="最大宽度">
              <el-slider v-model="localConfig.max_width" :min="200" :max="1980" :step="20" show-input />
            </el-form-item>
            <el-form-item label="位置 X">
              <el-slider v-model="localConfig.position_x" :min="-500" :max="500" :step="10" show-input />
            </el-form-item>
            <el-form-item label="位置 Y">
              <el-slider v-model="localConfig.position_y" :min="-1700" :max="100" :step="10" show-input />
            </el-form-item>
          </el-collapse-item>
        </el-collapse>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, reactive } from 'vue'
import type { TitleOverlayConfig } from '../types'

const props = defineProps<{
  enabled: boolean
  config: TitleOverlayConfig
}>()

const emit = defineEmits<{
  (e: 'update:enabled', val: boolean): void
  (e: 'update:config', val: TitleOverlayConfig): void
}>()

const localConfig = reactive<TitleOverlayConfig>({ ...props.config })

watch(
  () => props.config,
  (val) => {
    if (val) {
      Object.assign(localConfig, val)
    }
  },
  { deep: true }
)

watch(
  () => ({ ...localConfig }),
  (val) => {
    emit('update:config', val as TitleOverlayConfig)
  },
  { deep: true }
)

const advancedOpen = ref<string[]>([])

interface PresetPreview {
  fontColor: string
  borderColor: string
  borderWidth: number
}

interface PresetStyle {
  name: string
  config: Partial<TitleOverlayConfig>
  preview: PresetPreview
}

const presetStyles: PresetStyle[] = [
  {
    name: '经典白字',
    config: { font_color: '#FFFFFF', font_size: 68, font_weight: 700, font_border_width: 2, font_border_color: '#000000' },
    preview: { fontColor: '#FFFFFF', borderColor: '#000000', borderWidth: 1 },
  },
  {
    name: '金色醒目',
    config: { font_color: '#FFD700', font_size: 68, font_weight: 900, font_border_width: 3, font_border_color: '#000000' },
    preview: { fontColor: '#FFD700', borderColor: '#000000', borderWidth: 1 },
  },
  {
    name: '蓝色科技',
    config: { font_color: '#00BFFF', font_size: 68, font_weight: 700, font_border_width: 2, font_border_color: '#003366' },
    preview: { fontColor: '#00BFFF', borderColor: '#003366', borderWidth: 1 },
  },
  {
    name: '粉红温馨',
    config: { font_color: '#FF69B4', font_size: 68, font_weight: 600, font_border_width: 2, font_border_color: '#8B004B' },
    preview: { fontColor: '#FF69B4', borderColor: '#8B004B', borderWidth: 1 },
  },
  {
    name: '青绿典雅',
    config: { font_color: '#00E5A0', font_size: 68, font_weight: 700, font_border_width: 2, font_border_color: '#004D33' },
    preview: { fontColor: '#00E5A0', borderColor: '#004D33', borderWidth: 1 },
  },
  {
    name: '橙色热情',
    config: { font_color: '#FF8C00', font_size: 68, font_weight: 800, font_border_width: 2, font_border_color: '#5C3300' },
    preview: { fontColor: '#FF8C00', borderColor: '#5C3300', borderWidth: 1 },
  },
  {
    name: '霓虹光效',
    config: { font_color: '#00FFCC', font_size: 72, font_weight: 900, font_border_width: 2, font_border_color: '#00FFCC' },
    preview: { fontColor: '#00FFCC', borderColor: '#00FFCC', borderWidth: 1 },
  },
  {
    name: '纯净白字',
    config: { font_color: '#FFFFFF', font_size: 68, font_weight: 700, font_border_width: 0 },
    preview: { fontColor: '#FFFFFF', borderColor: '#000000', borderWidth: 1 },
  },
]

function applyPreset(preset: PresetStyle) {
  Object.assign(localConfig, {
    ...localConfig,
    ...preset.config,
  })
}
</script>