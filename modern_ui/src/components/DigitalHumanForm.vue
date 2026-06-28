<template>
  <el-form label-position="top" class="form-sections">
    <!-- ====== 左列 ====== -->
    <div class="form-column">

      <!-- ====== 第一板块：人物形象上传 ====== -->
      <div class="form-section-wrapper">
        <div class="form-section">
        <div class="form-section-title">🧑 人物上传</div>
        <div class="form-section-body">
          <el-form-item label="角色图片">
            <div class="upload-field-container">
              <UploadBox category="character_image" accept="image/*,.heic,.heif" @upload="(f, c) => $emit('upload', f, c, 'digital_character')" @select-history="(c) => $emit('select-history', c)" />
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
        <el-form-item>
          <el-radio-group v-model="form.tts_inference_mode">
            <el-radio-button value="comfyui">克隆声音</el-radio-button>
            <el-radio-button value="local">内置语音</el-radio-button>
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
                  :label="voice.name"
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
            <el-form-item label="CFG 强度" v-if="false">
              <el-slider v-model="form.voxcpm_cfg" :min="1.0" :max="3.0" :step="0.1" show-input />
            </el-form-item>
            <el-form-item label="控制指令" v-if="false">
              <el-input v-model="form.voxcpm_control_instruction" placeholder="例如：自然、温柔" />
            </el-form-item>
            <div class="checkbox-row" v-if="false">
              <el-checkbox v-model="form.voxcpm_normalize">归一化 Normalize</el-checkbox>
              <el-checkbox v-model="form.voxcpm_denoise">降噪 Denoise</el-checkbox>
            </div>
              <el-form-item label="参考音频">
              <div class="upload-field-container">
                <UploadBox category="ref_audio" accept="audio/*,.amr" @upload="(f, c) => $emit('upload', f, c, 'digital_ref_audio')" @select-history="(c) => $emit('select-history', c)" />
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
          <el-form-item label="TTS 工作流" v-if="false">
            <el-select v-model="form.tts_workflow" filterable clearable placeholder="选择 TTS 工作流" style="width:100%;">
              <el-option v-for="wf in ttsWorkflows" :key="wf.key" :label="wf.display_name" :value="wf.key" />
            </el-select>
          </el-form-item>
          <el-form-item label="参考音频">
            <div class="upload-field-container">
               <UploadBox category="ref_audio" accept="audio/*,.amr" @upload="(f, c) => $emit('upload', f, c, 'digital_ref_audio')" @select-history="(c) => $emit('select-history', c)" />
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
            <el-input v-model="previewText" type="textarea" :rows="2" placeholder="大家好，这是一段测试语音。" :maxlength="30" show-word-limit style="margin-bottom:8px;" />
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

    </div>

    <!-- ====== 右列 ====== -->
    <div class="form-column">

      <!-- ====== 第三板块：生成模式 ====== -->
      <div class="form-section-wrapper">
        <div class="form-section">
        <div class="form-section-title">💫 选择生成模式</div>
        <div class="form-section-body">

        <!-- 模式选择：始终可见 -->
        <el-form-item label="模式">
          <el-radio-group v-model="form.mode">
            <el-radio-button value="customize">🧐 口播模式</el-radio-button>
            <el-radio-button value="digital">💻 带货模式</el-radio-button>
          </el-radio-group>
        </el-form-item>

          <!-- 带货模式 -->
          <div v-if="form.mode === 'digital'" class="soft-panel">
            <el-form-item label="商品图片">
              <div class="upload-field-container">
                <UploadBox category="goods_image" accept="image/*,.heic,.heif" @upload="(f, c) => $emit('upload', f, c, 'digital_goods')" @select-history="(c) => $emit('select-history', c)" />
                <FilePreview v-if="form.goods_asset" :items="[form.goods_asset]" @remove="form.goods_asset = null" />
              </div>
            </el-form-item>
            <el-form-item label="商品标题">
              <el-input v-model="form.goods_title" placeholder="例如：智能保温杯" :maxlength="30" show-word-limit />
            </el-form-item>
            <el-form-item label="口播文案（可留空自动生成）">
              <el-input v-model="form.goods_text" type="textarea" :rows="5" maxlength="500" show-word-limit placeholder="可填写固定口播文案；留空时 AI 自动根据商品标题生成" />
            </el-form-item>
          </div>

          <!-- 自定义模式 -->
          <div v-if="form.mode === 'customize'" class="soft-panel">
            <el-form-item label="自定义口播文案">
              <el-input v-model="form.goods_text" type="textarea" :rows="6" maxlength="500" show-word-limit placeholder="填写固定口播文案内容" />
              <div style="margin-top:8px;display:flex;gap:8px;justify-content:flex-end;">
                <el-button v-if="form.goods_text.trim()" type="warning" size="small" @click="handleRewrite" :loading="rewriteLoading">
                  ✨ 一键改写
                </el-button>
                <el-button type="primary" size="small" @click="mediaDialogVisible = true">
                  🎵 从短视频链接提取
                </el-button>
              </div>
            </el-form-item>
          </div>

          <!-- 短视频导入弹窗 -->
          <el-dialog v-model="mediaDialogVisible" title="从短视频导入口播文案" :close-on-click-modal="false" class="media-dialog">
            <div style="margin-bottom:12px;font-size:13px;color:var(--el-text-color-secondary);">
              粘贴抖音/快手/小红书/B站等短视频分享信息，系统将自动提取视频中的口播文案。
            </div>
            <el-input
              v-model="mediaShareText"
              type="textarea"
              :rows="8"
              placeholder="粘贴短视频分享链接/信息&#10;&#10;支持：抖音、快手、小红书、B站&#10;例如：https://v.douyin.com/OOgNGe6Ln20/"
            />
            <template #footer>
              <el-button @click="handlePasteFromClipboard">📋 粘贴</el-button>
              <el-button @click="mediaDialogVisible = false">取消</el-button>
              <el-button
                type="primary"
                @click="handleMediaParse"
                :loading="mediaLoading"
                :disabled="!mediaShareText.trim()"
              >
                解析并导入
              </el-button>
            </template>
          </el-dialog>
      </div>
        </div>
      </div>

      <!-- ====== 第四板块：服务配置（注释保留） ====== -->
      <div class="form-section-wrapper" v-if="false">
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
      <!-- ====== 网感剪辑 ====== -->
      <div class="form-section-wrapper">
        <div class="form-section">
          <div class="form-section-title" style="display:flex;justify-content:space-between;align-items:center;">
            <span>🎬 网感剪辑</span>
            <div style="display:flex;align-items:center;gap:6px;">
              <span style="font-size:13px;font-weight:400;">开关</span>
              <el-switch
                :model-value="form.internet_clip_enabled"
                @update:model-value="form.internet_clip_enabled = $event"
              />
            </div>
          </div>
          <div class="form-section-body" v-if="form.internet_clip_enabled">
            <!-- 字幕配置 -->
            <div style="margin-bottom:16px;">
              <SubtitleConfigurator
                :enabled="form.subtitle_enabled"
                :config="form.subtitle_config"
                :preview-text="form.goods_text"
                @update:enabled="form.subtitle_enabled = $event"
                @update:config="form.subtitle_config = $event"
              />
            </div>
            <!-- 标题叠加 -->
            <div style="margin-bottom:16px;">
              <TitleOverlayConfigurator
                :enabled="form.title_overlay_config.enabled"
                :config="form.title_overlay_config"
                @update:enabled="form.title_overlay_config.enabled = $event"
                @update:config="form.title_overlay_config = $event"
              />
            </div>
            <!-- 个人名片 -->
            <div style="margin-bottom:16px;">
              <BusinessCardConfigurator
                :enabled="form.business_card_config.enabled"
                :config="form.business_card_config"
                @update:enabled="form.business_card_config.enabled = $event"
                @update:config="form.business_card_config = $event"
              />
            </div>
            <!-- 背景音乐 -->
            <div style="margin-bottom:16px;">
              <BgmConfigurator
                :enabled="form.bgm_config.enabled"
                :config="form.bgm_config"
                :bgm-list="bgmList"
                @update:enabled="form.bgm_config.enabled = $event"
                @update:config="form.bgm_config = $event"
                @upload="(f, c, t) => $emit('upload', f, c, t)"
                @select-history="(c) => $emit('select-history', c)"
              />
            </div>
            <!-- 画中画混剪（最后一项不需要底部间距） -->
            <PipMixConfigurator
              :enabled="form.pip_mix_config.enabled"
              :config="form.pip_mix_config"
              @update:enabled="form.pip_mix_config.enabled = $event"
              @update:config="form.pip_mix_config = $event"
              @upload="(f, c, t) => $emit('upload', f, c, t)"
              @select-history="(c) => $emit('select-history', c)"
            />
          </div>
        </div>
      </div>
    </div>
  </el-form>
</template>

<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'
import type { DigitalForm, WorkflowInfo, TtsVoiceInfo, BgmInfo } from '../types'
import { request, filePreviewUrl } from '../api'
import UploadBox from './UploadBox.vue'
import FilePreview from './FilePreview.vue'
import SubtitleConfigurator from './SubtitleConfigurator.vue'
import TitleOverlayConfigurator from './TitleOverlayConfigurator.vue'
import BusinessCardConfigurator from './BusinessCardConfigurator.vue'
import BgmConfigurator from './BgmConfigurator.vue'
import PipMixConfigurator from './PipMixConfigurator.vue'
import { ElMessage } from 'element-plus'

const props = defineProps<{
  form: DigitalForm
  mediaWorkflows: WorkflowInfo[]
  ttsWorkflows: WorkflowInfo[]
  ttsVoices: TtsVoiceInfo[]
  bgmList: BgmInfo[]
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

const emit = defineEmits<{
  (e: 'upload', file: File, category: string, target: string): void
  (e: 'select-history', category: string): void
}>()

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

// ---- AI 一键改写 ----
const rewriteLoading = ref(false)

async function handleRewrite() {
  const text = props.form.goods_text?.trim()
  if (!text) {
    ElMessage.warning('请输入要改写的文案')
    return
  }
  rewriteLoading.value = true
  try {
    const prompt = `请改写以下口播文案，保持原意不变，使表达更流畅自然、更有吸引力，直接返回改写后的文案，不要多余的解释：\n\n${text}`
    const res: any = await request('/api/llm/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt, temperature: 0.7, max_tokens: 1024 }),
    })
    if (res.content) {
      props.form.goods_text = res.content.trim().slice(0, 500)
      ElMessage.success('改写完成')
    } else {
      ElMessage.warning('改写失败，请重试')
    }
  } catch (e: any) {
    ElMessage.error(`改写失败：${e.message}`)
  } finally {
    rewriteLoading.value = false
  }
}

// ---- 剪贴板粘贴 ----
async function handlePasteFromClipboard() {
  try {
    const text = await navigator.clipboard.readText()
    if (text) {
      mediaShareText.value = text
      ElMessage.success('已粘贴剪贴板内容')
      return
    }
  } catch {
    // Clipboard API 不可用（非 HTTPS/非 localhost 环境）
  }
  // 聚焦输入框，提示用户按 Ctrl+V 粘贴
  ElMessage.info('请点击输入框后按 Ctrl+V 粘贴')
  nextTick(() => {
    const el = document.querySelector('.media-dialog textarea') as HTMLTextAreaElement
    el?.focus()
  })
}

// ---- 短视频导入口播文案 ----
const mediaDialogVisible = ref(false)
const mediaShareText = ref('')
const mediaLoading = ref(false)

async function handleMediaParse() {
  if (!mediaShareText.value.trim()) {
    ElMessage.warning('请输入短视频分享信息')
    return
  }
  mediaLoading.value = true
  try {
    const res: any = await request('/api/media/transcribe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ share_text: mediaShareText.value.trim() }),
    })
    if (res.success && res.text) {
      props.form.goods_text = res.text.slice(0, 500)
      mediaDialogVisible.value = false
      ElMessage.success('口播文案导入成功')
    } else {
      ElMessage.warning(res.message || '未能提取到有效口播文案')
    }
  } catch (e: any) {
    ElMessage.error(`导入失败：${e.message}`)
  } finally {
    mediaLoading.value = false
  }
}
</script>

<style scoped>
/* 短视频导入弹窗：PC 固定 480px，手机自适应 92% */
@media (max-width: 640px) {
  :deep(.media-dialog) {
    --el-dialog-width: 92%;
  }
  :deep(.media-dialog .el-dialog) {
    width: 92% !important;
    max-width: 92vw !important;
  }
}
</style>