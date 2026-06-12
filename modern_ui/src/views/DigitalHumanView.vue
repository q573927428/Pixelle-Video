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
          :uploads="[]"
          :media-workflows="mediaWorkflows"
          :tts-workflows="ttsWorkflows"
          :tts-voices="ttsVoices"
          @upload="(f, c, t) => emit('upload', f, c, t)"
          @select-history="(c) => emit('select-history', c)"
        />
      </div>
      <div class="page-generate">
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">🚀 生成</h3>
            <el-tag :type="running ? 'warning' : 'info'" effect="dark">{{ running ? '生成中' : '就绪' }}</el-tag>
          </div>
          <div class="card-body">
            <el-button type="primary" size="large" style="width:100%;height:48px;font-weight:900;" :loading="running" @click="emit('generate')">
              {{ running ? '正在生成...' : '开始生成 - 🤖 数字人' }}
            </el-button>
            <div style="margin:18px 0;">
              <el-progress :percentage="progress" :status="progressStatus" />
              <div class="small muted" style="margin-top:8px;">{{ statusText }}</div>
            </div>
            <video v-if="result.video_url" class="result-video" controls :src="result.video_url" />
            <div v-else class="empty-preview">
              <div><div style="font-size:38px;margin-bottom:10px;">🎞️</div><div>生成结果将在这里预览</div></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { DigitalForm, WorkflowInfo, TtsVoiceInfo } from '../types'
import DigitalHumanForm from '../components/DigitalHumanForm.vue'

const props = defineProps<{
  digitalForm: DigitalForm
  mediaWorkflows: WorkflowInfo[]
  ttsWorkflows: WorkflowInfo[]
  ttsVoices: TtsVoiceInfo[]
  running: boolean
  progress: number
  statusText: string
  result: any
}>()

const emit = defineEmits<{
  (e: 'upload', file: File, category: string, target: string): void
  (e: 'select-history', category: string): void
  (e: 'preview', path: string): void
  (e: 'generate'): void
}>()

const currentAssets = computed<string[]>(() => {
  return [props.digitalForm.character_asset, props.digitalForm.goods_asset, props.digitalForm.ref_audio].filter((x): x is string => !!x)
})

const progressStatus = computed(() => {
  if (props.progress >= 100) return 'success' as const
  if (props.statusText.includes('失败')) return 'exception' as const
  return undefined
})
</script>