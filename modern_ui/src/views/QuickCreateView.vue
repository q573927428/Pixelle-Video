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
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { QuickForm } from '../types'
import { filePreviewUrl, getUserUploads, request } from '../api'
import { useTaskRunner } from '../composables/useTaskRunner'
import { useResources } from '../composables/useResources'
import { getAuth } from '../composables/useAuth'
import QuickCreateForm from '../components/QuickCreateForm.vue'
import HistoryDialog from '../components/HistoryDialog.vue'

const { running, progress, statusText, result, submitTask, cleanedPayload, stopPolling } = useTaskRunner()
const { templates, mediaWorkflows, ttsWorkflows, bgmFiles, ttsVoices, handleUpload: uploadResource } = useResources()

const quickForm = ref<QuickForm>({
  text: '', mode: 'generate', title: '', n_scenes: 5,
  min_narration_words: 5, max_narration_words: 20,
  min_image_prompt_words: 30, max_image_prompt_words: 60,
  tts_inference_mode: 'local', tts_engine: 'edge_tts', tts_voice: 'zh-CN-YunjianNeural',
  tts_workflow: 'runninghub/tts_index2.json', ref_audio: null, media_workflow: null, video_fps: 30,
  frame_template: null, prompt_prefix: 'Minimalist black-and-white matchstick figure style illustration, clean lines, simple sketch style', bgm_path: null, bgm_volume: 0.3,
  tts_speed: 1.2, voxcpm_cfg: 2.0, voxcpm_normalize: false,
  voxcpm_denoise: false, voxcpm_control_instruction: '',
  voxcpm_use_prompt_text: false, voxcpm_prompt_text: '',
  api_model: '',
  // 批量生成模式
  batch_mode: false,
  batch_topics: '',
  batch_title_prefix: '',
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
  // 默认模板由 QuickCreateForm 内部处理
})

async function handleUpload(rawFile: File, category: string, target?: string) {
  const result = await uploadResource(rawFile, category, target)
  if (result && target === 'quick_ref_audio') quickForm.value.ref_audio = result.path
}

async function refreshHistory() {
  try {
    const res = await getUserUploads(historyFilterCategory.value || '')
    historyRecords.value = res.records || []
  } catch (_) {
    historyRecords.value = []
  }
}

async function openHistory(category: string) {
  historyFilterCategory.value = category
  await refreshHistory()
  historyVisible.value = true
}

function onHistorySelect(record: any) {
  const cat = historyFilterCategory.value || record.category || 'misc'
  if (cat === 'ref_audio') quickForm.value.ref_audio = record.path
  historyVisible.value = false
  historyFilterCategory.value = undefined
  ElMessage.success(`已选择：${record.name}`)
}

// 批量生成相关状态
const batchResults = ref<any[]>([])
const batchErrors = ref<any[]>([])
const batchTotal = ref(0)
let batchPollTimer: ReturnType<typeof setInterval> | null = null

function batchStopPolling() {
  if (batchPollTimer) {
    clearInterval(batchPollTimer)
    batchPollTimer = null
  }
}

onUnmounted(() => {
  batchStopPolling()
})

async function generate() {
  if (quickForm.value.batch_mode) {
    await generateBatch()
  } else {
    await generateSingle()
  }
}

async function generateSingle() {
  if (!quickForm.value.text.trim()) { ElMessage.warning('请输入主题或文案'); return }
  if (!quickForm.value.frame_template) { ElMessage.warning('请选择画面模板'); return }
  // 如果选择的是 API 模型，将 api_model 值赋给 media_workflow，否则后端会回退到 config.yaml 的默认 RunningHub 工作流
  if (quickForm.value.api_model && !quickForm.value.media_workflow) {
    quickForm.value.media_workflow = quickForm.value.api_model
  }

  // 每日限流预检
  try {
    const auth = getAuth()
    const usage = await auth.fetchUsage()
    if (!usage.is_unlimited && usage.remaining <= 0) {
      ElMessage.warning('今日生成次数已用完，请明天再试或升级为 VIP')
      return
    }
  } catch (e: any) {
    console.warn('查询每日使用量失败，跳过前端预检', e)
  }

  await submitTask('/api/video/generate/async', cleanedPayload(quickForm.value))
}

async function generateBatch() {
  const topics = quickForm.value.batch_topics
    .split('\n')
    .map(t => t.trim())
    .filter(t => t.length > 0)
  
  if (topics.length === 0) { ElMessage.warning('请输入至少一个主题'); return }
  if (!quickForm.value.frame_template) { ElMessage.warning('请选择画面模板'); return }
  if (topics.length > 100) { ElMessage.warning('主题数量不能超过 100 个'); return }
  
  // 每日限流预检：查询用户今日剩余次数
  try {
    const auth = getAuth()
    const usage = await auth.fetchUsage()
    if (!usage.is_unlimited && usage.remaining < topics.length) {
      try {
        await ElMessageBox.confirm(
          `您当前剩余可用次数为 ${usage.remaining} 次，但您设置了 ${topics.length} 个批量生成。<br>超出部分（${topics.length - usage.remaining} 个）将无法生成，是否继续？`,
          '超出每日限制',
          {
            confirmButtonText: '继续生成（仅前 ' + usage.remaining + ' 个有效）',
            cancelButtonText: '取消',
            type: 'warning',
            dangerouslyUseHTMLString: true,
          }
        )
      } catch {
        // 用户点击"取消"，直接返回不提交
        ElMessage.info('已取消生成')
        return
      }
      // 用户确认后，只提交剩余次数以内的主题数
      const allowedTopics = topics.slice(0, usage.remaining)
      if (allowedTopics.length === 0) {
        ElMessage.warning('今日生成次数已用完，无法继续')
        return
      }
      if (allowedTopics.length < topics.length) {
        ElMessage.warning(`今日仅剩 ${usage.remaining} 次，已截取前 ${allowedTopics.length} 个主题进行生成`)
      }
      await doSubmitBatch(allowedTopics)
      return
    }
  } catch (e: any) {
    // 如果查询失败（如未登录），不阻塞，交给后端校验
    console.warn('查询每日使用量失败，跳过前端预检', e)
  }
  
  await doSubmitBatch(topics)
}

async function doSubmitBatch(topics: string[]) {
  
  // 重置状态
  running.value = true
  progress.value = 2
  statusText.value = '批量任务提交中...'
  result.value = {}
  batchResults.value = []
  batchErrors.value = []
  batchTotal.value = topics.length
  
  // 构建共享配置（从 quickForm 提取非批量字段）
  const form = quickForm.value
  const payload: Record<string, any> = {
    topics,
    title_prefix: form.batch_title_prefix || undefined,
    n_scenes: form.n_scenes,
    mode: 'generate',
    tts_inference_mode: form.tts_inference_mode,
    tts_engine: form.tts_engine,
    tts_voice: form.tts_voice,
    tts_speed: form.tts_speed,
    tts_workflow: form.tts_workflow,
    ref_audio: form.ref_audio,
    voxcpm_cfg: form.voxcpm_cfg,
    voxcpm_normalize: form.voxcpm_normalize,
    voxcpm_denoise: form.voxcpm_denoise,
    voxcpm_control_instruction: form.voxcpm_control_instruction,
    voxcpm_use_prompt_text: form.voxcpm_use_prompt_text,
    voxcpm_prompt_text: form.voxcpm_prompt_text,
    min_narration_words: form.min_narration_words,
    max_narration_words: form.max_narration_words,
    min_image_prompt_words: form.min_image_prompt_words,
    max_image_prompt_words: form.max_image_prompt_words,
    video_fps: form.video_fps,
    media_workflow: form.media_workflow || form.api_model || undefined,
    frame_template: form.frame_template,
    prompt_prefix: form.prompt_prefix,
    bgm_path: form.bgm_path,
    bgm_volume: form.bgm_volume,
  }
  
  try {
    const data: any = await request('/api/video/generate/batch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    statusText.value = `批量任务已创建：${data.task_id} (${data.total_videos} 个视频)`
    progress.value = 8
    pollBatchTask(data.task_id, data.total_videos)
  } catch (e: any) {
    running.value = false
    statusText.value = `批量提交失败：${e.message}`
    ElMessage.error(statusText.value)
  }
}

function pollBatchTask(taskId: string, totalVideos: number) {
  batchStopPolling()
  const tick = async () => {
    try {
      const task: any = await request(`/api/tasks/${taskId}`)
      const pct = task.progress?.percentage ?? 0
      progress.value = Math.min(99, pct)
      statusText.value = task.progress?.message || task.message || `状态：${task.status}`
      
      if (task.status === 'completed') {
        running.value = false
        progress.value = 100
        batchStopPolling()
        
        const taskResult = task.result || {}
        batchResults.value = taskResult.results || []
        batchErrors.value = taskResult.errors || []
        
        const successCount = taskResult.success_count || 0
        const failedCount = taskResult.failed_count || 0
        
        statusText.value = `批量生成完成: ${successCount} 成功, ${failedCount} 失败`
        
        // 如果有成功结果，显示第一个视频预览
        if (batchResults.value.length > 0) {
          result.value = { video_url: batchResults.value[0].video_url }
        }
        
        if (failedCount > 0) {
          ElMessage.warning(`批量生成完成: ${successCount} 成功, ${failedCount} 失败`)
        } else {
          ElMessage.success('批量生成全部完成')
        }
      }
      
      if (['failed', 'cancelled'].includes(task.status)) {
        running.value = false
        statusText.value = `批量任务失败：${task.error || task.message || task.status}`
        batchStopPolling()
        ElMessage.error(statusText.value)
      }
    } catch (e: any) {
      running.value = false
      statusText.value = `任务查询失败：${e.message}`
      batchStopPolling()
    }
  }
  tick()
  batchPollTimer = setInterval(tick, 3000)
}

function previewAsset(path: string) {
  window.open(filePreviewUrl(path), '_blank')
}
</script>