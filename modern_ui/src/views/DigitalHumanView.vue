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
          :uploads="uploads"
          :media-workflows="mediaWorkflows"
          :tts-workflows="ttsWorkflows"
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
    <HistoryDialog v-model="historyVisible" :loading="historyLoading" :records="historyRecords" :filter-category="historyFilterCategory" @select="onHistorySelect" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import type { DigitalForm } from '../types'
import { filePreviewUrl, loadLocalHistory } from '../api'
import { useTaskRunner } from '../composables/useTaskRunner'
import { useResources } from '../composables/useResources'
import DigitalHumanForm from '../components/DigitalHumanForm.vue'
import HistoryDialog from '../components/HistoryDialog.vue'

const { running, progress, statusText, result, submitTask } = useTaskRunner()
const { mediaWorkflows, ttsWorkflows, ttsVoices, uploads, handleUpload: uploadResource, loadAll } = useResources()

const digitalForm = ref<DigitalForm>({
  mode: 'digital', character_asset: null, goods_asset: null, goods_title: '', goods_text: '',
  workflow_config: {
    first_workflow_path: 'workflows/runninghub/digital_image.json',
    second_workflow_path: 'workflows/runninghub/digital_combination.json',
    third_workflow_path: 'workflows/runninghub/digital_customize.json',
    api_image_workflow: '', api_video_workflow: '', api_video_params: {},
  },
  tts_inference_mode: 'local', tts_engine: 'edge_tts', tts_voice: 'zh-CN-YunjianNeural',
  tts_speed: 1.2, tts_workflow: '', ref_audio: '', voxcpm_cfg: 2.0,
  voxcpm_normalize: false, voxcpm_denoise: false,
  voxcpm_control_instruction: '', voxcpm_use_prompt_text: false,
  voxcpm_prompt_text: '',
  image_service_mode: 'runninghub', image_api_model: '',
  video_service_mode: 'runninghub', video_api_model: '',
  video_api_params: { duration: 5, resolution: '1280x720', aspect_ratio: '9:16', negative_prompt: '', watermark: false },
})

const historyVisible = ref(false)
const historyLoading = ref(false)
const historyRecords = ref<any[]>([])
const historyFilterCategory = ref<string | undefined>(undefined)

const currentAssets = computed<string[]>(() => {
  return [digitalForm.value.character_asset, digitalForm.value.goods_asset, digitalForm.value.ref_audio].filter((x): x is string => !!x)
})

const progressStatus = computed(() => {
  if (progress.value >= 100) return 'success' as const
  if (statusText.value.includes('失败')) return 'exception' as const
  return undefined
})

async function handleUpload(rawFile: File, category: string, target?: string) {
  const result = await uploadResource(rawFile, category, target)
  if (result) {
    if (target === 'digital_character') digitalForm.value.character_asset = result.path
    else if (target === 'digital_goods') digitalForm.value.goods_asset = result.path
    else if (target === 'digital_ref_audio') digitalForm.value.ref_audio = result.path
    else if (category === 'ref_audio') digitalForm.value.ref_audio = result.path
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
  if (cat === 'ref_audio') digitalForm.value.ref_audio = record.path
  else if (cat === 'character_image') digitalForm.value.character_asset = record.path
  else if (cat === 'goods_image') digitalForm.value.goods_asset = record.path
  historyVisible.value = false
  historyFilterCategory.value = undefined
  ElMessage.success(`已选择：${record.name}`)
}

async function generate() {
  if (!digitalForm.value.character_asset) { ElMessage.warning('请上传角色图片'); return }
  if (digitalForm.value.mode === 'digital' && !digitalForm.value.goods_asset) { ElMessage.warning('请上传商品图片'); return }

  // 构建后端所需的 payload：映射前端字段名到后端字段名
  const payload: Record<string, any> = {}
  payload.character_assets = digitalForm.value.character_asset ? [digitalForm.value.character_asset] : []
  payload.goods_assets = digitalForm.value.goods_asset ? [digitalForm.value.goods_asset] : []
  payload.mode = digitalForm.value.mode
  payload.goods_title = digitalForm.value.goods_title
  payload.goods_text = digitalForm.value.goods_text
  payload.workflow_config = digitalForm.value.workflow_config
  payload.tts_inference_mode = digitalForm.value.tts_inference_mode
  payload.tts_engine = digitalForm.value.tts_engine
  payload.tts_voice = digitalForm.value.tts_voice
  payload.tts_speed = digitalForm.value.tts_speed
  payload.tts_workflow = digitalForm.value.tts_workflow
  payload.ref_audio = digitalForm.value.ref_audio
  payload.voxcpm_cfg = digitalForm.value.voxcpm_cfg
  payload.voxcpm_normalize = digitalForm.value.voxcpm_normalize
  payload.voxcpm_denoise = digitalForm.value.voxcpm_denoise
  payload.voxcpm_control_instruction = digitalForm.value.voxcpm_control_instruction
  payload.voxcpm_use_prompt_text = digitalForm.value.voxcpm_use_prompt_text
  payload.voxcpm_prompt_text = digitalForm.value.voxcpm_prompt_text
  payload.image_service_mode = digitalForm.value.image_service_mode
  payload.image_api_model = digitalForm.value.image_api_model
  payload.video_service_mode = digitalForm.value.video_service_mode
  payload.video_api_model = digitalForm.value.video_api_model
  payload.video_api_params = digitalForm.value.video_api_params

  await submitTask('/api/pipelines/digital-human/async', payload)
}

function previewAsset(path: string) {
  window.open(filePreviewUrl(path), '_blank')
}

onMounted(() => {
  loadAll()
})
</script>
