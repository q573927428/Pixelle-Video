<template>
  <div class="form-section-wrapper">
    <div class="form-section">
      <div class="form-section-title" style="display:flex;justify-content:space-between;align-items:center;">
        <span>🎵 背景音乐</span>
        <div style="display:flex;align-items:center;gap:6px;">
          <span style="font-size:13px;font-weight:400;">开关</span>
          <el-switch
            :model-value="enabled"
            @update:model-value="$emit('update:enabled', $event)"
          />
        </div>
      </div>
      <div class="form-section-body" v-if="enabled">
        <el-form-item label="选择背景音乐">
          <el-select v-model="localConfig.selected_bgm" filterable placeholder="选择已有背景音乐" clearable style="width:100%;">
            <el-option
              v-for="bgm in bgmList"
              :key="bgm.path"
              :label="bgm.name"
              :value="bgm.path"
            >
              <div style="display:flex;justify-content:space-between;align-items:center;">
                <span>{{ bgm.name }}</span>
                <el-tag size="small" type="info" effect="plain">{{ bgm.source }}</el-tag>
              </div>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="自定义上传BGM">
          <div class="upload-field-container">
            <UploadBox category="custom_bgm" accept="audio/*,.mp3,.wav,.flac,.aac" @upload="(f, c) => $emit('upload', f, c, 'custom_bgm')" @select-history="(c) => $emit('select-history', c)" />
            <FilePreview v-if="localConfig.custom_bgm" :items="[localConfig.custom_bgm]" @remove="localConfig.custom_bgm = null" />
          </div>
        </el-form-item>
        <el-form-item label="音量">
          <el-slider v-model="localConfig.volume" :min="0" :max="100" :step="5" show-input>
            <template #prepend>🔉</template>
          </el-slider>
        </el-form-item>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, reactive } from 'vue'
import type { BgmConfig, BgmInfo } from '../types'
import UploadBox from './UploadBox.vue'
import FilePreview from './FilePreview.vue'

const props = defineProps<{
  enabled: boolean
  config: BgmConfig
  bgmList: BgmInfo[]
}>()

const emit = defineEmits<{
  (e: 'update:enabled', val: boolean): void
  (e: 'update:config', val: BgmConfig): void
  (e: 'upload', file: File, category: string, target: string): void
  (e: 'select-history', category: string): void
}>()

const localConfig = reactive<BgmConfig>({ ...props.config })

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
    emit('update:config', val as BgmConfig)
  },
  { deep: true }
)
</script>