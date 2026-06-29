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
          <div v-if="localConfig.selected_bgm" class="bgm-audio-player">
            <audio ref="audioRef" :src="filePreviewUrl(localConfig.selected_bgm)" controls class="bgm-audio" />
          </div>
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

<style scoped>
.bgm-audio-player {
  margin-top: 8px;
  width: 100%;
}
.bgm-audio {
  width: 100%;
  height: 40px;
}
</style>

<script setup lang="ts">
import { ref, watch, reactive, computed } from 'vue'
import type { BgmConfig, BgmInfo } from '../types'
import { filePreviewUrl } from '../api'
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

const audioRef = ref<HTMLAudioElement | null>(null)

watch(
  () => localConfig.volume,
  (val) => {
    if (audioRef.value) {
      audioRef.value.volume = val / 100
    }
  }
)

watch(
  () => localConfig.selected_bgm,
  () => {
    if (audioRef.value) {
      audioRef.value.volume = localConfig.volume / 100
    }
  }
)

const selectedBgmName = computed(() => {
  const bgm = props.bgmList.find((b) => b.path === localConfig.selected_bgm)
  return bgm ? bgm.name : localConfig.selected_bgm
})

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