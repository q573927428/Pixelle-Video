<template>
  <div class="tool-page">
    <div class="page-header">
      <span class="page-icon">🎨</span>
      <div>
        <h3 class="page-title">素材创作</h3>
        <p class="page-desc">上传图片/视频素材生成成片</p>
      </div>
    </div>
    <div class="page-layout">
      <div class="page-form">
        <AssetBasedForm
          :form="assetForm"
          :uploads="uploads"
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
              {{ running ? '正在生成...' : '开始生成 - 🎨 素材创作' }}
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
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import type { AssetForm } from '../types'
import { filePreviewUrl, loadLocalHistory } from '../api'
import { useTaskRunner } from '../composables/useTaskRunner'
import { useResources } from '../composables/useResources'
import AssetBasedForm from '../components/AssetBasedForm.vue'
import HistoryDialog from '../components/HistoryDialog.vue'

const { running, progress, statusText, result, submitTask, cleanedPayload } = useTaskRunner()
const { bgmFiles, ttsVoices, uploads, handleUpload: uploadResource } = useResources()

const assetForm = ref<AssetForm>({
  assets: [], image_asset: null, video_asset: null,
  video_title: '', intent: '', duration: 30, source: 'runninghub',
  analysis_image_workflow: 'runninghub/analyse_image.json',
  analysis_video_workflow: 'runninghub/analyse_video.json',
  analysis_vlm_model: '', animation_enabled: false,
  api_video_workflow: '', api_video_params: {},
  voice_id: 'zh-CN-YunjianNeural', tts_speed: 1.2, bgm_path: null,
  bgm_volume: 0.2, bgm_mode: 'loop',
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

async function handleUpload(rawFile: File, category: string, target?: string) {
  const result = await uploadResource(rawFile, category, target)
  if (result) {
    if (target === 'asset_image') { assetForm.value.image_asset = result.path; if (!assetForm.value.assets.includes(result.path)) assetForm.value.assets.push(result.path) }
    else if (target === 'asset_video') { assetForm.value.video_asset = result.path; if (!assetForm.value.assets.includes(result.path)) assetForm.value.assets.push(result.path) }
    else if (category === 'image') { assetForm.value.image_asset = result.path; if (!assetForm.value.assets.includes(result.path)) assetForm.value.assets.push(result.path) }
    else if (category === 'video') { assetForm.value.video_asset = result.path; if (!assetForm.value.assets.includes(result.path)) assetForm.value.assets.push(result.path) }
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
  if (cat === 'video') { assetForm.value.video_asset = record.path; if (!assetForm.value.assets.includes(record.path)) assetForm.value.assets.push(record.path) }
  else if (cat === 'image') { assetForm.value.image_asset = record.path; if (!assetForm.value.assets.includes(record.path)) assetForm.value.assets.push(record.path) }
  historyVisible.value = false
  historyFilterCategory.value = undefined
  ElMessage.success(`已选择：${record.name}`)
}

async function generate() {
  if (!assetForm.value.image_asset && !assetForm.value.video_asset) { ElMessage.warning('请上传素材图片或视频'); return }
  await submitTask('/api/pipelines/asset-based/async', cleanedPayload(assetForm.value))
}

function previewAsset(path: string) {
  window.open(filePreviewUrl(path), '_blank')
}
</script>
