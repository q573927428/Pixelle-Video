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
              <div class="small muted" style="padding:8px 12px;background:rgba(255,255,255,0.04);border-radius:8px;">{{ statusText }}</div>
            </div>
            <div v-if="submitted || batchSubmitted" style="margin:12px 0;padding:12px;background:rgba(64,158,255,0.08);border:1px solid rgba(64,158,255,0.2);border-radius:8px;">
              <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
                <span style="font-size:14px;color:var(--el-color-primary);flex:1;">
                  ✅ 任务已提交，可以关闭网页。可在「任务中心」查看，成功后可以在「历史记录」查看。
                </span>
                <el-button size="small" type="danger" plain @click="cancelAllTasks">一键取消全部</el-button>
              </div>
            </div>

            <!-- 批量模式结果列表 -->
            <template v-if="batchResults.length > 0">
              <el-table :data="batchResults" style="width:100%;" size="small" max-height="400">
                <el-table-column prop="index" label="#" width="40" />
                <el-table-column prop="topic" label="主题" min-width="80" show-overflow-tooltip />
                <el-table-column label="状态" width="80">
                  <template #default="{ row }">
                    <el-tag v-if="row.loading" type="info" size="small">生成中</el-tag>
                    <el-tag v-else-if="row.success" type="success" size="small">成功</el-tag>
                    <el-tag v-else type="danger" size="small">失败</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="预览" min-width="160">
                  <template #default="{ row }">
                    <video v-if="row.video_url" :src="row.video_url" controls style="width:100%;height:150px;object-fit:contain;background:#000;border-radius:4px;" />
                    <span v-else class="small muted">暂无</span>
                  </template>
                </el-table-column>
              </el-table>
            </template>

            <!-- 单次模式结果 -->
            <video v-if="!batchResults.length && result.video_url" class="result-video" controls :src="result.video_url" />
            <div v-else-if="!batchResults.length" class="empty-preview">
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
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { DigitalForm } from '../types'
import { request, filePreviewUrl, getUserUploads, cancelTask } from '../api'
import { useTaskRunner } from '../composables/useTaskRunner'
import { useResources } from '../composables/useResources'
import { getAuth } from '../composables/useAuth'
import DigitalHumanForm from '../components/DigitalHumanForm.vue'
import HistoryDialog from '../components/HistoryDialog.vue'

const { running, progress, statusText, result, submitTask, currentTaskId, submitted, cancelCurrentTask } = useTaskRunner()
const { mediaWorkflows, ttsWorkflows, ttsVoices, handleUpload: uploadResource } = useResources()

const batchResults = ref<any[]>([])
const batchSubmitted = ref(false)
const batchTaskIds = ref<string[]>([])

const digitalForm = ref<DigitalForm>({
  mode: 'customize', batch_mode: false, batch_topics: '', batch_goods_assets: [], batch_character_assets: [],
  character_asset: null, goods_asset: null, goods_title: '', goods_text: '',
  workflow_config: {
    first_workflow_path: 'workflows/runninghub/digital_image.json',
    second_workflow_path: 'workflows/runninghub/digital_combination.json',
    third_workflow_path: 'workflows/runninghub/digital_customize.json',
    api_image_workflow: '', api_video_workflow: '', api_video_params: {},
  },
  tts_inference_mode: 'comfyui', tts_engine: 'edge_tts', tts_voice: 'zh-CN-YunjianNeural',
  tts_speed: 1.2, tts_workflow: 'runninghub/tts_index2.json', ref_audio: '', voxcpm_cfg: 2.0,
  voxcpm_normalize: false, voxcpm_denoise: false,
  voxcpm_control_instruction: '', voxcpm_use_prompt_text: false,
  voxcpm_prompt_text: '',
  image_service_mode: 'runninghub', image_api_model: '',
  video_service_mode: 'runninghub', video_api_model: '',
  video_api_params: { duration: 10, resolution: '1280x720', aspect_ratio: '9:16', negative_prompt: '', watermark: false },
})

const historyVisible = ref(false)
const historyLoading = ref(false)
const historyRecords = ref<any[]>([])
const historyFilterCategory = ref<string | undefined>(undefined)

const currentAssets = computed<string[]>(() => {
  return [digitalForm.value.character_asset, digitalForm.value.goods_asset, digitalForm.value.ref_audio].filter((x): x is string => !!x)
})


async function handleUpload(rawFile: File, category: string, target?: string) {
  const result = await uploadResource(rawFile, category, target)
  if (result) {
    if (target === 'digital_character') digitalForm.value.character_asset = result.path
    else if (target === 'digital_batch_character') digitalForm.value.batch_character_assets = [...digitalForm.value.batch_character_assets, result.path]
    else if (target === 'digital_goods') digitalForm.value.goods_asset = result.path
    else if (target === 'digital_batch_goods') digitalForm.value.batch_goods_assets = [...digitalForm.value.batch_goods_assets, result.path]
    else if (target === 'digital_ref_audio') digitalForm.value.ref_audio = result.path
    else if (category === 'ref_audio') digitalForm.value.ref_audio = result.path
  }
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
  if (cat === 'ref_audio') digitalForm.value.ref_audio = record.path
  else if (cat === 'character_image') {
    if (digitalForm.value.batch_mode) {
      digitalForm.value.batch_character_assets = [...digitalForm.value.batch_character_assets, record.path]
    } else {
      digitalForm.value.character_asset = record.path
    }
  }
  else if (cat === 'goods_image') {
    if (digitalForm.value.batch_mode) {
      digitalForm.value.batch_goods_assets = [...digitalForm.value.batch_goods_assets, record.path]
    } else {
      digitalForm.value.goods_asset = record.path
    }
  }
  historyVisible.value = false
  historyFilterCategory.value = undefined
  ElMessage.success(`已选择：${record.name}`)
}

function buildPayload(overrides?: { mode?: string; title?: string; text?: string }): Record<string, any> {
  const payload: Record<string, any> = {}
  payload.character_assets = digitalForm.value.character_asset ? [digitalForm.value.character_asset] : []
  payload.goods_assets = digitalForm.value.goods_asset ? [digitalForm.value.goods_asset] : []
  payload.mode = overrides?.mode || digitalForm.value.mode
  payload.goods_title = overrides?.title ?? digitalForm.value.goods_title
  payload.goods_text = overrides?.text ?? digitalForm.value.goods_text
  payload.workflow_config = { ...digitalForm.value.workflow_config }
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
  payload.video_api_params = { ...digitalForm.value.video_api_params }

  if (digitalForm.value.image_service_mode === 'api' && digitalForm.value.image_api_model) {
    payload.workflow_config.api_image_workflow = digitalForm.value.image_api_model
  }
  if (digitalForm.value.video_service_mode === 'api' && digitalForm.value.video_api_model) {
    payload.workflow_config.api_video_workflow = digitalForm.value.video_api_model
  }

  return payload
}

async function generate() {
  if (digitalForm.value.batch_mode) {
    if (!digitalForm.value.character_asset && digitalForm.value.batch_character_assets.length === 0) {
      ElMessage.warning('请上传角色图片'); return
    }
  } else {
    if (!digitalForm.value.character_asset) { ElMessage.warning('请上传角色图片'); return }
  }

    if (digitalForm.value.batch_mode) {
      const topics = digitalForm.value.batch_topics.trim().split('\n').filter(line => line.trim()).map(line => line.trim())
      if (!topics.length) { ElMessage.warning('请输入商品主题列表'); return }
      
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
            ElMessage.info('已取消生成')
            return
          }
          const allowedTopics = topics.slice(0, usage.remaining)
          if (allowedTopics.length === 0) {
            ElMessage.warning('今日生成次数已用完，无法继续')
            return
          }
          if (allowedTopics.length < topics.length) {
            ElMessage.warning(`今日仅剩 ${usage.remaining} 次，已截取前 ${allowedTopics.length} 个主题进行生成`)
          }
          topics.splice(0, topics.length, ...allowedTopics)
        }
      } catch (e: any) {
        console.warn('查询每日使用量失败，跳过前端预检', e)
      }

    running.value = true
    progress.value = 0
    statusText.value = `批量生成开始：共 ${topics.length} 个主题...`
    result.value = {}
    batchResults.value = topics.map((t, i) => ({ index: i + 1, topic: t, success: false, video_url: '', loading: true }))
    batchSubmitted.value = false
    batchTaskIds.value = []

    // Step 1: Submit ALL tasks in parallel immediately
    const taskIds: string[] = []
    for (let i = 0; i < topics.length; i++) {
      const topic = topics[i]
      statusText.value = `[${i + 1}/${topics.length}] 提交中：${topic}`
      try {
        const isCustomize = digitalForm.value.mode === 'customize'
        const bgAssets = digitalForm.value.batch_goods_assets
        const charAssets = digitalForm.value.batch_character_assets
        const goodsImage = bgAssets.length > 0 ? bgAssets[Math.min(i, bgAssets.length - 1)] : ''
        const characterImage = charAssets.length > 0 ? charAssets[Math.min(i, charAssets.length - 1)] : ''
        const payload = buildPayload({
          mode: digitalForm.value.mode,
          title: isCustomize ? '' : topic,
          text: isCustomize ? topic : '',
        })
        payload.goods_assets = goodsImage ? [goodsImage] : []
        payload.character_assets = characterImage ? [characterImage] : (digitalForm.value.character_asset ? [digitalForm.value.character_asset] : [])
        const data: any = await request('/api/pipelines/digital-human/async', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        })
        taskIds[i] = data.task_id
      } catch (e: any) {
        taskIds[i] = ''
        batchResults.value[i].success = false
        batchResults.value[i].loading = false
        console.error(`[${i + 1}/${topics.length}] ${topic} 提交失败：`, e)
      }
    }

    batchTaskIds.value = taskIds.filter(id => id)
    batchSubmitted.value = true

    // Step 2: Poll ALL tasks in parallel
    statusText.value = `全部已提交（${topics.length} 个），等待执行...`
    const pollPromises = taskIds.map((taskId, i) => pollTaskOnce(taskId))
    const pollResults = await Promise.all(pollPromises)

    let completedCount = 0
    let failedCount = 0
    for (let i = 0; i < topics.length; i++) {
      batchResults.value[i].loading = false
      if (pollResults[i]?.success) {
        completedCount++
        batchResults.value[i].success = true
        try {
          const task: any = await request(`/api/tasks/${taskIds[i]}`)
          if (task.result?.video_url) {
            batchResults.value[i].video_url = task.result.video_url
          }
        } catch (_) {}
      } else {
        failedCount++
        batchResults.value[i].success = false
      }
    }

    running.value = false
    progress.value = 100
    statusText.value = `批量生成完成：成功 ${completedCount} 个，失败 ${failedCount} 个，共 ${topics.length} 个`
    batchSubmitted.value = false
    batchTaskIds.value = []
    return
  }

  if (digitalForm.value.mode === 'digital' && !digitalForm.value.goods_asset) { ElMessage.warning('请上传商品图片'); return }
  const payload = buildPayload()
  payload.mode = digitalForm.value.mode
  payload.goods_text = digitalForm.value.goods_text
  payload.goods_title = digitalForm.value.goods_title

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

  await submitTask('/api/pipelines/digital-human/async', payload)
}

async function cancelAllTasks() {
  if (batchTaskIds.value.length > 0) {
    // 批量取消：逐个取消所有子任务
    running.value = false
    batchSubmitted.value = false
    for (const tid of batchTaskIds.value) {
      try {
        await cancelTask(tid)
      } catch (_) {}
    }
    batchTaskIds.value = []
    statusText.value = '全部任务已取消'
  } else if (currentTaskId.value) {
    await cancelCurrentTask()
  }
}

function pollTaskOnce(taskId: string): Promise<{ success: boolean; error?: string }> {
  return new Promise((resolve) => {
    const maxAttempts = 600  // 最多等 30 分钟（600 * 3s）
    let attempts = 0
    const tick = async () => {
      try {
        const task: any = await request(`/api/tasks/${taskId}`)
        if (task.status === 'completed') {
          resolve({ success: true })
          return
        }
        if (['failed', 'cancelled'].includes(task.status)) {
          resolve({ success: false, error: task.error || task.message })
          return
        }
        attempts++
        if (attempts >= maxAttempts) {
          resolve({ success: false, error: '轮询超时' })
          return
        }
        setTimeout(tick, 3000)
      } catch (e: any) {
        // 网络波动等临时错误不要直接判失败，重试
        console.warn(`[pollTaskOnce] polling error for ${taskId}:`, e.message)
        attempts++
        if (attempts >= maxAttempts) {
          resolve({ success: false, error: '轮询失败过多' })
          return
        }
        setTimeout(tick, 5000)  // 网络错误后等 5 秒重试
      }
    }
    tick()
  })
}

function previewAsset(path: string) {
  window.open(filePreviewUrl(path), '_blank')
}
</script>

<style scoped>
:deep(.el-table) {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: rgba(255,255,255,0.04);
  --el-table-row-hover-bg-color: rgba(255,255,255,0.06);
  --el-table-border-color: rgba(255,255,255,0.08);
  --el-table-text-color: rgba(255,255,255,0.85);
  --el-table-header-text-color: rgba(255,255,255,0.6);
}
:deep(.el-table__body tr.current-row > td) {
  background: transparent;
}
:deep(.el-table__inner-wrapper::before) {
  display: none;
}
:deep(.el-table__header-wrapper tr th) {
  border-bottom: 1px solid rgba(255,255,255,0.08);
}
:deep(.el-table__body tr td) {
  border-bottom: 1px solid rgba(255,255,255,0.04);
}
</style>