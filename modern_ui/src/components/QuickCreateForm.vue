<template>
  <el-form label-position="top" class="form-sections">
    <!-- ====== 第一板块：批量模式与文案输入 ====== -->
    <div class="form-section-wrapper">
      <div class="form-section">
      <div class="form-section-title">📝 创作模式与文案输入</div>
      <div class="form-section-body">
      
      <!-- 批量模式开关 -->
      <el-form-item label="生成模式">
        <el-checkbox v-model="form.batch_mode" style="margin-bottom:6px;">
          📦 批量生成模式 — 一次性输入多个主题，批量生成视频
        </el-checkbox>
      </el-form-item>
      
      <!-- 批量模式 -->
      <template v-if="form.batch_mode">
        <el-alert
          title="批量生成：每行输入一个视频主题，所有视频共享下方画面、配音、BGM 等配置。"
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 14px;"
        />
        <el-form-item label="视频主题（每行一个）">
          <el-input
            v-model="form.batch_topics"
            type="textarea"
            :rows="10"
            placeholder="输入视频主题1&#10;输入视频主题2&#10;输入视频主题3&#10;..."
          />
        </el-form-item>
        <div class="soft-panel">
          <el-form-item label="标题前缀（可选）">
            <el-input v-model="form.batch_title_prefix" placeholder="例如：产品名称 - " clearable />
          </el-form-item>
          <el-form-item label="分镜数量（所有视频统一）">
            <el-slider v-model="form.n_scenes" :min="1" :max="20" show-input />
          </el-form-item>
        </div>
        <div class="small muted" style="margin-bottom: 14px;">💡 批量模式固定使用 AI 生成分镜模式。</div>
      </template>
      
      <!-- 单视频模式（原有 UI） -->
      <template v-else>
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
      </template>
      
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


    <!-- ====== 第二板块：画面与媒体配置 ====== -->
    <div class="form-section-wrapper">
      <div class="form-section">
      <div class="form-section-title">🎨 画面与媒体配置</div>
      <div class="form-section-body">

      <!-- 分镜类型 -->
      <el-form-item label="分镜类型">
        <el-radio-group v-model="templateType" @change="onTemplateTypeChange">
          <el-radio-button value="static">📄 静态样式</el-radio-button>
          <el-radio-button value="image">🖼️ 生成插图</el-radio-button>
          <el-radio-button value="video">🎬 生成视频</el-radio-button>
        </el-radio-group>
      </el-form-item>

      <!-- 当前选中模板信息 -->
      <div v-if="selectedTemplateInfo" class="soft-panel" style="margin-bottom:12px;">
        <div class="small"><strong>{{ selectedTemplateInfo.display_name }}</strong></div>
        <div class="small muted">📐 模板尺寸: {{ selectedTemplateInfo.width }} × {{ selectedTemplateInfo.height }}</div>
      </div>

      <!-- 尺寸切换按钮组 -->
      <div v-if="sizeGroups.length > 0" class="size-tabs" style="margin-bottom:10px;">
        <el-radio-group v-model="activeSizeTab" @change="onSizeTabChange" size="small">
          <el-radio-button
            v-for="group in sizeGroups"
            :key="group.size"
            :value="group.size"
          >{{ group.label }}</el-radio-button>
        </el-radio-group>
      </div>

      <!-- 模板网格（当前选中的尺寸组） -->
      <div v-if="currentGroupTemplates.length > 0" class="template-grid">
        <div
          v-for="tpl in currentGroupTemplates"
          :key="tpl.key"
          class="template-card"
          :class="{ 'is-selected': selectedKey === tpl.key }"
          @click="selectTemplate(tpl.key)"
        >
          <div class="template-thumb">
            <img
              v-if="getPreviewUrl(tpl.key)"
              :src="getPreviewUrl(tpl.key)"
              class="template-thumb-img"
              loading="lazy"
              @error="onPreviewError($event, tpl.key)"
            />
            <div v-else class="template-thumb-placeholder">{{ tpl.display_name.replace(/^(static_|image_|video_)/, '') }}</div>
          </div>
          <div class="template-card-footer">
            <span class="small" :class="selectedKey === tpl.key ? '' : 'muted'">
              {{ selectedKey === tpl.key ? '✅ 已选' : '选择' }}
            </span>
          </div>
        </div>
      </div>
      <div v-else class="small muted" style="margin:8px 0 14px;">当前类型下没有可用模板，请选择其他分镜类型。</div>

      <!-- 最终视频尺寸 -->
      <div v-if="selectedTemplateInfo" style="margin:6px 0 14px;">
        <el-tag size="small" type="info" effect="plain">最终视频尺寸：{{ selectedTemplateInfo.width }} × {{ selectedTemplateInfo.height }}</el-tag>
      </div>

      <!-- 自定义参数区域 -->
      <div v-if="Object.keys(templateParams).length > 0" class="soft-panel" style="margin-bottom:14px;">
        <div class="form-section-subtitle">📝 自定义参数</div>
        <div v-loading="templateParamsLoading" style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
          <template v-for="(cfg, name) in templateParams" :key="name">
            <el-form-item v-if="cfg.type === 'text'" :label="cfg.label || name">
              <el-input v-model="customParamValues[name]" :placeholder="String(cfg.default)" />
            </el-form-item>
            <el-form-item v-else-if="cfg.type === 'number'" :label="cfg.label || name">
              <el-input-number v-model="customParamValues[name]" :default-value="Number(cfg.default)" style="width:100%;" />
            </el-form-item>
            <el-form-item v-else-if="cfg.type === 'color'" :label="cfg.label || name">
              <el-color-picker v-model="customParamValues[name]" :default-value="cfg.default" show-alpha />
            </el-form-item>
            <el-form-item v-else-if="cfg.type === 'bool'" :label="cfg.label || name">
              <el-checkbox v-model="customParamValues[name]" :default-value="Boolean(cfg.default)" />
            </el-form-item>
          </template>
        </div>
      </div>

      <!-- 模板预览（默认折叠） -->
      <el-collapse v-model="previewTemplateActiveNames" style="margin-top:12px;">
        <el-collapse-item name="preview-template">
          <template #title>
            <span style="font-size:13px;font-weight:500;color:var(--el-color-primary);">🔍 预览模板</span>
          </template>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
            <el-form-item label="标题">
              <el-input v-model="previewTitle" placeholder="AI 改变内容创作" />
            </el-form-item>
            <el-form-item label="图片路径">
              <el-input v-model="previewImage" placeholder="resources/example.png" />
            </el-form-item>
          </div>
          <el-form-item label="文本">
            <el-input v-model="previewTextContent" type="textarea" :rows="2" placeholder="Pixelle.AI 正在用人工智能改变内容创作的方式..." />
          </el-form-item>
          <div class="small muted" style="margin-bottom:8px;">📐 模板尺寸: {{ selectedTemplateInfo ? `${selectedTemplateInfo.width} × ${selectedTemplateInfo.height}` : '-' }}</div>
          <el-button type="primary" size="small" @click="handlePreviewTemplate" :loading="previewTemplateLoading" style="width:100%;">
            🖼️ 预览模板
          </el-button>
          <img v-if="previewTemplateUrl" :src="previewTemplateUrl" style="width:100%;margin-top:10px;border-radius:12px;border:1px solid var(--line);" />
        </el-collapse-item>
      </el-collapse>

    </div>
      </div>
    </div>

    <!-- ====== 🎨 插图/视频生成 ====== -->
    <div class="form-section-wrapper">
      <div class="form-section">
      <div class="form-section-title">🎨 {{ templateType === 'video' ? '视频' : '插图' }}生成</div>
      <div class="form-section-body">

      <div v-if="templateType !== 'static'" class="soft-panel">
        <div class="form-section-subtitle">🎨 {{ templateType === 'video' ? '视频' : '插图' }}生成</div>
        <div class="small muted" style="margin-bottom:10px;">💡 功能说明：根据分镜选择确定使用的素材类型</div>

        <el-form-item label="生成来源">
          <el-radio-group v-model="workflowSource" size="small">
            <el-radio-button value="runninghub">RunningHub</el-radio-button>
            <!-- <el-radio-button value="selfhost">本地 ComfyUI</el-radio-button> -->
            <el-radio-button value="api">API 模型</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <template v-if="workflowSource !== 'api'">
          <el-form-item label="Workflow">
            <el-select v-model="form.media_workflow" filterable clearable placeholder="默认/选择图片或视频工作流" style="width:100%;">
              <el-option v-for="wf in filteredWorkflows" :key="wf.key" :label="wf.display_name" :value="wf.key" />
            </el-select>
          </el-form-item>
        </template>
        <template v-else>
          <el-form-item label="API 模型">
            <el-select v-model="form.api_model" filterable clearable placeholder="选择 API 模型" style="width:100%;">
              <el-option
                v-for="m in apiMediaModels"
                :key="m.value"
                :label="m.label"
                :value="m.value"
              />
            </el-select>
          </el-form-item>
        </template>

        <!-- 媒体尺寸信息 -->
        <div v-if="selectedTemplateInfo" class="small muted" style="margin:4px 0 10px;">
          📐 {{ templateType === 'video' ? '视频' : '插图' }}尺寸：{{ selectedTemplateInfo.width }}x{{ selectedTemplateInfo.height }}（由模板自动决定）
        </div>

        <el-form-item label="提示词前缀">
          <el-input v-model="form.prompt_prefix" type="textarea" :rows="2" placeholder="在生成图片提示词前添加固定前缀（可选）" />
        </el-form-item>

        <!-- 预览提示词（默认折叠） -->
        <el-collapse v-model="previewPromptActiveNames" style="margin-top:12px;">
          <el-collapse-item name="preview-prompt">
            <template #title>
              <span style="font-size:13px;font-weight:500;color:var(--el-color-primary);">🔍 预览提示词</span>
            </template>
            <el-form-item>
              <el-input v-model="previewPrompt" type="textarea" :rows="2" placeholder="输入预览提示词，例如：a dog" />
            </el-form-item>
            <el-button size="small" @click="handlePreviewStyle" :loading="stylePreviewLoading" style="width:100%;">
              👁️ 生成预览风格
            </el-button>
          </el-collapse-item>
        </el-collapse>
        <img v-if="stylePreviewUrl" :src="stylePreviewUrl" style="width:100%;margin-top:10px;border-radius:12px;border:1px solid var(--line);" />
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
      <!-- 背景音乐预览 -->
      <div v-if="form.bgm_path" class="soft-panel" style="margin-top:8px;">
        <div style="display:flex;gap:10px;align-items:center;">
          <span class="small muted">🎵 音频预览：</span>
          <audio :src="filePreviewUrl(form.bgm_path)" controls style="height:32px;flex:1;min-width:0;" />
        </div>
      </div>
    </div>
      </div>
    </div>
  </el-form>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
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

const previewActiveNames = ref<string[]>([])
const asrLoading = ref(false)

// ====== 🎨 画面与媒体配置 ======

// 分镜类型
const templateType = ref<'static' | 'image' | 'video'>('image')

// 按模板类型分组
const groupedTemplates = computed(() => {
  const groups: Record<string, TemplateInfo[]> = {}
  const keywordMap: Record<string, string> = { static: 'static_', image: 'image_', video: 'video_' }
  const prefix = keywordMap[templateType.value]
  props.templates.forEach(t => {
    if (t.name.startsWith(prefix)) {
      if (!groups[t.size]) groups[t.size] = []
      groups[t.size].push(t)
    }
  })
  return groups
})

const sizeGroups = computed(() => {
  return Object.entries(groupedTemplates.value).map(([size, tpls]) => ({
    size,
    templates: tpls,
    label: `${tpls[0]?.orientation === 'portrait' ? '竖屏' : tpls[0]?.orientation === 'landscape' ? '横屏' : '方形'} ${size}`,
  }))
})

const selectedTemplateInfo = computed(() => {
  return props.templates.find(t => t.key === props.form.frame_template)
})

const activeSizeTab = ref('')

// 当前选中尺寸组的模板列表
const currentGroupTemplates = computed(() => {
  const group = sizeGroups.value.find(g => g.size === activeSizeTab.value)
  return group?.templates || []
})

// 当前选中的模板 key（用于模板画廊高亮）
const selectedKey = computed(() => props.form.frame_template)

function onSizeTabChange(size: string) {
  // 仅切换显示组，不自动选中模板
  // 如果当前选中的模板不在新组中，取消选中
  const group = sizeGroups.value.find(g => g.size === size)
  if (group && !group.templates.find(t => t.key === props.form.frame_template)) {
    // 不清除选择，让用户手动点击卡片选择
  }
}

function selectTemplate(key: string) {
  props.form.frame_template = key
}

function onTemplateTypeChange() {
  // 切换类型后自动设置第一个尺寸组和第一个模板
  const groups = sizeGroups.value
  if (groups.length > 0) {
    activeSizeTab.value = groups[0].size
    if (groups[0].templates.length > 0) {
      selectTemplate(groups[0].templates[0].key)
    }
  }
}

// 自定义参数
const customParamValues = ref<Record<string, any>>({})
const templateParams = ref<Record<string, { type: string; default: any; label: string }>>({})
const templateParamsLoading = ref(false)
const templateMediaSize = ref({ width: 0, height: 0 })

async function loadTemplateParams(templateKey: string) {
  if (!templateKey) return
  templateParamsLoading.value = true
  try {
    const res: any = await request(`/api/frame/template/params?template=${encodeURIComponent(templateKey)}`)
    templateParams.value = res.params || {}
    templateMediaSize.value = { width: res.media_width || 0, height: res.media_height || 0 }
    // 初始化自定义参数默认值
    const vals: Record<string, any> = {}
    for (const [name, cfg] of Object.entries(res.params || {})) {
      vals[name] = (cfg as any).default
    }
    customParamValues.value = vals
  } catch (_) {
    templateParams.value = {}
    templateMediaSize.value = { width: 0, height: 0 }
  } finally {
    templateParamsLoading.value = false
  }
}

// 监听模板变化
watch(() => props.form.frame_template, (newKey) => {
  if (newKey) loadTemplateParams(newKey)
})

// 模板预览缩略图路径映射
// docs/images/{size}/{name}.{jpg|png}  →  /api/files/docs/images/{size}/{name}.{jpg|png}
const previewCache = ref<Record<string, string>>({})
const failedKeys = ref<Set<string>>(new Set())

function getPreviewUrl(templateKey: string): string {
  if (failedKeys.value.has(templateKey)) return ''
  if (templateKey) {
    const parts = templateKey.replace(/\\/g, '/').split('/')
    if (parts.length >= 2) {
      const size = parts[0]
      const name = parts[1].replace('.html', '')
      const url = `/api/files/docs/images/${size}/${name}.jpg`
      previewCache.value[templateKey] = url
      return url
    }
  }
  return ''
}

function onPreviewError(event: Event, templateKey: string) {
  const img = event.target as HTMLImageElement
  if (!img) return
  // 如果 .jpg 加载失败，尝试 .png 作为 fallback
  const currentSrc = img.src
  if (currentSrc.endsWith('.jpg') || currentSrc.endsWith('.jpeg')) {
    const pngSrc = currentSrc.replace(/\.jpe?g$/, '.png')
    if (pngSrc !== currentSrc) {
      img.src = pngSrc
      return
    }
  }
  // .png 也失败则标记为失败并隐藏
  failedKeys.value.add(templateKey)
  img.style.display = 'none'
}

// 初始化模板参数和尺寸 tab
const initialLoad = ref(false)
watch(() => props.templates, (tpls) => {
  if (tpls.length > 0 && !initialLoad.value) {
    initialLoad.value = true
    const imgTpl = tpls.find(t => t.name.startsWith('image_'))
    const portrait = tpls.find(t => t.orientation === 'portrait')
    const def = imgTpl || portrait || tpls[0]
    if (def && !props.form.frame_template) {
      props.form.frame_template = def.key
    }
    if (props.form.frame_template) {
      loadTemplateParams(props.form.frame_template)
    }
    // 设置默认尺寸 tab
    if (sizeGroups.value.length > 0) {
      activeSizeTab.value = sizeGroups.value[0].size
    }
  }
}, { immediate: true })

// 折叠状态（默认折叠）
const previewTemplateActiveNames = ref<string[]>([])
const previewPromptActiveNames = ref<string[]>([])

// 模板预览
const previewTitle = ref('AI 改变内容创作')
const previewImage = ref('resources/example.png')
const previewTextContent = ref('Pixelle.AI 正在用人工智能改变内容创作的方式，让每个人都能轻松制作专业级视频。')
const previewTemplateLoading = ref(false)
const previewTemplateUrl = ref('')

async function handlePreviewTemplate() {
  if (!props.form.frame_template) { ElMessage.warning('请先选择模板'); return }
  previewTemplateLoading.value = true
  previewTemplateUrl.value = ''
  try {
    const res: any = await request('/api/frame/render', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        template: props.form.frame_template,
        title: previewTitle.value,
        text: previewTextContent.value,
        image: previewImage.value,
      }),
    })
    if (res.frame_path) {
      previewTemplateUrl.value = filePreviewUrl(res.frame_path)
    }
    ElMessage.success('模板预览生成成功')
  } catch (e: any) {
    ElMessage.error(`预览失败：${e.message}`)
  } finally {
    previewTemplateLoading.value = false
  }
}

// 媒体生成来源
const workflowSource = ref('runninghub')

const filteredWorkflows = computed(() => {
  const prefix = templateType.value === 'video' ? 'video_' : 'image_'
  return props.mediaWorkflows.filter(wf => {
    // 先按模板类型过滤
    if (!wf.name.startsWith(prefix)) return false
    // 再按生成来源过滤
    if (workflowSource.value === 'runninghub' && wf.source !== 'runninghub') return false
    if (workflowSource.value === 'selfhost' && wf.source !== 'selfhost') return false
    return true
  })
})

// API 模型选项（值需要带 api/ 前缀以便后端路由到 API 媒体服务）
const apiMediaModels = computed(() => {
  if (templateType.value === 'video') {
    return [
      { label: 'wan2.7-r2v - API Dashscope', value: 'api/dashscope/wan2.7-r2v' },
      { label: 'happyhorse-1.0-r2v - API Dashscope', value: 'api/dashscope/happyhorse-1.0-r2v' },
    ]
  }
  return [
    { label: 'wan2.7-image - API Dashscope', value: 'api/dashscope/wan2.7-image' },
    { label: 'wan2.7-image-pro - API Dashscope', value: 'api/dashscope/wan2.7-image-pro' },
    { label: 'wan2.6-t2i - API Dashscope', value: 'api/dashscope/wan2.6-t2i' },
    { label: 'gpt-image-2 - API OpenAI', value: 'api/openai/gpt-image-2' },
    { label: 'doubao-seedream-5-0-260128 - API Seedream', value: 'api/seedream/doubao-seedream-5-0-260128' },
    { label: 'doubao-seedream-4-5-251128 - API Seedream', value: 'api/seedream/doubao-seedream-4-5-251128' },
    { label: 'doubao-seedream-4-0-250828 - API Seedream', value: 'api/seedream/doubao-seedream-4-0-250828' },
  ]
})

// 风格预览
const stylePreviewLoading = ref(false)
const stylePreviewUrl = ref('')
const previewPrompt = ref('a dog')

async function handlePreviewStyle() {
  if (!previewPrompt.value.trim()) { ElMessage.warning('请输入预览提示词'); return }
  
  // 校验：根据生成来源检查对应的字段
  if (workflowSource.value === 'api') {
    if (!props.form.api_model) { ElMessage.warning('请先选择 API 模型'); return }
  } else {
    if (!props.form.media_workflow) { ElMessage.warning('请先选择 Workflow'); return }
  }
  
  stylePreviewLoading.value = true
  stylePreviewUrl.value = ''
  const tpl = selectedTemplateInfo.value
  try {
    const payload: Record<string, any> = {
      prompt: props.form.prompt_prefix + previewPrompt.value.trim(),
      width: tpl?.width || 1024,
      height: tpl?.height || 1024,
    }
    if (workflowSource.value === 'api') {
      payload.workflow = props.form.api_model
    } else {
      payload.workflow = props.form.media_workflow
    }
    const res: any = await request('/api/image/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (res.image_url) {
      stylePreviewUrl.value = res.image_url
    } else if (res.image_path) {
      stylePreviewUrl.value = filePreviewUrl(res.image_path)
    }
    ElMessage.success('风格预览生成成功')
  } catch (e: any) {
    ElMessage.error(`风格预览失败：${e.message}`)
  } finally {
    stylePreviewLoading.value = false
  }
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

<style scoped>
/* 尺寸切换按钮组 - 匹配深色主题 */
.size-tabs .el-radio-group {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.size-tabs .el-radio-button__inner {
  font-size: 12px;
  padding: 6px 12px;
  border-radius: 8px !important;
  border: 1px solid rgba(71, 85, 105, 0.45) !important;
  background: rgba(8, 13, 25, 0.92) !important;
  color: #94a3b8 !important;
}
.size-tabs .el-radio-button__original-radio:checked + .el-radio-button__inner {
  background: linear-gradient(135deg, rgba(124, 58, 237, 0.3), rgba(6, 182, 212, 0.18)) !important;
  border-color: rgba(125, 211, 252, 0.45) !important;
  color: #fff !important;
}

/* 模板网格 */
.template-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: 8px;
  margin-bottom: 12px;
}
.template-card {
  border: 1px solid var(--line);
  border-radius: 12px;
  background: rgba(15, 23, 42, 0.52);
  cursor: pointer;
  transition: 0.18s ease;
  overflow: hidden;
}
.template-card:hover {
  border-color: rgba(125, 211, 252, 0.36);
  background: rgba(124, 58, 237, 0.15);
}
.template-card.is-selected {
  border-color: rgba(125, 211, 252, 0.55);
  background: linear-gradient(135deg, rgba(124, 58, 237, 0.25), rgba(6, 182, 212, 0.1));
}
.template-thumb {
  aspect-ratio: 88 / 157;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(2, 6, 23, 0.4);
  border-bottom: 1px solid var(--line);
}
.template-thumb-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.template-thumb-placeholder {
  font-size: 11px;
  color: #64748b;
  text-align: center;
  padding: 4px;
  word-break: break-all;
  line-height: 1.3;
}
.template-card-footer {
  padding: 6px 8px;
  text-align: center;
}
.form-section-subtitle {
  font-size: 13px;
  font-weight: 800;
  margin-bottom: 10px;
  color: #a78bfa;
}
</style>