<template>
  <el-form label-position="top" class="form-sections">
    <!-- ====== 第一板块：素材上传 ====== -->
    <div class="form-section-wrapper">
      <div class="form-section">
      <div class="form-section-title">📤 素材上传</div>
      <div class="form-section-body">
      <el-form-item label="图片素材">
        <div class="upload-field-container">
          <UploadBox category="image" accept="image/*" @upload="handleImageUpload" @select-history="(c) => $emit('select-history', c)" />
          <FilePreview v-if="form.image_asset" :items="[form.image_asset]" @remove="form.image_asset = null" />
        </div>
      </el-form-item>
      <el-form-item label="视频素材">
        <div class="upload-field-container">
          <UploadBox category="video" accept="video/*" @upload="handleVideoUpload" @select-history="(c) => $emit('select-history', c)" />
          <FilePreview v-if="form.video_asset" :items="[form.video_asset]" @remove="form.video_asset = null" />
        </div>
      </el-form-item>
    </div>
      </div>
    </div>

    <!-- ====== 第二板块：视频信息 ====== -->
    <div class="form-section-wrapper">
      <div class="form-section">
      <div class="form-section-title">📋 视频信息</div>
      <div class="form-section-body">
      <el-form-item label="视频标题">
        <el-input v-model="form.video_title" placeholder="如：宠物店年终促销" />
      </el-form-item>
      <el-form-item label="创作意图">
        <el-input v-model="form.intent" type="textarea" :rows="4" placeholder="描述卖点、风格、受众等..." />
      </el-form-item>
      <el-form-item label="目标时长（秒）">
        <el-slider v-model="form.duration" :min="15" :max="120" :step="5" show-input />
      </el-form-item>
    </div>
      </div>
    </div>

    <!-- ====== 第三板块：素材分析与动画配置 ====== -->
    <div class="form-section-wrapper">
      <div class="form-section">
      <div class="form-section-title">⚙️ 素材分析与动画配置</div>
      <div class="form-section-body">

      <!-- 3.1 素材分析服务 -->
      <div class="sub-section">
        <div class="sub-section-title">3.1 素材分析服务</div>
        <el-form-item label="素材分析来源">
          <el-radio-group v-model="form.source">
            <el-radio-button value="runninghub">RunningHub（云端）</el-radio-button>
            <el-radio-button value="selfhost">本地 ComfyUI</el-radio-button>
            <el-radio-button value="api">API VLM</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="分析图片工作流">
          <el-input v-model="form.analysis_image_workflow" placeholder="如 runninghub/analyse_image.json" />
        </el-form-item>
        <el-form-item label="分析视频工作流">
          <el-input v-model="form.analysis_video_workflow" placeholder="如 runninghub/analyse_video.json" />
        </el-form-item>
        <el-form-item v-if="form.source === 'api'" label="API VLM 模型">
          <el-input v-model="form.analysis_vlm_model" placeholder="填写模型 key" />
        </el-form-item>
      </div>

      <!-- 3.2 素材动画服务 -->
      <div class="sub-section">
        <div class="sub-section-title">3.2 素材动画服务</div>
        <el-form-item label="素材动画服务">
          <el-radio-group v-model="form.animation_enabled">
            <el-radio-button :value="false">不启用</el-radio-button>
            <el-radio-button :value="true">API 调用</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="form.animation_enabled" label="图生视频动画工作流">
          <el-input v-model="form.api_video_workflow" placeholder="api/..." />
        </el-form-item>
      </div>
    </div>
      </div>
    </div>

    <!-- ====== 第四板块：配音合成 ====== -->
    <div class="form-section-wrapper">
      <div class="form-section">
      <div class="form-section-title">🎤 配音合成</div>
      <div class="form-section-body">
      <el-form-item label="TTS 声音">
        <el-select v-model="form.voice_id" filterable placeholder="选择 TTS 音色" style="width:100%;">
          <el-option
            v-for="voice in ttsVoices"
            :key="voice.id"
            :label="`${voice.name} (${voice.locale}${voice.gender ? ' · ' + voice.gender : ''})`"
            :value="voice.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="TTS 语速">
        <el-slider v-model="form.tts_speed" :min="0.5" :max="2.0" :step="0.1" show-input />
      </el-form-item>

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

    <!-- ====== 第五板块：背景音乐 ====== -->
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
import { ref } from 'vue'
import type { AssetForm, BgmInfo, TtsVoiceInfo } from '../types'
import { request, filePreviewUrl } from '../api'
import UploadBox from './UploadBox.vue'
import FilePreview from './FilePreview.vue'
import { ElMessage } from 'element-plus'

const props = defineProps<{
  form: AssetForm
  bgmFiles: BgmInfo[]
  ttsVoices: TtsVoiceInfo[]
}>()

const emit = defineEmits<{
  (e: 'upload', file: File, category: string, target: string): void
  (e: 'select-history', category: string): void
}>()

function handleImageUpload(file: File, category: string) {
  emit('upload', file, category, 'asset_image')
}

function handleVideoUpload(file: File, category: string) {
  emit('upload', file, category, 'asset_video')
}

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
    if (props.form.voice_id) {
      params.voice_id = props.form.voice_id
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
</script>
