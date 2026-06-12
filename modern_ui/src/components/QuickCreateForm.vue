<template>
  <el-form label-position="top" class="form-sections">
    <!-- ====== 第一板块：创作模式与文案输入 ====== -->
    <div class="form-section-wrapper">
      <div class="form-section">
      <div class="form-section-title">📝 创作模式与文案输入</div>
      <div class="form-section-body">
      <el-form-item label="创作模式">
        <el-radio-group v-model="form.mode">
          <el-radio-button value="generate">AI 生成分镜</el-radio-button>
          <el-radio-button value="fixed">固定文案</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-alert
        v-if="form.mode === 'generate'"
        title="AI 生成分镜：输入主题/素材方向，由 AI 自动拆分场景、旁白和画面提示词。"
        type="info"
        :closable="false"
        show-icon
        style="margin-bottom: 14px;"
      />
      <el-alert
        v-else
        title="固定文案：直接使用输入内容作为旁白脚本，不再按主题重新扩写。"
        type="warning"
        :closable="false"
        show-icon
        style="margin-bottom: 14px;"
      />
      <el-form-item label="视频标题">
        <el-input v-model="form.title" placeholder="可留空，由 AI 自动生成" clearable />
      </el-form-item>
      <el-form-item :label="form.mode === 'generate' ? '主题 / 创作方向' : '固定旁白文案'">
        <el-input
          v-model="form.text"
          type="textarea"
          :rows="form.mode === 'generate' ? 8 : 12"
          :placeholder="form.mode === 'generate' ? '输入视频主题、卖点、风格或营销方向...' : '输入完整旁白文案，每段可换行；系统会尽量按原文生成视频...'"
        />
      </el-form-item>
      <div class="soft-panel">
        <el-form-item v-if="form.mode === 'generate'" label="分镜数量">
          <el-slider v-model="form.n_scenes" :min="1" :max="20" show-input />
        </el-form-item>
        <div v-else class="small muted" style="margin-bottom: 14px;">固定文案模式会忽略分镜数量，按输入文案组织画面。</div>
        <el-form-item label="视频帧率">
          <el-slider v-model="form.video_fps" :min="15" :max="60" :step="5" show-input />
        </el-form-item>
      </div>
    </div>
      </div>
    </div>

    <!-- ====== 第二板块：画面与媒体配置 ====== -->
    <div class="form-section-wrapper">
      <div class="form-section">
      <div class="form-section-title">🎨 画面与媒体配置</div>
      <div class="form-section-body">
      <el-form-item label="画面模板">
        <el-select v-model="form.frame_template" filterable placeholder="选择 HTML 模板" style="width:100%;">
          <el-option v-for="tpl in templates" :key="tpl.key" :label="`${tpl.display_name} · ${tpl.size}`" :value="tpl.key" />
        </el-select>
      </el-form-item>
      <el-form-item label="媒体工作流">
        <el-select v-model="form.media_workflow" filterable clearable placeholder="默认/选择图片或视频工作流" style="width:100%;">
          <el-option v-for="wf in mediaWorkflows" :key="wf.key" :label="wf.display_name" :value="wf.key" />
        </el-select>
      </el-form-item>
      <el-form-item label="图片风格前缀">
        <el-input v-model="form.prompt_prefix" type="textarea" :rows="2" placeholder="在生成图片提示词前添加固定前缀（可选）" />
      </el-form-item>
    </div>
      </div>
    </div>

    <!-- ====== 第三板块：配音合成 (TTS) ====== -->
    <div class="form-section-wrapper">
      <div class="form-section">
      <div class="form-section-title">🎤 配音合成 (TTS)</div>
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
            <el-slider v-model="form.voxcpm_cfg" :min="1" :max="3.0" :step="0.1" show-input />
          </el-form-item>
          <el-form-item label="控制指令">
            <el-input v-model="form.voxcpm_control_instruction" placeholder="例如：自然、温柔、带一点营销感" />
          </el-form-item>
          <div class="checkbox-row">
            <el-checkbox v-model="form.voxcpm_normalize">归一化 Normalize</el-checkbox>
            <el-checkbox v-model="form.voxcpm_denoise">降噪 Denoise</el-checkbox>
          </div>
          <el-form-item label="参考音频">
            <div class="upload-field-container">
              <UploadBox category="ref_audio" accept="audio/*" @upload="(f, c) => $emit('upload', f, c, 'quick_ref_audio')" @select-history="(c) => $emit('select-history', c)" />
              <FilePreview v-if="form.ref_audio" :items="refAudioItems" @remove="form.ref_audio = null" />
            </div>
          </el-form-item>
          <div v-if="form.ref_audio" class="soft-panel">
            <el-checkbox v-model="form.voxcpm_use_prompt_text">启用 Prompt Text（极致克隆模式）</el-checkbox>
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
          <el-select v-model="form.tts_workflow" filterable clearable placeholder="默认/选择 TTS 工作流" style="width:100%;">
            <el-option v-for="wf in ttsWorkflows" :key="wf.key" :label="wf.display_name" :value="wf.key" />
          </el-select>
        </el-form-item>
        <el-form-item label="参考音频（可选）">
          <div class="upload-field-container">
            <UploadBox category="ref_audio" accept="audio/*" @upload="(f, c) => $emit('upload', f, c, 'quick_ref_audio')" @select-history="(c) => $emit('select-history', c)" />
            <FilePreview v-if="form.ref_audio" :items="refAudioItems" @remove="form.ref_audio = null" />
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

    <!-- ====== 第四板块：背景音乐 ====== -->
    <div class="form-section-wrapper">
      <div class="form-section">
      <div class="form-section-title">🎵 背景音乐</div>
      <div class="form-section-body">
      <el-form-item label="背景音乐">
        <el-select v-model="form.bgm_path" clearable filterable placeholder="不使用 BGM" style="width:100%;">
          <el-option v-for="item in bgmFiles" :key="item.path" :label="item.name" :value="item.path" />
        </el-select>
      </el-form-item>
      <el-form-item label="BGM 音量">
        <el-slider v-model="form.bgm_volume" :min="0" :max="1" :step="0.05" show-input />
      </el-form-item>
    </div>
      </div>
    </div>
  </el-form>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { QuickForm, WorkflowInfo, TemplateInfo, BgmInfo, TtsVoiceInfo } from '../types'
import { request, filePreviewUrl } from '../api'
import UploadBox from './UploadBox.vue'
import FilePreview from './FilePreview.vue'
import { ElMessage } from 'element-plus'

const props = defineProps<{
  form: QuickForm
  templates: TemplateInfo[]
  mediaWorkflows: WorkflowInfo[]
  ttsWorkflows: WorkflowInfo[]
  bgmFiles: BgmInfo[]
  ttsVoices: TtsVoiceInfo[]
}>()

defineEmits<{
  (e: 'upload', file: File, category: string, target: string): void
  (e: 'select-history', category: string): void
}>()

const refAudioItems = computed<string[]>(() => {
  return props.form.ref_audio ? [props.form.ref_audio] : []
})

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
        // VoxCPM API
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
        // Edge TTS: voice_id 选择音色
        params.voice_id = props.form.tts_voice
      }
    } else if (props.form.tts_inference_mode === 'comfyui') {
      // ComfyUI: 传 TTS 工作流 + voice_id + 语速 + 参考音频(可选)
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