<template>
  <el-form label-position="top" class="form-sections">
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
          <el-form-item label="CFG 强度">
            <el-slider v-model="form.voxcpm_cfg" :min="1.0" :max="5.0" :step="0.1" show-input />
          </el-form-item>
          <el-form-item label="控制指令">
            <el-input v-model="form.voxcpm_control_instruction" placeholder="例如：自然、温柔" />
          </el-form-item>
          <div class="checkbox-row">
            <el-checkbox v-model="form.voxcpm_normalize">归一化 Normalize</el-checkbox>
            <el-checkbox v-model="form.voxcpm_denoise">降噪 Denoise</el-checkbox>
          </div>
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

      <!-- 声音预览 -->
      <div class="soft-panel" style="margin-top:12px;border:1px dashed var(--el-color-primary);">
        <el-form-item label="🔊 声音预览">
          <el-input v-model="previewText" type="textarea" :rows="2" placeholder="大家好，这是一段测试语音。" />
        </el-form-item>
        <div style="display:flex;gap:10px;align-items:center;">
          <el-button type="primary" @click="handlePreviewTts" :loading="previewLoading">
            ▶ 生成预览
          </el-button>
          <audio v-if="previewAudioUrl" :src="previewAudioUrl" controls style="height:32px;flex:1;min-width:0;" />
        </div>
      </div>
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
        <div class="sub-section-title">3.1 前置图片生成服务</div>
        <el-form-item label="图片生成服务来源">
          <el-radio-group v-model="form.image_service_mode">
            <el-radio-button value="runninghub">☁️ RunningHub（云端）</el-radio-button>
            <el-radio-button value="api">API 模型</el-radio-button>
          </el-radio-group>
          <div class="service-hint">选择前置图片生成使用的模型服务来源：RunningHub 使用云端工作流；API 调用直接请求模型供应商。</div>
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
            <div class="small muted" style="margin-top:4px;">(默认) digital_image.json - Runninghub</div>
          </el-form-item>
        </div>

        <!-- API 模型模式 -->
        <div v-if="form.image_service_mode === 'api'" class="soft-panel">
          <el-form-item label="API 模型">
            <el-select v-model="form.image_api_model" filterable placeholder="选择 API 图片模型" style="width:100%;">
              <el-option label="wan2.7-image - API Dashscope" value="wan2.7-image" />
              <el-option label="wan2.7-image-pro - API Dashscope" value="wan2.7-image-pro" />
              <el-option label="wan2.6-t2i - API Dashscope" value="wan2.6-t2i" />
              <el-option label="gpt-image-2 - API OpenAI" value="gpt-image-2" />
              <el-option label="doubao-seedream-5-0-260128 - API Seedream" value="doubao-seedream-5-0-260128" />
              <el-option label="doubao-seedream-4-5-251128 - API Seedream" value="doubao-seedream-4-5-251128" />
              <el-option label="doubao-seedream-4-0-250828 - API Seedream" value="doubao-seedream-4-0-250828" />
            </el-select>
          </el-form-item>
        </div>
      </div>

      <!-- 3.2 口播视频合成服务 -->
      <div class="sub-section">
        <div class="sub-section-title">3.2 口播视频合成服务</div>
        <el-form-item label="视频合成服务来源">
          <el-radio-group v-model="form.video_service_mode">
            <el-radio-button value="runninghub">☁️ RunningHub（云端）</el-radio-button>
            <el-radio-button value="api">API 模型</el-radio-button>
          </el-radio-group>
          <div class="service-hint">选择口播视频合成使用的模型服务来源：RunningHub 使用云端工作流；API 调用直接请求模型供应商。</div>
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
            <div class="small muted" style="margin-top:4px;">(默认) digital_combination.json - Runninghub</div>
          </el-form-item>
        </div>

        <!-- API 模型模式 -->
        <div v-if="form.video_service_mode === 'api'" class="soft-panel">
          <el-form-item label="API 模型">
            <el-select v-model="form.video_api_model" filterable placeholder="选择 API 视频模型" style="width:100%;">
              <el-option label="wan2.7-r2v - API Dashscope" value="wan2.7-r2v" />
              <el-option label="happyhorse-1.0-r2v - API Dashscope" value="happyhorse-1.0-r2v" />
            </el-select>
          </el-form-item>

          <div class="sub-section" style="margin-top:12px;">
            <div class="sub-section-title" style="font-size:13px;">API 视频模型参数</div>
            <el-form-item label="已接入能力">
              <el-tag type="info">digital_human</el-tag>
              <el-tag type="info" style="margin-left:6px;">reference_to_video</el-tag>
              <el-tag type="info" style="margin-left:6px;">voice_reference</el-tag>
            </el-form-item>
            <el-form-item label="视频时长（秒）">
              <el-input-number v-model="form.video_api_params.duration" :min="1" :max="30" :step="1" style="width:100%;" />
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
          </div>
        </div>
      </div>
    </div>
      </div>
    </div>

    <!-- ====== 第四板块：生成模式 ====== -->
    <div class="form-section-wrapper">
      <div class="form-section">
      <div class="form-section-title">💫 选择生成模式</div>
      <div class="form-section-body">
      <el-form-item label="模式">
        <el-radio-group v-model="form.mode">
          <el-radio-button value="digital">💻 带货模式</el-radio-button>
          <el-radio-button value="customize">🧐 自定义模式</el-radio-button>
        </el-radio-group>
      </el-form-item>

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
    </div>
      </div>
    </div>
  </el-form>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
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

defineEmits<{
  (e: 'upload', file: File, category: string, target: string): void
  (e: 'select-history', category: string): void
}>()

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