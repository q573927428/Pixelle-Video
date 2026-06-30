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
          :tts-workflows="ttsWorkflows"
          :tts-voices="ttsVoices"
          :bgm-list="bgmFiles"
          @upload="handleUpload"
          @select-history="openHistory"
        />
      </div>
      <div class="page-generate">
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">🚀 提交生成</h3>
          </div>
          <div class="card-body">
            <el-button type="primary" size="large" style="width:100%;height:48px;font-weight:900;margin-bottom:20px;" :disabled="!canSubmit" @click="generate">
              提交生成 - 🤖 数字人
            </el-button>
            <!-- ZS币费用预览 -->
            <div v-if="estimatedSeconds > 0" class="cost-preview">
              <div class="cost-row">
                <span>文案字数</span>
                <span><strong>{{ textCharCount }}</strong> 字</span>
              </div>
              <div class="cost-row">
                <span>预估时长</span>
                <span><strong>{{ estimatedSeconds }}</strong> 秒</span>
              </div>
              <div class="cost-row">
                <span>预估消耗</span>
                <span><strong style="color:#fbbf24;">{{ estimatedCost }}</strong> ZS币</span>
              </div>
              <div class="cost-row">
                <span>当前余额</span>
                <span :style="{ color: auth.zsBalance.value >= estimatedCost ? '#22c55e' : '#ef4444' }">
                  <strong>{{ auth.zsBalance.value }}</strong> ZS币
                  <span v-if="auth.zsBalance.value < estimatedCost" style="margin-left:4px;">⚠️ 不足</span>
                </span>
              </div>
            </div>

            <!-- 提交成功后显示提示信息 -->
            <div style="margin-top:20px;padding:12px;border-radius:8px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);font-size:13px;line-height:1.8;">
              <div style="color:var(--el-text-color-secondary);">💡 提交生成视频后：</div>
              <ul style="margin:4px 0 0;padding-left:18px;color:var(--el-text-color-regular);">
                <li>可以关闭此页面，任务将在后台继续处理</li>
                <li>在「任务中心」可查看处理进度</li>
                <li>在「历史记录」中可查看和下载生成的视频</li>
                <li>在「历史记录」中还可以编辑发布一生成成功的视频</li>
              </ul>
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
import { ElMessage } from 'element-plus'
import type { DigitalForm } from '../types'
import { getUserUploads } from '../api'
import { useTaskRunner } from '../composables/useTaskRunner'
import { useResources } from '../composables/useResources'
import { getAuth } from '../composables/useAuth'
import DigitalHumanForm from '../components/DigitalHumanForm.vue'
import HistoryDialog from '../components/HistoryDialog.vue'

const { submitTask, currentTaskId, cancelCurrentTask } = useTaskRunner()
const { ttsWorkflows, ttsVoices, bgmFiles, handleUpload: uploadResource, loadT: refreshTaskList } = useResources()

const auth = getAuth()

// ZS币计费
const textCharCount = computed(() => {
  return (digitalForm.value.goods_text || '').replace(/[。！？；，、：；“”''—…（）【】《》〈〉.!?,;:()\[\]{}<>""''\-/\s]/g, '').length
})
const estimatedSeconds = computed(() => {
  const text = digitalForm.value.goods_text?.trim() || ''
  const speed = digitalForm.value.tts_speed || 1.0
  if (!text) return 0
  const cleanText = text.replace(/[。！？；，、：；“”''—…（）【】《》〈〉.!?,;:()\[\]{}<>""''\-/\s]/g, '')
  return Math.ceil(cleanText.length / 4 / speed) || 0
})
const estimatedCost = computed(() => {
  const baseCost = estimatedSeconds.value * 5
  const discount = auth.userDiscount.value
  if (discount < 100) return Math.max(1, Math.floor(baseCost * discount / 100))
  return baseCost
})

// 提交状态
const submitMessage = ref('')
const submitSuccess = ref(false)
const canSubmit = computed(() => {
  if (!digitalForm.value.character_asset) return false
  if (!digitalForm.value.goods_text?.trim()) return false
  if (digitalForm.value.tts_inference_mode === 'comfyui' && !digitalForm.value.ref_audio) return false
  if (estimatedSeconds.value > 0 && auth.zsBalance.value < estimatedCost.value) return false
  return true
})

function getVideoWorkflowPath(): string {
  if (auth.isVip.value || auth.isSvip.value || auth.isAdmin.value) {
    return 'workflows/runninghub/digital_combination_new.json'
  }
  return 'workflows/runninghub/digital_combination.json'
}

const digitalForm = ref<DigitalForm>({
  mode: 'customize',
  ai_title: '',
  ai_topics: '',
  character_asset: null, goods_text: '',
  workflow_config: {
    first_workflow_path: 'workflows/runninghub/digital_image.json',
    second_workflow_path: getVideoWorkflowPath(),
    third_workflow_path: 'workflows/runninghub/digital_customize.json',
    api_image_workflow: '', api_video_workflow: '', api_video_params: {},
  },
  tts_inference_mode: 'comfyui', tts_engine: 'edge_tts', tts_voice: 'zh-CN-YunjianNeural',
  tts_speed: 1.2, tts_workflow: 'runninghub/tts_index2.json', ref_audio: '', voxcpm_cfg: 2.0,
  voxcpm_normalize: false, voxcpm_denoise: false,
  voxcpm_control_instruction: '', voxcpm_use_prompt_text: false,
  voxcpm_prompt_text: '担心海关查验会把你的心爱宝贝弄坏。真实情况是，海关比你想象的要专业，但也确实会有痕迹。',
  image_service_mode: 'runninghub', image_api_model: '',
  video_service_mode: 'runninghub', video_api_model: '',
  video_api_params: { duration: 10, resolution: '1280x720', aspect_ratio: '9:16', negative_prompt: '', watermark: false },
  subtitle_enabled: false,
  subtitle_config: { enabled: false, font_size: 56, font_color: '#FFFFFF', font_family: 'NotoSansSC-Bold', font_weight: 400, position_x: 0, position_y: -390, max_width: 900, letter_spacing: 3, background_color: '#000000', background_opacity: 0, background_padding: '12px 24px', background_radius: 8, font_border_width: 1, font_border_color: '#000000' },
  internet_clip_enabled: true,
  title_overlay_config: { enabled: false, text: '', font_size: 56, font_color: '#FFFFFF', font_family: 'NotoSansSC-Bold', font_weight: 400, position_x: 0, position_y: -390, max_width: 900, letter_spacing: 3, font_border_width: 1, font_border_color: '#000000', background_color: '#000000', background_opacity: 0, background_padding: '12px 24px', background_radius: 8, text_align: 'center', display_mode: 'full', duration_seconds: 5 },
  business_card_config: { enabled: false, title: '', subtitle: '', display_mode: 'duration', duration_seconds: 2 },
  bgm_config: { enabled: false, selected_bgm: null, volume: 15, custom_bgm: null },
  pip_mix_config: { enabled: false, overlay_video: null, overlay_image: null, position_x: 0, position_y: 0, width: 320, height: 568, opacity: 1.0 },
})

const historyVisible = ref(false)
const historyLoading = ref(false)
const historyRecords = ref<any[]>([])
const historyFilterCategory = ref<string | undefined>(undefined)

const currentAssets = computed<string[]>(() => {
  return [digitalForm.value.character_asset, digitalForm.value.ref_audio].filter((x): x is string => !!x)
})

async function handleUpload(rawFile: File, category: string, target?: string) {
  const result = await uploadResource(rawFile, category, target)
  if (result) {
    if (target === 'digital_character') digitalForm.value.character_asset = result.path
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
  else if (cat === 'character_image') digitalForm.value.character_asset = record.path
  historyVisible.value = false
  historyFilterCategory.value = undefined
  ElMessage.success(`已选择：${record.name}`)
}

function buildPayload(): Record<string, any> {
  const payload: Record<string, any> = {}
  payload.character_assets = digitalForm.value.character_asset ? [digitalForm.value.character_asset] : []
  payload.goods_assets = []
  payload.mode = digitalForm.value.mode
  payload.goods_text = digitalForm.value.goods_text
  payload.estimated_seconds = estimatedSeconds.value
  payload.workflow_config = { ...digitalForm.value.workflow_config }
  payload.workflow_config.second_workflow_path = getVideoWorkflowPath()
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
  payload.subtitle_config = digitalForm.value.subtitle_config.enabled ? { ...digitalForm.value.subtitle_config } : { enabled: false }
  payload.title_overlay_config = digitalForm.value.title_overlay_config.enabled ? { ...digitalForm.value.title_overlay_config } : { enabled: false, text: '' }
  payload.business_card_config = digitalForm.value.business_card_config.enabled ? { ...digitalForm.value.business_card_config } : { enabled: false }
  payload.bgm_config = digitalForm.value.bgm_config.enabled ? { ...digitalForm.value.bgm_config } : { enabled: false }
  return payload
}

async function generate() {
  submitMessage.value = ''
  submitSuccess.value = false

  // 余额校验
  if (estimatedSeconds.value > 0 && auth.zsBalance.value < estimatedCost.value) {
    submitMessage.value = `ZS币不足（当前 ${auth.zsBalance.value}，需要 ${estimatedCost.value}），请先充值`
    return
  }
  if (digitalForm.value.tts_inference_mode === 'comfyui' && !digitalForm.value.ref_audio) {
    submitMessage.value = '克隆声音模式，请上传参考音频'; return
  }
  if (!digitalForm.value.character_asset) {
    submitMessage.value = '请上传角色图片'; return
  }

  const payload = buildPayload()
  payload.mode = digitalForm.value.mode
  payload.goods_text = digitalForm.value.goods_text

  try {
    const usage = await auth.fetchUsage()
    if (!usage.is_unlimited && usage.remaining <= 0) {
      submitMessage.value = '今日生成次数已用完，请明天再试或升级会员'
      return
    }
  } catch (e: any) {
    console.warn('查询每日使用量失败，跳过前端预检', e)
  }

  try {
    await submitTask('/api/pipelines/digital-human/async', payload)
    // 提交成功后清空文案，允许继续提交
    digitalForm.value.goods_text = ''
    submitSuccess.value = true
    submitMessage.value = '提交成功'
    // 刷新余额
    auth.fetchMe().catch(() => {})
  } catch (e: any) {
    submitMessage.value = e?.message || '提交失败'
  }
}

async function cancelAllTasks() {
  if (currentTaskId.value) {
    await cancelCurrentTask()
  }
}
</script>

<style scoped>
.page-generate {
  position: sticky;
  top: 20px;
  align-self: start;
  z-index: 10;
}
.cost-preview {
  padding: 12px;
  background: rgba(255,255,255,0.04);
  border-radius: 8px;
  margin-bottom: 12px;
  border: 1px solid rgba(255,255,255,0.08);
}
.cost-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  padding: 4px 0;
  color: #ccc;
}
</style>