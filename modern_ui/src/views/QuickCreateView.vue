<template>
  <div class="tool-page">
    <div class="page-header">
      <span class="page-icon">⚡</span>
      <div>
        <h3 class="page-title">快速创作</h3>
        <p class="page-desc">文本到视频，AI 分镜/固定文案</p>
      </div>
    </div>
    <div class="page-layout">
      <div class="page-form">
        <QuickCreateForm
          :form="quickForm"
          :templates="templates"
          :media-workflows="mediaWorkflows"
          :tts-workflows="ttsWorkflows"
          :bgm-files="bgmFiles"
          :tts-voices="ttsVoices"
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
            <el-button type="primary" size="large" style="width:100%;height:48px;font-weight:900;" :loading="running" @click="generate">
              {{ running ? '正在生成...' : '开始生成 - ⚡ 快速创作' }}
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
    <HistoryDialog v-model="historyVisible" :loading="historyLoading" :records="historyRecords" :filter-category="historyFilterCategory" @select="onHistorySelect" @delete="refreshHistory" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import type { QuickForm } from '../types'
import { filePreviewUrl, loadLocalHistory } from '../api'
import { useTaskRunner } from '../composables/useTaskRunner'
import { useResources } from '../composables/useResources'
import QuickCreateForm from '../components/QuickCreateForm.vue'
import HistoryDialog from '../components/HistoryDialog.vue'

const { running, progress, statusText, result, submitTask, cleanedPayload } = useTaskRunner()
const { templates, mediaWorkflows, ttsWorkflows, bgmFiles, ttsVoices, handleUpload: uploadResource } = useResources()

const quickForm = ref<QuickForm>({
  text: '', mode: 'generate', title: '', n_scenes: 5,
  min_narration_words: 5, max_narration_words: 20,
  min_image_prompt_words: 30, max_image_prompt_words: 60,
  tts_inference_mode: 'local', tts_engine: 'edge_tts', tts_voice: 'zh-CN-YunjianNeural',
  tts_workflow: null, ref_audio: null, media_workflow: null, video_fps: 30,
  frame_template: null, prompt_prefix: '', bgm_path: null, bgm_volume: 0.3,
  tts_speed: 1.2, voxcpm_cfg: 2.0, voxcpm_normalize: false,
  voxcpm_denoise: false, voxcpm_control_instruction: '',
  voxcpm_use_prompt_text: false, voxcpm_prompt_text: '',
})

const historyVisible = ref(false)
const historyLoading = ref(false)
const historyRecords = ref<any[]>([])
const historyFilterCategory = ref<string | undefined>(undefined)

const progressStatus = computed(() => {
  if (progress.value >= 100) return 'success' as const
  if (statusText.value.includes('失败')) return 'exception' as const
  return undefined
})

onMounted(() => {
  // 设置默认模板
  if (!quickForm.value.frame_template && templates.value.length) {
    const portrait = templates.value.find((t: any) => t.orientation === 'portrait')
    quickForm.value.frame_template = (portrait || templates.value[0]).key
  }
})

async function handleUpload(rawFile: File, category: string, target?: string) {
  const result = await uploadResource(rawFile, category, target)
  if (result && target === 'quick_ref_audio') quickForm.value.ref_audio = result.path
}

function refreshHistory() {
  const localHistory = loadLocalHistory()
  historyRecords.value = localHistory.slice(0, 50)
}

function openHistory(category: string) {
  refreshHistory()
  historyFilterCategory.value = category
  historyVisible.value = true
}

function onHistorySelect(record: any) {
  const cat = historyFilterCategory.value || record.category || 'misc'
  if (cat === 'ref_audio') quickForm.value.ref_audio = record.path
  historyVisible.value = false
  historyFilterCategory.value = undefined
  ElMessage.success(`已选择：${record.name}`)
}

async function generate() {
  if (!quickForm.value.text.trim()) { ElMessage.warning('请输入主题或文案'); return }
  if (!quickForm.value.frame_template) { ElMessage.warning('请选择画面模板'); return }
  await submitTask('/api/video/generate/async', cleanedPayload(quickForm.value))
}

function previewAsset(path: string) {
  window.open(filePreviewUrl(path), '_blank')
}
</script>