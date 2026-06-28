<template>
  <div class="form-section-wrapper">
    <div class="form-section">
      <div class="form-section-title" style="display:flex;justify-content:space-between;align-items:center;">
        <span>🖼️ 画中画混剪</span>
        <div style="display:flex;align-items:center;gap:6px;">
          <span style="font-size:13px;font-weight:400;">开关</span>
          <el-switch
            :model-value="enabled"
            @update:model-value="$emit('update:enabled', $event)"
          />
        </div>
      </div>
      <div class="form-section-body" v-if="enabled">
        <el-form-item label="叠加视频">
          <div class="upload-field-container">
            <UploadBox category="pip_overlay_video" accept="video/*,.mp4,.mov,.avi" @upload="(f, c) => $emit('upload', f, c, 'pip_overlay_video')" @select-history="(c) => $emit('select-history', c)" />
            <FilePreview v-if="localConfig.overlay_video" :items="[localConfig.overlay_video]" @remove="localConfig.overlay_video = null" />
          </div>
        </el-form-item>
        <el-form-item label="叠加图片">
          <div class="upload-field-container">
            <UploadBox category="pip_overlay_image" accept="image/*,.png,.jpg,.jpeg,.webp" @upload="(f, c) => $emit('upload', f, c, 'pip_overlay_image')" @select-history="(c) => $emit('select-history', c)" />
            <FilePreview v-if="localConfig.overlay_image" :items="[localConfig.overlay_image]" @remove="localConfig.overlay_image = null" />
          </div>
        </el-form-item>
        <el-divider style="margin:8px 0;" />
        <el-form-item label="位置 X">
          <el-slider v-model="localConfig.position_x" :min="-500" :max="500" :step="10" show-input />
        </el-form-item>
        <el-form-item label="位置 Y">
          <el-slider v-model="localConfig.position_y" :min="-1700" :max="100" :step="10" show-input />
        </el-form-item>
        <el-form-item label="宽度">
          <el-slider v-model="localConfig.width" :min="100" :max="1920" :step="20" show-input />
        </el-form-item>
        <el-form-item label="高度">
          <el-slider v-model="localConfig.height" :min="100" :max="1920" :step="20" show-input />
        </el-form-item>
        <el-form-item label="透明度">
          <el-slider v-model="localConfig.opacity" :min="0" :max="1.0" :step="0.05" show-input />
        </el-form-item>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, reactive } from 'vue'
import type { PipMixConfig } from '../types'
import UploadBox from './UploadBox.vue'
import FilePreview from './FilePreview.vue'

const props = defineProps<{
  enabled: boolean
  config: PipMixConfig
}>()

const emit = defineEmits<{
  (e: 'update:enabled', val: boolean): void
  (e: 'update:config', val: PipMixConfig): void
  (e: 'upload', file: File, category: string, target: string): void
  (e: 'select-history', category: string): void
}>()

const localConfig = reactive<PipMixConfig>({ ...props.config })

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
    emit('update:config', val as PipMixConfig)
  },
  { deep: true }
)
</script>