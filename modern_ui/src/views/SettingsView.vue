<template>
  <div class="tool-page">
    <div class="page-header">
      <span class="page-icon">⚙️</span>
      <div>
        <h3 class="page-title">系统配置</h3>
        <p class="page-desc">LLM / ComfyUI / RunningHub / API 媒体模型</p>
      </div>
    </div>

    <el-alert v-if="!isConfigured" title="系统尚未配置，请填写以下必要信息" type="warning" show-icon :closable="false" style="margin-bottom:18px;" />

    <div class="page-layout" style="grid-template-columns: 1fr 1fr;">
      <!-- ========== Column 1: LLM ========== -->
      <div class="card">
        <div class="card-header"><h3 class="card-title">🤖 LLM 配置</h3></div>
        <div class="card-body">
          <el-form label-position="top" size="default">
            <el-form-item label="快速预设">
              <el-select v-model="selectedPreset" style="width:100%" @change="onPresetChange">
                <el-option v-for="p in presets" :key="p" :label="p" :value="p" />
              </el-select>
            </el-form-item>

            <el-form-item v-if="presetApiKeyUrl" label="获取 API Key">
              <el-link :href="presetApiKeyUrl" type="primary" target="_blank">🔑 点击获取 API Key</el-link>
            </el-form-item>

            <el-divider />

            <el-form-item label="API Key *" required>
              <el-input v-model="llmConfig.api_key" type="password" show-password placeholder="sk-..." />
            </el-form-item>

            <el-form-item label="Base URL *" required>
              <el-input v-model="llmConfig.base_url" placeholder="https://api.openai.com/v1" />
            </el-form-item>

            <!-- Model selection with load + test buttons -->
            <el-form-item label="模型 *" required>
              <div style="display:flex;gap:8px;width:100%;">
                <el-select v-model="llmConfig.model" style="flex:1;" filterable allow-create placeholder="选择或输入模型名称">
                  <el-option v-for="m in loadedModels" :key="m" :label="m" :value="m" />
                </el-select>
                <el-button :loading="loadingModels" @click="loadModels" :disabled="!llmConfig.api_key || !llmConfig.base_url">🔄 加载</el-button>
                <el-button :loading="testingConnection" @click="testConnection" :disabled="!llmConfig.api_key || !llmConfig.base_url">🔌 测试</el-button>
              </div>
            </el-form-item>
          </el-form>
        </div>
      </div>

      <!-- ========== Column 2: ComfyUI ========== -->
      <div class="card">
        <div class="card-header"><h3 class="card-title">🔧 ComfyUI / RunningHub</h3></div>
        <div class="card-body">
          <el-form label-position="top" size="default">
            <el-form-item label="本地 ComfyUI">
              <div style="display:flex;gap:8px;width:100%;">
                <el-input v-model="comfyuiConfig.comfyui_url" placeholder="http://127.0.0.1:8188" style="flex:1;" />
                <el-button :loading="testingComfyUI" @click="testComfyUI">测试连接</el-button>
              </div>
            </el-form-item>

            <el-form-item label="ComfyUI API Key（可选）">
              <el-input v-model="comfyuiConfig.comfyui_api_key" type="password" show-password placeholder="留空则不使用" />
            </el-form-item>

            <el-divider />

            <el-form-item label="RunningHub API Key">
              <el-input v-model="comfyuiConfig.runninghub_api_key" type="password" show-password placeholder="rh_..." />
            </el-form-item>

            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
              <el-form-item label="并发上限">
                <el-input-number v-model="comfyuiConfig.runninghub_concurrent_limit" :min="1" :max="10" style="width:100%;" />
              </el-form-item>
              <el-form-item label="实例规格">
                <el-select v-model="instanceTypeDisplay" style="width:100%;">
                  <el-option label="24G 基础版" value="24g" />
                  <el-option label="48G 增强版" value="plus" />
                </el-select>
              </el-form-item>
            </div>
          </el-form>
        </div>
      </div>
    </div>

    <!-- ========== API 媒体模型 ========== -->
    <div class="card">
      <div class="card-header"><h3 class="card-title">🧩 API 媒体模型</h3></div>
      <div class="card-body">
        <div class="service-hint" style="margin-bottom:16px;">
          用于直连图像/视频模型，不影响上方 LLM 与 ComfyUI/RunningHub 配置。
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
          <!-- Common settings -->
          <div class="sub-section" style="grid-column:1/-1;">
            <div class="sub-section-title">通用设置</div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
              <el-form-item label="打印模型请求参数">
                <el-switch v-model="commonConfig.print_model_input" />
              </el-form-item>
              <el-form-item label="本地代理（可选）">
                <el-input v-model="commonConfig.local_proxy" placeholder="http://127.0.0.1:9090" />
              </el-form-item>
            </div>
          </div>

          <!-- OpenAI -->
          <div class="sub-section">
            <div class="sub-section-title">OpenAI / GPT Image</div>
            <el-form-item label="启用代理">
              <el-switch v-model="openaiConfig.use_proxy" />
            </el-form-item>
            <el-form-item label="API Key">
              <el-input v-model="openaiConfig.api_key" type="password" show-password placeholder="sk-..." />
            </el-form-item>
            <el-form-item label="Base URL">
              <el-input v-model="openaiConfig.base_url" placeholder="https://api.openai.com/v1" />
            </el-form-item>
          </div>

          <!-- DashScope -->
          <div class="sub-section">
            <div class="sub-section-title">DashScope / Wan / HappyHorse</div>
            <el-form-item label="启用代理">
              <el-switch v-model="dashscopeConfig.use_proxy" />
            </el-form-item>
            <el-form-item label="API Key">
              <el-input v-model="dashscopeConfig.api_key" type="password" show-password placeholder="sk-..." />
            </el-form-item>
            <el-form-item label="Base URL">
              <el-input v-model="dashscopeConfig.base_url" placeholder="https://dashscope.aliyuncs.com/api/v1" />
            </el-form-item>
          </div>

          <!-- ARK -->
          <div class="sub-section">
            <div class="sub-section-title">Volcengine ARK / Seedream / Seedance</div>
            <el-form-item label="启用代理">
              <el-switch v-model="arkConfig.use_proxy" />
            </el-form-item>
            <el-form-item label="API Key">
              <el-input v-model="arkConfig.api_key" type="password" show-password placeholder="..." />
            </el-form-item>
            <el-form-item label="Base URL">
              <el-input v-model="arkConfig.base_url" placeholder="https://ark.cn-beijing.volces.com/api/v3" />
            </el-form-item>
          </div>

          <!-- Kling -->
          <div class="sub-section">
            <div class="sub-section-title">Kling AI / 可灵</div>
            <el-form-item label="启用代理">
              <el-switch v-model="klingConfig.use_proxy" />
            </el-form-item>
            <el-form-item label="Base URL">
              <el-input v-model="klingConfig.base_url" placeholder="https://api-beijing.klingai.com" />
            </el-form-item>
            <el-form-item label="Access Key">
              <el-input v-model="klingConfig.access_key" type="password" show-password />
            </el-form-item>
            <el-form-item label="Secret Key">
              <el-input v-model="klingConfig.secret_key" type="password" show-password />
            </el-form-item>
          </div>
        </div>
      </div>
    </div>

    <!-- ========== Action Buttons ========== -->
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
      <el-button type="primary" size="large" style="height:48px;font-weight:900;" :loading="saving" @click="handleSave">
        保存配置
      </el-button>
      <el-button size="large" style="height:48px;font-weight:900;" :loading="resetting" @click="handleReset">
        重置配置
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getConfig,
  saveConfig as apiSaveConfig,
  loadLLMModels,
  testLLMConnection,
  testComfyUIConnection,
  resetConfig as apiResetConfig,
  detectPreset,
  getPresetConfig,
} from '../api'

// ====== State ======
const presets = ref<string[]>([])
const selectedPreset = ref<string>('Custom')
const loadedModels = ref<string[]>([])
const isConfigured = ref(true)
const presetApiKeyUrl = ref('')

const llmConfig = reactive({ api_key: '', base_url: '', model: '' })
const comfyuiConfig = reactive({
  comfyui_url: 'http://127.0.0.1:8188',
  comfyui_api_key: '',
  runninghub_api_key: '',
  runninghub_concurrent_limit: 1,
  runninghub_instance_type: '',
})
const instanceTypeDisplay = ref('24g')

const commonConfig = reactive({ print_model_input: false, local_proxy: '' })
const openaiConfig = reactive({ api_key: '', base_url: '', use_proxy: false })
const dashscopeConfig = reactive({ api_key: '', base_url: '', use_proxy: false })
const arkConfig = reactive({ api_key: '', base_url: '', use_proxy: false })
const klingConfig = reactive({ base_url: '', access_key: '', secret_key: '', use_proxy: false })

const saving = ref(false)
const resetting = ref(false)
const loadingModels = ref(false)
const testingConnection = ref(false)
const testingComfyUI = ref(false)

const runninghubInstanceType = computed(() => {
  return instanceTypeDisplay.value === 'plus' ? 'plus' : ''
})

// ====== Load initial config ======
onMounted(async () => {
  try {
    const cfg = await getConfig()
    presets.value = [...cfg.presets, 'Custom']

    // LLM
    llmConfig.api_key = cfg.llm.api_key
    llmConfig.base_url = cfg.llm.base_url
    llmConfig.model = cfg.llm.model

    // Detect preset
    try {
      const matchedPreset = await detectPreset()
      selectedPreset.value = matchedPreset
      if (matchedPreset !== 'Custom') {
        try {
          const presetData = await getPresetConfig(matchedPreset)
          if (presetData.api_key_url) {
            presetApiKeyUrl.value = presetData.api_key_url
          }
          // Auto-fill base_url and model if not set
          if (!llmConfig.base_url && presetData.base_url) {
            llmConfig.base_url = presetData.base_url
          }
          if (!llmConfig.model && presetData.model) {
            llmConfig.model = presetData.model
          }
          // Auto-fill Ollama default API key
          if (!llmConfig.api_key && presetData.default_api_key) {
            llmConfig.api_key = presetData.default_api_key
          }
        } catch {
          // ignore preset detail errors
        }
      }
    } catch {
      selectedPreset.value = 'Custom'
    }

    // ComfyUI
    comfyuiConfig.comfyui_url = cfg.comfyui.comfyui_url
    comfyuiConfig.comfyui_api_key = cfg.comfyui.comfyui_api_key
    comfyuiConfig.runninghub_api_key = cfg.comfyui.runninghub_api_key
    comfyuiConfig.runninghub_concurrent_limit = cfg.comfyui.runninghub_concurrent_limit
    comfyuiConfig.runninghub_instance_type = cfg.comfyui.runninghub_instance_type
    instanceTypeDisplay.value = cfg.comfyui.runninghub_instance_type === 'plus' ? 'plus' : '24g'

    const ap = cfg.api_providers
    if (ap.common) {
      commonConfig.print_model_input = !!ap.common.print_model_input
      commonConfig.local_proxy = ap.common.local_proxy || ''
    }
    if (ap.openai) {
      openaiConfig.api_key = ap.openai.api_key || ''
      openaiConfig.base_url = ap.openai.base_url || ''
      openaiConfig.use_proxy = !!ap.openai.use_proxy
    }
    if (ap.dashscope) {
      dashscopeConfig.api_key = ap.dashscope.api_key || ''
      dashscopeConfig.base_url = ap.dashscope.base_url || ''
      dashscopeConfig.use_proxy = !!ap.dashscope.use_proxy
    }
    if (ap.ark) {
      arkConfig.api_key = ap.ark.api_key || ''
      arkConfig.base_url = ap.ark.base_url || ''
      arkConfig.use_proxy = !!ap.ark.use_proxy
    }
    if (ap.kling) {
      klingConfig.base_url = ap.kling.base_url || ''
      klingConfig.access_key = ap.kling.access_key || ''
      klingConfig.secret_key = ap.kling.secret_key || ''
      klingConfig.use_proxy = !!ap.kling.use_proxy
    }

    isConfigured.value = !!(cfg.llm.api_key && cfg.llm.base_url && cfg.llm.model)
  } catch (e: any) {
    ElMessage.error(`加载配置失败：${e.message}`)
  }
})

// ====== Preset ======
async function onPresetChange(val: string) {
  presetApiKeyUrl.value = ''
  if (val === 'Custom') return

  try {
    const presetData = await getPresetConfig(val)
    if (presetData.base_url) llmConfig.base_url = presetData.base_url
    if (presetData.model) llmConfig.model = presetData.model
    if (presetData.default_api_key) llmConfig.api_key = presetData.default_api_key
    if (presetData.api_key_url) presetApiKeyUrl.value = presetData.api_key_url
  } catch (e: any) {
    ElMessage.warning(`加载预设失败：${e.message}`)
  }
}

// ====== Load models ======
async function loadModels() {
  if (!llmConfig.api_key || !llmConfig.base_url) {
    ElMessage.warning('请先填写 API Key 和 Base URL')
    return
  }
  loadingModels.value = true
  try {
    const models = await loadLLMModels(llmConfig.api_key, llmConfig.base_url)
    loadedModels.value = models
    ElMessage.success(`成功加载 ${models.length} 个模型`)
  } catch (e: any) {
    ElMessage.error(`加载模型失败：${e.message}`)
  } finally {
    loadingModels.value = false
  }
}

// ====== Test LLM ======
async function testConnection() {
  if (!llmConfig.api_key || !llmConfig.base_url) {
    ElMessage.warning('请先填写 API Key 和 Base URL')
    return
  }
  testingConnection.value = true
  try {
    const res = await testLLMConnection(llmConfig.api_key, llmConfig.base_url)
    if (res.success) {
      ElMessage.success(`连接成功！发现 ${res.model_count} 个模型`)
    } else {
      ElMessage.error(`连接失败：${res.message}`)
    }
  } catch (e: any) {
    ElMessage.error(`连接失败：${e.message}`)
  } finally {
    testingConnection.value = false
  }
}

// ====== Test ComfyUI ======
async function testComfyUI() {
  if (!comfyuiConfig.comfyui_url) {
    ElMessage.warning('请先填写 ComfyUI 地址')
    return
  }
  testingComfyUI.value = true
  try {
    const ok = await testComfyUIConnection(comfyuiConfig.comfyui_url)
    if (ok) {
      ElMessage.success('连接成功！')
    } else {
      ElMessage.error('连接失败，请检查地址是否正确')
    }
  } catch (e: any) {
    ElMessage.error(`连接失败：${e.message}`)
  } finally {
    testingComfyUI.value = false
  }
}

// ====== Save ======
async function handleSave() {
  if (!llmConfig.api_key || !llmConfig.base_url || !llmConfig.model) {
    ElMessage.warning('请填写完整的 LLM 配置（API Key、Base URL、模型）')
    return
  }

  saving.value = true
  try {
    const res = await apiSaveConfig({
      llm: {
        api_key: llmConfig.api_key,
        base_url: llmConfig.base_url,
        model: llmConfig.model,
      },
      comfyui: {
        comfyui_url: comfyuiConfig.comfyui_url,
        comfyui_api_key: comfyuiConfig.comfyui_api_key,
        runninghub_api_key: comfyuiConfig.runninghub_api_key,
        runninghub_concurrent_limit: comfyuiConfig.runninghub_concurrent_limit,
        runninghub_instance_type: runninghubInstanceType.value,
      },
      api_providers: {
        common: { print_model_input: commonConfig.print_model_input, local_proxy: commonConfig.local_proxy },
        openai: { api_key: openaiConfig.api_key, base_url: openaiConfig.base_url, use_proxy: openaiConfig.use_proxy },
        dashscope: { api_key: dashscopeConfig.api_key, base_url: dashscopeConfig.base_url, use_proxy: dashscopeConfig.use_proxy },
        ark: { api_key: arkConfig.api_key, base_url: arkConfig.base_url, use_proxy: arkConfig.use_proxy },
        kling: { base_url: klingConfig.base_url, access_key: klingConfig.access_key, secret_key: klingConfig.secret_key, use_proxy: klingConfig.use_proxy },
      },
    })
    if (res.success) {
      ElMessage.success('配置已保存')
      isConfigured.value = true
    } else {
      ElMessage.error(`保存失败：${res.message}`)
    }
  } catch (e: any) {
    ElMessage.error(`保存失败：${e.message}`)
  } finally {
    saving.value = false
  }
}

// ====== Reset ======
async function handleReset() {
  try {
    await ElMessageBox.confirm('确定要重置所有配置为默认值吗？', '确认重置', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }

  resetting.value = true
  try {
    const res = await apiResetConfig()
    if (res.success) {
      ElMessage.success('配置已重置，请重新加载页面')
      window.location.reload()
    }
  } catch (e: any) {
    ElMessage.error(`重置失败：${e.message}`)
  } finally {
    resetting.value = false
  }
}
</script>