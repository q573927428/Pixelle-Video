<template>
  <div class="tool-page">
    <div class="page-header">
      <span class="page-icon">🎥</span>
      <div>
        <h3 class="page-title">图生视频</h3>
        <p class="page-desc">首帧图片驱动视频生成</p>
      </div>
    </div>
    <div class="page-layout">
      <div class="page-form">
        <I2vForm
          :form="i2vForm"
          :uploads="uploads"
          :workflows="workflows"
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
              {{ running ? '正在生成...' : '开始生成 - 🎥 图生视频' }}
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
    <HistoryDialog v-model="historyVisible" :loading="historyLoading" :records="historyRecords" :filter-category="historyFilterCategory" @select="onHistorySelect" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import type { I2vForm as I2vFormData, WorkflowInfo } from '../types'
import { filePreviewUrl, loadLocalHistory } from '../api'
import { useTaskRunner } from '../composables/useTaskRunner'
import { useResources } from '../composables/useResources'
import I2vForm from '../components/I2vForm.vue'
import HistoryDialog from '../components/HistoryDialog.vue'

const { running, progress, statusText, result, submitTask, parseJson } = useTaskRunner()
const { mediaWorkflows, uploads, handleUpload: uploadResource, loadAll } = useResources()

const i2vForm = ref<I2vFormData>({
  image_asset: null, prompt_text: '', workflow_key: '', api_video_params_json: '',
})

const historyVisible = ref(false)
const historyLoading = ref(false)
const historyRecords = ref<any[]>([])
const historyFilterCategory = ref<string | undefined>(undefined)

const workflows = computed<WorkflowInfo[]>(() =>
  mediaWorkflows.value.filter(wf => {
    const key = (wf.key || wf.path || '').toLowerCase()
    const name = (wf.name || key).toLowerCase()
    return key.startsWith('api/') || name.startsWith('i2v_') || key.includes('/i2v_')
  })
)

const progressStatus = computed(() => {
  if (progress.value >= 100) return 'success' as const
  if (statusText.value.includes('失败')) return 'exception' as const
  return undefined
})

async function handleUpload(rawFile: File, category: string, target?: string) {
  const result = await uploadResource(rawFile, category, target)
  if (result) {
    if (target === 'i2v_image') i2vForm.value.image_asset = result.path
    else if (category === 'image') i2vForm.value.image_asset = result.path
  }
}

function openHistory(category: string) {
  const localHistory = loadLocalHistory()
  historyRecords.value = localHistory.slice(0, 50)
  historyFilterCategory.value = category
  historyVisible.value = true
}

function onHistorySelect(record: any) {
  const cat = historyFilterCategory.value || record.category || 'misc'
  if (cat === 'image') i2vForm.value.image_asset = record.path
  historyVisible.value = false
  historyFilterCategory.value = undefined
  ElMessage.success(`已选择：${record.name}`)
}

async function generate() {
  if (!i2vForm.value.image_asset) { ElMessage.warning('请上传首帧图片'); return }
  if (!i2vForm.value.prompt_text.trim()) { ElMessage.warning('请输入提示词'); return }
  if (!i2vForm.value.workflow_key) { ElMessage.warning('请选择图生视频工作流'); return }
  await submitTask('/api/pipelines/image-to-video/async', {
    image_assets: [i2vForm.value.image_asset].filter(Boolean),
    prompt_text: i2vForm.value.prompt_text,
    workflow_key: i2vForm.value.workflow_key,
    api_video_params: parseJson(i2vForm.value.api_video_params_json),
  })
}

function previewAsset(path: string) {
  window.open(filePreviewUrl(path), '_blank')
}

onMounted(() => {
  loadAll()
})
</script>
