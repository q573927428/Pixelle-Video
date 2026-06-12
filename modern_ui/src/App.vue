<template>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-logo">🎬</div>
        <div>
          <h1 class="brand-title">Pixelle Studio</h1>
          <p class="brand-subtitle">Full Modern UI</p>
        </div>
      </div>

      <div class="nav-title">工作台</div>
      <button
        v-for="item in navItems"
        :key="item.key"
        class="nav-item"
        :class="{ active: activeView === item.key }"
        @click="switchView(item.key)"
      >
        <span class="nav-icon">{{ item.icon }}</span>
        <span>{{ item.label }}</span>
      </button>
    </aside>

    <main class="main">
      <!-- <div class="topbar">
        <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
          <span class="status-pill"><i class="dot" :class="{ ok: healthOk }"></i>{{ healthOk ? 'API 在线' : 'API 检测中' }}</span>
          <el-button @click="loadAll">刷新资源</el-button>
        </div>
      </div> -->

      <QuickCreateView
        v-if="activeView === 'quick_create'"
        :quick-form="quickForm"
        :templates="templates"
        :media-workflows="mediaWorkflows"
        :tts-workflows="ttsWorkflows"
        :bgm-files="bgmFiles"
        :tts-voices="ttsVoices"
        :running="running"
        :progress="progress"
        :status-text="statusText"
        :result="result"
        @upload="handleUpload"
        @select-history="openHistory"
        @preview="previewAsset"
        @generate="generateQuickCreate"
      />

      <AssetBasedView
        v-if="activeView === 'custom_media'"
        :asset-form="assetForm"
        :bgm-files="bgmFiles"
        :tts-voices="ttsVoices"
        :running="running"
        :progress="progress"
        :status-text="statusText"
        :result="result"
        @upload="handleUpload"
        @select-history="openHistory"
        @preview="previewAsset"
        @generate="generateAssetBased"
      />

      <DigitalHumanView
        v-if="activeView === 'digital_human'"
        :digital-form="digitalForm"
        :media-workflows="mediaWorkflows"
        :tts-workflows="ttsWorkflows"
        :tts-voices="ttsVoices"
        :running="running"
        :progress="progress"
        :status-text="statusText"
        :result="result"
        @upload="handleUpload"
        @select-history="openHistory"
        @preview="previewAsset"
        @generate="generateDigitalHuman"
      />

      <I2vView
        v-if="activeView === 'image_to_video'"
        :i2v-form="i2vForm"
        :workflows="i2vWorkflows"
        :running="running"
        :progress="progress"
        :status-text="statusText"
        :result="result"
        @upload="handleUpload"
        @select-history="openHistory"
        @preview="previewAsset"
        @generate="generateI2v"
      />

      <ActionTransferView
        v-if="activeView === 'action_transfer'"
        :action-form="actionForm"
        :workflows="actionWorkflows"
        :running="running"
        :progress="progress"
        :status-text="statusText"
        :result="result"
        @upload="handleUpload"
        @select-history="openHistory"
        @preview="previewAsset"
        @generate="generateActionTransfer"
      />

      <!-- ====== 📤 上传中心 ====== -->
      <section v-if="activeView === 'assets'">
        <div class="grid grid-2">
          <div class="card">
            <div class="card-header"><h3 class="card-title">📤 上传中心</h3><el-tag effect="dark">temp/uploads</el-tag></div>
            <div class="card-body">
              <el-tabs v-model="uploadCategory">
                <el-tab-pane label="图片素材" name="image" />
                <el-tab-pane label="视频素材" name="video" />
                <el-tab-pane label="参考音频" name="ref_audio" />
                <el-tab-pane label="数字人角色" name="character_image" />
                <el-tab-pane label="商品图" name="goods_image" />
              </el-tabs>
              <UploadBox :category="uploadCategory" :accept="uploadAccept" @upload="handleUpload" @select-history="openHistory" />
              <UploadList :uploads="uploads" />
            </div>
          </div>
          <div class="card">
            <div class="card-header"><h3 class="card-title">🧭 使用说明</h3></div>
            <div class="card-body">
              <el-timeline>
                <el-timeline-item timestamp="1. 上传素材" type="primary">上传后的绝对路径会自动加入对应工具表单。</el-timeline-item>
                <el-timeline-item timestamp="2. 选择工作流" type="success">图生视频使用 i2v_ 工作流，动作迁移使用 af_ 工作流。</el-timeline-item>
                <el-timeline-item timestamp="3. 提交任务" type="warning">所有工具统一进入任务中心，可轮询状态并预览结果。</el-timeline-item>
              </el-timeline>
            </div>
          </div>
        </div>
      </section>

      <!-- ====== 📊 任务中心 ====== -->
      <section v-if="activeView === 'tasks'">
        <div class="card">
          <div class="card-header"><h3 class="card-title">📊 任务中心</h3><el-button @click="loadAll">刷新</el-button></div>
          <div class="card-body">
            <div v-if="!tasks.length" class="empty-preview">暂无任务</div>
            <div v-for="task in tasks" :key="task.task_id" class="task-item">
              <div class="task-top"><span class="mono">{{ task.task_id }}</span><el-tag :type="tagType(task.status)" effect="dark">{{ task.status }}</el-tag></div>
              <el-progress :percentage="task.percentage || 0" />
              <div class="small muted">{{ task.message || `状态：${task.status}` }}</div>
            </div>
          </div>
        </div>
      </section>

      <!-- ====== 🧩 资源管理 ====== -->
      <section v-if="activeView === 'resources'">
        <div class="grid grid-3">
          <ResourceCard title="🖼️ 模板" :items="templates" label-key="display_name" tag-key="size" />
          <ResourceCard title="🧩 媒体工作流" :items="mediaWorkflows" label-key="display_name" tag-key="source" />
          <ResourceCard title="🎵 BGM / TTS" :items="[...bgmFiles, ...ttsWorkflows]" label-key="display_name" fallback-label-key="name" tag-key="source" />
        </div>
      </section>
    </main>

    <HistoryDialog v-model="historyVisible" :loading="historyLoading" :records="historyRecords" :filter-category="historyFilterCategory" @select="onHistorySelect" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import type { QuickForm, AssetForm, DigitalForm, ActionForm, NavItem, TtsVoiceInfo } from './types'
import type { I2vForm as I2vFormData } from './types'
import { request, uploadFile as apiUpload, loadResources, loadTasks as apiLoadTasks, checkHealth, filePreviewUrl, saveToLocalHistory, loadLocalHistory } from './api'
import UploadBox from './components/UploadBox.vue'
import UploadList from './components/UploadList.vue'
import ResourceCard from './components/ResourceCard.vue'
import HistoryDialog from './components/HistoryDialog.vue'
import QuickCreateView from './views/QuickCreateView.vue'
import AssetBasedView from './views/AssetBasedView.vue'
import DigitalHumanView from './views/DigitalHumanView.vue'
import I2vView from './views/I2vView.vue'
import ActionTransferView from './views/ActionTransferView.vue'

const activeView = ref('quick_create')
const selectedTool = ref('quick_create')
const uploadCategory = ref('image')

const uploadAccept = computed(() => {
  const acceptMap: Record<string, string> = {
    image: 'image/*',
    video: 'video/*',
    ref_audio: 'audio/*',
    character_image: 'image/*',
    goods_image: 'image/*',
  }
  return acceptMap[uploadCategory.value] || undefined
})
const healthOk = ref(false)
const running = ref(false)
const progress = ref(0)
const statusText = ref('等待开始')
const templates = ref<any[]>([])
const mediaWorkflows = ref<any[]>([])
const ttsWorkflows = ref<any[]>([])
const bgmFiles = ref<any[]>([])
const ttsVoices = ref<TtsVoiceInfo[]>([])
const tasks = ref<any[]>([])
const uploads = ref<any[]>([])
const result = ref<any>({})

const historyVisible = ref(false)
const historyLoading = ref(false)
const historyRecords = ref<any[]>([])
const historyFilterCategory = ref<string | undefined>(undefined)

let pollTimer: ReturnType<typeof setInterval> | null = null

const toolKeys = ['quick_create', 'custom_media', 'digital_human', 'image_to_video', 'action_transfer'] as const

const navItems: NavItem[] = [
  { key: 'quick_create', icon: '⚡', label: '快速创作' },
  { key: 'custom_media', icon: '🎨', label: '素材创作' },
  { key: 'digital_human', icon: '🤖', label: '数字人' },
  { key: 'image_to_video', icon: '🎥', label: '图生视频' },
  { key: 'action_transfer', icon: '💃', label: '动作迁移' },
  { key: 'assets', icon: '📤', label: '上传中心' },
  { key: 'tasks', icon: '📊', label: '任务中心' },
  { key: 'resources', icon: '🧩', label: '资源管理' },
]

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
})

const i2vForm = ref<I2vFormData>({
  image_asset: null, prompt_text: '', workflow_key: '', api_video_params_json: '',
})

const actionForm = ref<ActionForm>({
  video_asset: null, image_asset: null, prompt_text: '', duration: 5,
  workflow_key: '', api_video_params_json: '',
})

const i2vWorkflows = computed(() =>
  mediaWorkflows.value.filter(wf => {
    const key = (wf.key || wf.path || '').toLowerCase()
    const name = (wf.name || key).toLowerCase()
    return key.startsWith('api/') || name.startsWith('i2v_') || key.includes('/i2v_')
  })
)

const actionWorkflows = computed(() =>
  mediaWorkflows.value.filter(wf => {
    const key = (wf.key || wf.path || '').toLowerCase()
    const name = (wf.name || key).toLowerCase()
    return key.startsWith('api/') || name.startsWith('af_') || key.includes('/af_')
  })
)

onMounted(() => loadAll())

function switchView(key: string) {
  activeView.value = key
  if (toolKeys.includes(key as any)) {
    selectedTool.value = key
  }
}

function parseJson(text: string) {
  if (!text || !text.trim()) return {}
  try { return JSON.parse(text) }
  catch (e: any) { throw new Error(`JSON 参数格式错误：${e.message}`) }
}

function cleanedPayload(payload: any) {
  return Object.fromEntries(
    Object.entries(payload).filter(([_, v]) => v !== '' && v !== null && v !== undefined && !(Array.isArray(v) && v.length === 0))
  )
}

async function loadAll() {
  await Promise.allSettled([checkH(), loadRes(), loadT()])
}

async function checkH() {
  healthOk.value = await checkHealth()
}

async function loadRes() {
  try {
    const res = await loadResources()
    templates.value = res.templates
    mediaWorkflows.value = res.mediaWorkflows
    ttsWorkflows.value = res.ttsWorkflows
    bgmFiles.value = res.bgmFiles
    ttsVoices.value = res.ttsVoices || []
    if (!quickForm.value.frame_template && templates.value.length) {
      const portrait = templates.value.find((t: any) => t.orientation === 'portrait')
      quickForm.value.frame_template = (portrait || templates.value[0]).key
    }
  } catch (e: any) {
    ElMessage.error(`资源加载失败：${e.message}`)
  }
}

async function loadT() {
  try { tasks.value = await apiLoadTasks() }
  catch { tasks.value = [] }
}

async function handleUpload(rawFile: File, category: string, target?: string) {
  if (!rawFile) return
  try {
    const data = await apiUpload(rawFile, category)
    uploads.value.unshift(data)
    applyUploadTarget(data.path, target, category)
    saveToLocalHistory(data, category)
    ElMessage.success(`${data.filename} 上传成功`)
  } catch (e: any) {
    ElMessage.error(`上传失败：${e.message}`)
  }
}

function applyUploadTarget(path: string, target?: string, category?: string) {
  if (target === 'quick_ref_audio') quickForm.value.ref_audio = path
  else if (target === 'asset_image') { assetForm.value.image_asset = path; if (!assetForm.value.assets.includes(path)) assetForm.value.assets.push(path) }
  else if (target === 'asset_video') { assetForm.value.video_asset = path; if (!assetForm.value.assets.includes(path)) assetForm.value.assets.push(path) }
  else if (target === 'digital_character') digitalForm.value.character_asset = path
  else if (target === 'digital_goods') digitalForm.value.goods_asset = path
  else if (target === 'digital_ref_audio') digitalForm.value.ref_audio = path
  else if (target === 'i2v_image') i2vForm.value.image_asset = path
  else if (target === 'action_video') actionForm.value.video_asset = path
  else if (target === 'action_image') actionForm.value.image_asset = path
  else if (category === 'image') { assetForm.value.image_asset = path; if (!assetForm.value.assets.includes(path)) assetForm.value.assets.push(path); i2vForm.value.image_asset = path; actionForm.value.image_asset = path }
  else if (category === 'video') { assetForm.value.video_asset = path; if (!assetForm.value.assets.includes(path)) assetForm.value.assets.push(path); actionForm.value.video_asset = path }
  else if (category === 'ref_audio') { quickForm.value.ref_audio = path; digitalForm.value.ref_audio = path }
}

function openHistory(category: string) {
  const localHistory = loadLocalHistory()
  historyRecords.value = localHistory.slice(0, 50)
  historyFilterCategory.value = category
  historyVisible.value = true
}

function onHistorySelect(record: any) {
  const cat = historyFilterCategory.value || record.category || 'misc'
  if (cat === 'ref_audio') { quickForm.value.ref_audio = record.path; digitalForm.value.ref_audio = record.path }
  else if (cat === 'character_image') { digitalForm.value.character_asset = record.path }
  else if (cat === 'goods_image') { digitalForm.value.goods_asset = record.path }
  else if (cat === 'video') { actionForm.value.video_asset = record.path; assetForm.value.video_asset = record.path; if (!assetForm.value.assets.includes(record.path)) assetForm.value.assets.push(record.path) }
  else if (cat === 'image') { assetForm.value.image_asset = record.path; if (!assetForm.value.assets.includes(record.path)) assetForm.value.assets.push(record.path); i2vForm.value.image_asset = record.path; actionForm.value.image_asset = record.path }
  historyVisible.value = false
  historyFilterCategory.value = undefined
  ElMessage.success(`已选择：${record.name}`)
}

async function submitTask(url: string, payload: any) {
  running.value = true
  progress.value = 2
  statusText.value = '任务提交中...'
  result.value = {}
  try {
    const data: any = await request(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    statusText.value = `任务已创建：${data.task_id}`
    progress.value = 8
    pollTask(data.task_id)
  } catch (e: any) {
    running.value = false
    statusText.value = `提交失败：${e.message}`
    ElMessage.error(statusText.value)
  }
}

async function generateQuickCreate() {
  if (!quickForm.value.text.trim()) { ElMessage.warning('请输入主题或文案'); return }
  if (!quickForm.value.frame_template) { ElMessage.warning('请选择画面模板'); return }
  await submitTask('/api/video/generate/async', cleanedPayload(quickForm.value))
}

async function generateAssetBased() {
  if (!assetForm.value.image_asset && !assetForm.value.video_asset) { ElMessage.warning('请上传素材图片或视频'); return }
  await submitTask('/api/pipelines/asset-based/async', cleanedPayload(assetForm.value))
}

async function generateDigitalHuman() {
  if (!digitalForm.value.character_asset) { ElMessage.warning('请上传角色图片'); return }
  if (digitalForm.value.mode === 'digital' && !digitalForm.value.goods_asset) { ElMessage.warning('请上传商品图片'); return }
  await submitTask('/api/pipelines/digital-human/async', cleanedPayload(digitalForm.value))
}

async function generateI2v() {
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

async function generateActionTransfer() {
  if (!actionForm.value.video_asset) { ElMessage.warning('请上传参考动作视频'); return }
  if (!actionForm.value.image_asset) { ElMessage.warning('请上传目标图片'); return }
  if (!actionForm.value.prompt_text.trim()) { ElMessage.warning('请输入提示词'); return }
  if (!actionForm.value.workflow_key) { ElMessage.warning('请选择动作迁移工作流'); return }
  await submitTask('/api/pipelines/action-transfer/async', {
    video_assets: [actionForm.value.video_asset].filter(Boolean),
    image_assets: [actionForm.value.image_asset].filter(Boolean),
    prompt_text: actionForm.value.prompt_text,
    duration: actionForm.value.duration,
    workflow_key: actionForm.value.workflow_key,
    api_video_params: parseJson(actionForm.value.api_video_params_json),
  })
}

function pollTask(taskId: string) {
  if (pollTimer) clearInterval(pollTimer)
  const tick = async () => {
    try {
      const task: any = await request(`/api/tasks/${taskId}`)
      progress.value = Math.max(8, Math.min(99, task.percentage || 0))
      statusText.value = task.message || `状态：${task.status}`
      if (task.status === 'completed') {
        running.value = false; progress.value = 100; result.value = task.result || {}; statusText.value = '生成完成'
        clearInterval(pollTimer!); loadT(); ElMessage.success('视频生成完成')
      }
      if (['failed', 'cancelled'].includes(task.status)) {
        running.value = false; statusText.value = `任务失败：${task.error || task.message || task.status}`
        clearInterval(pollTimer!); loadT(); ElMessage.error(statusText.value)
      }
    } catch (e: any) {
      running.value = false; statusText.value = `任务查询失败：${e.message}`
      clearInterval(pollTimer!)
    }
  }
  tick()
  pollTimer = setInterval(tick, 3000)
}

function tagType(status: string): string {
  return { completed: 'success', running: 'warning', pending: 'info', failed: 'danger', cancelled: 'info' }[status] || 'info'
}

function previewAsset(path: string) {
  window.open(filePreviewUrl(path), '_blank')
}

(window as any).filePreviewUrl = filePreviewUrl
</script>