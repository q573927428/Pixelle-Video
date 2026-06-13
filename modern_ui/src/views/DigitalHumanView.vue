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
                    <video v-if="row.video_url" :src="row.video_url" controls style="width:100%;height:80px;object-fit:contain;background:#000;border-radius:4px;" />
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
import { request, filePreviewUrl, loadLocalHistory } from '../api'
import { useTaskRunner } from '../composables/useTaskRunner'
import { useResources } from '../composables/useResources'
import { getAuth } from '../composables/useAuth'
import DigitalHumanForm from '../components/DigitalHumanForm.vue'
import HistoryDialog from '../components/HistoryDialog.vue'

const { running, progress, statusText, result, submitTask } = useTaskRunner()
const { mediaWorkflows, ttsWorkflows, ttsVoices, uploads, handleUpload: uploadResource } = useResources()

const batchResults = ref<any[]>([])

const digitalForm = ref<DigitalForm>({
  mode: 'customize', batch_mode: false, batch_topics: '', batch_goods_assets: [],
  character_asset: null, goods_asset: null, goods_title: '', goods_text: '',
  workflow_config: {
    first_workflow_path: 'workflows/runninghub/digital_image.json',
    second_workflow_path: 'workflows/runninghub/digital_combination.json',
    third_workflow_path: 'workflows/runninghub/digital_customize.json',
    api_image_workflow: '', api_video_workflow: '', api_video_params: {},
  },
  tts_inference_mode: 'local', tts_engine: 'edge_tts', tts_voice: 'zh-CN-YunjianNeural',
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
    else if (target === 'digital_batch_goods') digitalForm.value.batch_goods_assets = [...digitalForm.value.batch_goods_assets, result.path]
    else if (target === 'digital_ref_audio') digitalForm.value.ref_audio = result.path
    else if (category === 'ref_audio') digitalForm.value.ref_audio = result.path
  }
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
  if (cat === 'ref_audio') digitalForm.value.ref_audio = record.path
  else if (cat === 'character_image') digitalForm.value.character_asset = record.path
  else if (cat === 'goods_image') {
    if (digitalForm.value.batch_mode) {
      // 批量模式下追加到多图列表
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

  // 当选择 API 模型模式时，将选中的模型名称映射到 workflow_config 的 api 字段
  if (digitalForm.value.image_service_mode === 'api' && digitalForm.value.image_api_model) {
    payload.workflow_config.api_image_workflow = digitalForm.value.image_api_model
  }
  if (digitalForm.value.video_service_mode === 'api' && digitalForm.value.video_api_model) {
    payload.workflow_config.api_video_workflow = digitalForm.value.video_api_model
  }

  return payload
}

async function generate() {
  if (!digitalForm.value.character_asset) { ElMessage.warning('请上传角色图片'); return }

    // 批量模式
    if (digitalForm.value.batch_mode) {
      const topics = digitalForm.value.batch_topics.trim().split('\n').filter(line => line.trim()).map(line => line.trim())
      if (!topics.length) { ElMessage.warning('请输入商品主题列表'); return }
      
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
          // 用户确认后，只处理剩余次数以内的主题
          const allowedTopics = topics.slice(0, usage.remaining)
          if (allowedTopics.length === 0) {
            ElMessage.warning('今日生成次数已用完，无法继续')
            return
          }
          if (allowedTopics.length < topics.length) {
            ElMessage.warning(`今日仅剩 ${usage.remaining} 次，已截取前 ${allowedTopics.length} 个主题进行生成`)
          }
          // 替换 topics 为截取后的列表
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

    let completedCount = 0
    let failedCount = 0

    for (let i = 0; i < topics.length; i++) {
      const topic = topics[i]
      statusText.value = `[${i + 1}/${topics.length}] 正在生成：${topic}`
      try {
        // 带货模式：topic 作为商品标题，文案 AI 自动生成
        // 自定义模式：topic 作为固定口播文案
        const isCustomize = digitalForm.value.mode === 'customize'
        // 按顺序匹配商品图片：不足时用最后一张，没有则留空
        const bgAssets = digitalForm.value.batch_goods_assets
        const goodsImage = bgAssets.length > 0 ? bgAssets[Math.min(i, bgAssets.length - 1)] : ''
        const payload = buildPayload({
          mode: digitalForm.value.mode,
          title: isCustomize ? '' : topic,
          text: isCustomize ? topic : '',
        })
        // 覆盖 goods_assets 为当前主题对应的商品图
        payload.goods_assets = goodsImage ? [goodsImage] : []
        const data: any = await request('/api/pipelines/digital-human/async', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        })
        // 等待任务完成
        const taskId = data.task_id
        const pollResult = await pollTaskOnce(taskId)
        if (pollResult.success) {
          completedCount++
          batchResults.value[i].success = true
          batchResults.value[i].loading = false
          // 从已完成的任务中获取视频 URL
          try {
            const task: any = await request(`/api/tasks/${taskId}`)
            if (task.result?.video_url) {
              batchResults.value[i].video_url = task.result.video_url
            }
          } catch (_) {}
        } else {
          failedCount++
          batchResults.value[i].success = false
          batchResults.value[i].loading = false
        }
      } catch (e: any) {
        failedCount++
        batchResults.value[i].success = false
        batchResults.value[i].loading = false
        console.error(`[${i + 1}/${topics.length}] ${topic} 失败：`, e)
      }
      progress.value = Math.round(((i + 1) / topics.length) * 100)
    }

    running.value = false
    progress.value = 100
    statusText.value = `批量生成完成：成功 ${completedCount} 个，失败 ${failedCount} 个，共 ${topics.length} 个`
    if (failedCount === 0) {
      ElMessage.success(`批量生成完成！共 ${completedCount} 个视频`)
    } else {
      ElMessage.warning(`批量生成完成：成功 ${completedCount} 个，失败 ${failedCount} 个`)
    }
    return
  }

  // 单次模式
  if (digitalForm.value.mode === 'digital' && !digitalForm.value.goods_asset) { ElMessage.warning('请上传商品图片'); return }
  const payload = buildPayload()
  payload.mode = digitalForm.value.mode
  payload.goods_text = digitalForm.value.goods_text
  payload.goods_title = digitalForm.value.goods_title

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

  await submitTask('/api/pipelines/digital-human/async', payload)
}

// 辅助：轮询单个任务直到完成或失败
function pollTaskOnce(taskId: string): Promise<{ success: boolean; error?: string }> {
  return new Promise((resolve) => {
    const maxAttempts = 120 // 最多轮询 120 次 × 3秒 = 6 分钟
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
        resolve({ success: false, error: e.message })
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
