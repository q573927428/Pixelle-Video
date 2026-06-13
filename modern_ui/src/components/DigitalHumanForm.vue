<template>
  <el-form label-position="top" class="form-sections">
    <!-- ====== 第四板块：生成模式 ====== -->
    <div class="form-section-wrapper">
      <div class="form-section">
      <div class="form-section-title">💫 选择生成模式</div>
      <div class="form-section-body">
      
      <!-- 模式选择：始终可见 -->
      <el-form-item label="模式">
        <el-radio-group v-model="form.mode">
          <el-radio-button value="customize">🧐 自定义模式</el-radio-button>
          <el-radio-button value="digital">💻 带货模式</el-radio-button>
        </el-radio-group>
      </el-form-item>

      <!-- 批量模式切换 -->
      <el-form-item label="批量模式">
        <el-switch
          v-model="form.batch_mode"
          active-text="批量生成（多组数据逐个生成）"
          inactive-text="单次生成"
        />
      </el-form-item>

      <!-- ====== 批量模式：多组数据输入 ====== -->
      <template v-if="form.batch_mode">
        <!-- 批量-带货模式 -->
        <template v-if="form.mode === 'digital'">
          <el-alert
            title="每行输入一个商品主题/标题，按顺序对应商品图片（可选）"
            type="info"
            :closable="false"
            show-icon
            style="margin-bottom:14px;"
          />
          <el-form-item label="商品主题列表（每行一个）">
            <el-input
              v-model="form.batch_topics"
              type="textarea"
              :rows="8"
              placeholder="智能保温杯&#10;无线蓝牙耳机&#10;便携式咖啡机&#10;..."
            />
          </el-form-item>
          <div v-if="batchTopicsCount > 0" class="soft-panel">
            <el-tag type="success">共 {{ batchTopicsCount }} 个主题</el-tag>
            <div class="small muted" style="margin-top:6px;">
              商品标题使用主题名称，文案由 AI 自动生成。
              可上传多张商品图片，按顺序与主题一一对应；少于主题数时最后一张循环使用。
            </div>
          </div>
          <el-form-item label="商品图片（按顺序一一对应）">
            <div class="upload-field-container">
              <UploadBox category="goods_image" accept="image/*" @upload="(f, c) => $emit('upload', f, c, 'digital_batch_goods')" @select-history="(c) => $emit('select-history', c)" />
            </div>
            <div v-if="form.batch_goods_assets.length > 0" style="width:100%;">
              <div class="small muted" style="margin-bottom:6px;">
                已上传 {{ form.batch_goods_assets.length }} 张商品图片
              </div>
              <FilePreview :items="form.batch_goods_assets" @remove="(idx) => form.batch_goods_assets.splice(idx, 1)" />
            </div>
          </el-form-item>
        </template>

        <!-- 批量-自定义模式 -->
        <template v-if="form.mode === 'customize'">
          <el-alert
            title="每行输入一段固定口播文案，系统逐行生成数字人视频"
            type="warning"
            :closable="false"
            show-icon
            style="margin-bottom:14px;"
          />
          <el-form-item label="口播文案列表（每行一段）">
            <el-input
              v-model="form.batch_topics"
              type="textarea"
              :rows="10"
              placeholder="这件商品真的太好用了，推荐给大家。&#10;今天给大家带来一款超实用的产品，看完你就懂了。&#10;你可能不知道，这款产品还有这么多隐藏功能。&#10;..."
            />
          </el-form-item>
          <div v-if="batchTopicsCount > 0" class="soft-panel">
            <el-tag type="success">共 {{ batchTopicsCount }} 段文案</el-tag>
            <div class="small muted" style="margin-top:6px;">每段文案对应一个口播视频</div>
          </div>
        </template>
      </template>

      <!-- ====== 单次模式：常规输入 ====== -->
      <template v-if="!form.batch_mode">
        <!-- 带货模式 -->
        <div v-if="form.mode === 'digital'" class="soft-panel">
          <el-form-item label="商品图片">
            <div class="upload-field-container">
              <UploadBox category="goods_image" accept="image/*" @upload="(f, c) => $emit('upload', f, c, 'digital_goods')" @select-history="(c) => $emit('select-history', c)" />
              <FilePreview v-if="form.goods_asset" :items="[form.goods_asset]" @remove="form.goods_asset = null" />
            </div>
          </el-form-item>
          <el-form-item label="商品标题">
            <el-input v-model="form.goods_title" placeholder="例如：智能保温杯" />
          </el-form-item>
          <el-form-item label="口播文案（可留空自动生成）">
            <el-input v-model="form.goods_text" type="textarea" :rows="5" placeholder="可填写固定口播文案；留空时 AI 自动根据商品标题生成" />
          </el-form-item>
        </div>

        <!-- 自定义模式 -->
        <div v-if="form.mode === 'customize'" class="soft-panel">
          <el-form-item label="自定义口播文案">
            <el-input v-model="form.goods_text" type="textarea" :rows="6" placeholder="填写固定口播文案内容" />
          </el-form-item>
        </div>
      </template>
    </div>
      </div>
    </div>

    <!-- ====== 第二板块：配音合成 ====== -->
    <div class="form-section-wrapper">
      <div class="form-section">
      <div class="form-section-title">🎤 配音合成</div>
      <div class="form-section-body">
      <el-form-item label="TTS 模式">
        <el-radio-group v-model="form.tts_inference_mode">
          <el-radio-button value="local">本地</el-radio-button>
          <el-radio-button value="comfyui">ComfyUI</el-radio-button>
        </el-radio-group>
      </el-form-item>

      <!-- 本地模式：可切换 Edge TTS / VoxCPM API -->
      <div v-if="form.tts_inference_mode === 'local'" class="soft-panel">
        <el-form-item label="本地 TTS 引擎">
          <el-radio-group v-model="form.tts_engine">
            <el-radio-button value="edge_tts">Edge TTS（默认）</el-radio-button>
            <el-radio-button value="voxcpm_api">VoxCPM API（在线）</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <!-- Edge TTS 选项 -->
        <div v-if="form.tts_engine === 'edge_tts'">
          <el-form-item label="音色选择">
            <el-select v-model="form.tts_voice" filterable placeholder="选择 TTS 音色" style="width:100%;">
              <el-option
                v-for="voice in ttsVoices"
                :key="voice.id"
                :label="`${voice.name} (${voice.locale}${voice.gender ? ' · ' + voice.gender : ''})`"
                :value="voice.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="语速">
            <el-slider v-model="form.tts_speed" :min="0.5" :max="2.0" :step="0.1" show-input />
          </el-form-item>
        </div>

        <!-- VoxCPM API 选项 -->
        <div v-if="form.tts_engine === 'voxcpm_api'" class="voxcpm-section">
          <!-- <el-form-item label="CFG 强度">
            <el-slider v-model="form.voxcpm_cfg" :min="1.0" :max="3.0" :step="0.1" show-input />
          </el-form-item> -->
          <!-- <el-form-item label="控制指令">
            <el-input v-model="form.voxcpm_control_instruction" placeholder="例如：自然、温柔" />
          </el-form-item> -->
          <!-- <div class="checkbox-row">
            <el-checkbox v-model="form.voxcpm_normalize">归一化 Normalize</el-checkbox>
            <el-checkbox v-model="form.voxcpm_denoise">降噪 Denoise</el-checkbox>
          </div> -->
          <el-form-item label="参考音频">
            <div class="upload-field-container">
              <UploadBox category="ref_audio" accept="audio/*" @upload="(f, c) => $emit('upload', f, c, 'digital_ref_audio')" @select-history="(c) => $emit('select-history', c)" />
              <FilePreview v-if="form.ref_audio" :items="refAudioItems" @remove="form.ref_audio = ''" />
            </div>
          </el-form-item>
          <div v-if="form.ref_audio" class="soft-panel">
            <el-checkbox v-model="form.voxcpm_use_prompt_text">启用 Prompt Text</el-checkbox>
            <el-form-item v-if="form.voxcpm_use_prompt_text" label="Prompt Text">
              <div style="position:relative;width:100%;">
                <el-input
                  v-model="form.voxcpm_prompt_text"
                  type="textarea"
                  :rows="2"
                  placeholder="参考音频的文字内容"
                  style="width:100%;"
                />
                <el-button
                  circle
                  type="primary"
                  size="small"
                  @click="handleAsrTranscribe"
                  :loading="asrLoading"
                  :disabled="!form.ref_audio"
                  style="position:absolute;bottom:6px;right:6px;z-index:1;"
                >
                  🎙️
                </el-button>
              </div>
            </el-form-item>
          </div>
        </div>
      </div>

      <!-- ComfyUI 模式 -->
      <div v-if="form.tts_inference_mode === 'comfyui'" class="soft-panel">
        <el-form-item label="TTS 工作流">
          <el-select v-model="form.tts_workflow" filterable clearable placeholder="选择 TTS 工作流" style="width:100%;">
            <el-option v-for="wf in ttsWorkflows" :key="wf.key" :label="wf.display_name" :value="wf.key" />
          </el-select>
        </el-form-item>
        <el-form-item label="参考音频">
          <div class="upload-field-container">
             <UploadBox category="ref_audio" accept="audio/*" @upload="(f, c) => $emit('upload', f, c, 'digital_ref_audio')" @select-history="(c) => $emit('select-history', c)" />
            <FilePreview v-if="form.ref_audio" :items="refAudioItems" @remove="form.ref_audio = ''" />
          </div>
        </el-form-item>
      </div>

      <!-- 声音预览（默认折叠） -->
      <el-collapse v-model="previewActiveNames" style="margin-top:12px;">
        <el-collapse-item name="voice-preview">
          <template #title>
            <span style="font-size:13px;font-weight:500;color:var(--el-color-primary);">🔊 声音预览</span>
          </template>
          <el-input v-model="previewText" type="textarea" :rows="2" placeholder="大家好，这是一段测试语音。" style="margin-bottom:8px;" />
          <div style="display:flex;gap:10px;align-items:center;">
            <el-button type="primary" @click="handlePreviewTts" :loading="previewLoading">
              ▶ 生成预览
            </el-button>
            <audio v-if="previewAudioUrl" :src="previewAudioUrl" controls style="height:32px;flex:1;min-width:0;" />
          </div>
        </el-collapse-item>
      </el-collapse>
    </div>
      </div>
    </div>

    <!-- ====== 第一板块：人物形象上传 ====== -->
    <div class="form-section-wrapper">
      <div class="form-section">
      <div class="form-section-title">🧑 人物形象上传</div>
      <div class="form-section-body">
      <el-form-item label="角色图片">
        <div class="upload-field-container">
          <UploadBox category="character_image" accept="image/*" @upload="(f, c) => $emit('upload', f, c, 'digital_character')" @select-history="(c) => $emit('select-history', c)" />
          <FilePreview v-if="form.character_asset" :items="[form.character_asset]" @remove="form.character_asset = null" />
        </div>
      </el-form-item>
    </div>
      </div>
    </div>

    <!-- ====== 第三板块：服务配置 ====== -->
    <div class="form-section-wrapper">
      <div class="form-section">
      <div class="form-section-title">⚙️ 服务配置</div>
      <div class="form-section-body">

      <!-- 3.1 前置图片生成服务 -->
      <div class="sub-section">
        <div class="sub-section-title">3.1 前置图片生成服务来源</div>
        <el-form-item >
          <el-radio-group v-model="form.image_service_mode">
            <el-radio-button value="runninghub">☁️ RunningHub（云端）</el-radio-button>
            <el-radio-button value="api">API 模型</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <!-- RunningHub 模式 -->
        <div v-if="form.image_service_mode === 'runninghub'" class="soft-panel">
          <el-form-item label="工作流">
            <el-select v-model="form.workflow_config.first_workflow_path" filterable placeholder="选择 RunningHub 工作流" style="width:100%;">
              <el-option
                v-for="wf in imageWorkflows"
                :key="wf.key"
                :label="wf.display_name"
                :value="wf.key"
              />
            </el-select>
          </el-form-item>
        </div>

        <!-- API 模型模式 -->
        <div v-if="form.image_service_mode === 'api'" class="soft-panel">
          <el-form-item label="API 模型">
            <el-select v-model="form.image_api_model" filterable placeholder="选择 API 图片模型" style="width:100%;">
              <el-option label="wan2.7-image - API Dashscope" value="dashscope/wan2.7-image" />
              <el-option label="wan2.7-image-pro - API Dashscope" value="dashscope/wan2.7-image-pro" />
              <el-option label="wan2.6-t2i - API Dashscope" value="dashscope/wan2.6-t2i" />
              <el-option label="gpt-image-2 - API OpenAI" value="openai/gpt-image-2" />
              <el-option label="doubao-seedream-5-0-260128 - API Seedream" value="seedream/doubao-seedream-5-0-260128" />
              <el-option label="doubao-seedream-4-5-251128 - API Seedream" value="seedream/doubao-seedream-4-5-251128" />
              <el-option label="doubao-seedream-4-0-250828 - API Seedream" value="seedream/doubao-seedream-4-0-250828" />
            </el-select>
          </el-form-item>
        </div>
      </div>

      <!-- 3.2 口播视频合成服务 -->
      <div class="sub-section">
        <div class="sub-section-title">3.2 口播视频合成服务来源</div>
        <el-form-item>
          <el-radio-group v-model="form.video_service_mode">
            <el-radio-button value="runninghub">☁️ RunningHub（云端）</el-radio-button>
            <el-radio-button value="api">API 模型</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <!-- RunningHub 模式 -->
        <div v-if="form.video_service_mode === 'runninghub'" class="soft-panel">
          <el-form-item label="工作流">
            <el-select v-model="form.workflow_config.second_workflow_path" filterable placeholder="选择 RunningHub 工作流" style="width:100%;">
              <el-option
                v-for="wf in videoWorkflows"
                :key="wf.key"
                :label="wf.display_name"
                :value="wf.key"
              />
            </el-select>
          </el-form-item>
        </div>

        <!-- API 模型模式 -->
        <div v-if="form.video_service_mode === 'api'" class="soft-panel">
          <el-form-item label="API 模型">
            <el-select v-model="form.video_api_model" filterable placeholder="选择 API 视频模型" style="width:100%;">
              <el-option label="wan2.7-r2v - API Dashscope" value="dashscope/wan2.7-r2v" />
              <el-option label="happyhorse-1.0-r2v - API Dashscope" value="dashscope/happyhorse-1.0-r2v" />
            </el-select>
          </el-form-item>

          <el-collapse v-model="videoApiParamsActiveNames" style="margin-top:12px;">
            <el-collapse-item name="video-api-params">
              <template #title>
                <span class="sub-section-title" style="font-size:13px;">API 视频模型参数</span>
              </template>
              <el-form-item label="已接入能力">
                <el-tag type="info">digital_human</el-tag>
                <el-tag type="info" style="margin-left:6px;">reference_to_video</el-tag>
                <el-tag type="info" style="margin-left:6px;">voice_reference</el-tag>
              </el-form-item>
              <el-form-item label="视频时长（秒）">
                <el-input-number v-model="form.video_api_params.duration" :min="5" :max="15" :step="1" style="width:100%;" />
              </el-form-item>
              <el-form-item label="分辨率">
                <el-select v-model="form.video_api_params.resolution" filterable placeholder="选择分辨率" style="width:100%;">
                  <el-option label="720P（默认）" value="1280x720" />
                  <el-option label="1080P" value="1920x1080" />
                </el-select>
              </el-form-item>
              <el-form-item label="画幅比例">
                <el-select v-model="form.video_api_params.aspect_ratio" filterable placeholder="选择画幅比例" style="width:100%;">
                  <el-option label="9:16（默认）" value="9:16" />
                  <el-option label="16:9" value="16:9" />
                  <el-option label="1:1" value="1:1" />
                  <el-option label="4:3" value="4:3" />
                  <el-option label="3:4" value="3:4" />
                </el-select>
              </el-form-item>
              <el-form-item label="负向提示词（可选）">
                <el-input v-model="form.video_api_params.negative_prompt" type="textarea" :rows="2" placeholder="输入不希望出现的内容" />
              </el-form-item>
              <el-form-item>
                <el-checkbox v-model="form.video_api_params.watermark">添加水印</el-checkbox>
              </el-form-item>
            </el-collapse-item>
          </el-collapse>
        </div>
      </div>
    </div>
      </div>
    </div>

  </el-form>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { DigitalForm, WorkflowInfo, TtsVoiceInfo } from '../types'
import { request, filePreviewUrl } from '../api'
import UploadBox from './UploadBox.vue'
import FilePreview from './FilePreview.vue'
import { ElMessage } from 'element-plus'

const props = defineProps<{
  form: DigitalForm
  uploads: any[]
  mediaWorkflows: WorkflowInfo[]
  ttsWorkflows: WorkflowInfo[]
  ttsVoices: TtsVoiceInfo[]
}>()

const refAudioItems = computed<string[]>(() => {
  return props.form.ref_audio ? [props.form.ref_audio] : []
})

// 批量模式：计算主题数量
const batchTopicsCount = computed(() => {
  if (!props.form.batch_topics || !props.form.batch_topics.trim()) return 0
  return props.form.batch_topics.trim().split('\n').filter(line => line.trim()).length
})

// 从 mediaWorkflows 中过滤出图片生成相关的工作流（来源为 runninghub）
const imageWorkflows = computed<WorkflowInfo[]>(() => {
  return props.mediaWorkflows.filter(wf => {
    const key = (wf.key || wf.path || '').toLowerCase()
    return wf.source === 'runninghub' && (key.includes('image') || key.includes('digital_image'))
  })
})

// 从 mediaWorkflows 中过滤出口播视频合成相关的工作流（来源为 runninghub）
const videoWorkflows = computed<WorkflowInfo[]>(() => {
  return props.mediaWorkflows.filter(wf => {
    const key = (wf.key || wf.path || '').toLowerCase()
    return wf.source === 'runninghub' && (key.includes('combination') || key.includes('digital_combination') || key.includes('video'))
  })
})

const emit = defineEmits<{
  (e: 'upload', file: File, category: string, target: string): void
  (e: 'select-history', category: string): void
}>()

// 批量模式下不强制切换模式，两种模式都支持
function onBatchModeChange(val: boolean) {
  // 不需要额外操作，保持当前 mode 不变
}

const videoApiParamsActiveNames = ref<string[]>([])

const previewActiveNames = ref<string[]>([])
const asrLoading = ref(false)

// 声音预览
const previewText = ref('大家好，这是一段测试语音。')
const previewLoading = ref(false)
const previewAudioUrl = ref('')

async function handlePreviewTts() {
  if (!previewText.value.trim()) {
    ElMessage.warning('请输入预览文本')
    return
  }
  previewLoading.value = true
  previewAudioUrl.value = ''
  try {
    const params: Record<string, any> = { text: previewText.value.trim() }
    
    if (props.form.tts_inference_mode === 'local') {
      if (props.form.tts_engine === 'voxcpm_api') {
        // VoxCPM API: 直接调用 VoxCPM，不走 ComfyUI/workflow
        params.engine = 'voxcpm_api'
        if (props.form.voxcpm_cfg) params.cfg = props.form.voxcpm_cfg
        if (props.form.voxcpm_normalize) params.normalize = true
        if (props.form.voxcpm_denoise) params.denoise = true
        if (props.form.voxcpm_control_instruction) params.control_instruction = props.form.voxcpm_control_instruction
        if (props.form.voxcpm_use_prompt_text) {
          params.use_prompt_text = true
          if (props.form.voxcpm_prompt_text) params.prompt_text = props.form.voxcpm_prompt_text
        }
        if (props.form.ref_audio) {
          params.ref_audio = props.form.ref_audio
        }
      } else {
        // Edge TTS: 使用 voice_id 选择音色
        params.voice_id = props.form.tts_voice
      }
    } else if (props.form.tts_inference_mode === 'comfyui') {
      // ComfyUI: 传 TTS 工作流 + voice_id + 参考音频(可选)
      if (props.form.tts_workflow) {
        params.workflow = props.form.tts_workflow
      }
      params.voice_id = props.form.tts_voice
      if (props.form.ref_audio) {
        params.ref_audio = props.form.ref_audio
      }
    }
    
    const res: any = await request('/api/tts/synthesize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    })
    if (res.audio_path) {
      // 如果返回的是 HTTP URL（远程文件），直接使用；否则通过 filePreviewUrl 转本地路径
      if (res.audio_path.startsWith('http://') || res.audio_path.startsWith('https://')) {
        previewAudioUrl.value = res.audio_path
      } else {
        previewAudioUrl.value = filePreviewUrl(res.audio_path)
      }
    }
    ElMessage.success('预览语音生成成功')
  } catch (e: any) {
    ElMessage.error(`生成失败：${e.message}`)
  } finally {
    previewLoading.value = false
  }
}

async function handleAsrTranscribe() {
  if (!props.form.ref_audio) return
  asrLoading.value = true
  try {
    const res: any = await request('/api/audio/asr', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ audio_path: props.form.ref_audio }),
    })
    props.form.voxcpm_prompt_text = res.text || ''
    ElMessage.success('语音转文字完成')
  } catch (e: any) {
    ElMessage.error(`转写失败：${e.message}`)
  } finally {
    asrLoading.value = false
  }
}
</script>

<style scoped>
</style>
