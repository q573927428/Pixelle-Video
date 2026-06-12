import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { TtsVoiceInfo } from '../types'
import { loadResources, loadTasks as apiLoadTasks, checkHealth, uploadFile as apiUpload, saveToLocalHistory, loadLocalHistory } from '../api'

export function useResources() {
  const healthOk = ref(false)
  const templates = ref<any[]>([])
  const mediaWorkflows = ref<any[]>([])
  const ttsWorkflows = ref<any[]>([])
  const bgmFiles = ref<any[]>([])
  const ttsVoices = ref<TtsVoiceInfo[]>([])
  const tasks = ref<any[]>([])
  const uploads = ref<any[]>([])

  async function checkH() {
    healthOk.value = await checkHealth()
  }

  async function loadRes() {
    try {
      const res = await loadResources()
      templates.value = res.templates
      mediaWorkflows.value = res.mediaWorkflows
      ttsWorkflows.value = res.ttsWorkflows
      bgmFiles.value = res.bgmFiles
      ttsVoices.value = res.ttsVoices || []
    } catch (e: any) {
      ElMessage.error(`资源加载失败：${e.message}`)
    }
  }

  async function loadT() {
    try { tasks.value = await apiLoadTasks() }
    catch { tasks.value = [] }
  }

  async function loadAll() {
    await Promise.allSettled([checkH(), loadRes(), loadT()])
  }

  async function handleUpload(rawFile: File, category: string, target?: string) {
    if (!rawFile) return
    try {
      const data = await apiUpload(rawFile, category)
      uploads.value.unshift(data)
      saveToLocalHistory(data, category)
      ElMessage.success(`${data.filename} 上传成功`)
      return { path: data.path, category }
    } catch (e: any) {
      ElMessage.error(`上传失败：${e.message}`)
      return null
    }
  }

  function openHistory(category: string) {
    const localHistory = loadLocalHistory()
    return {
      records: localHistory.slice(0, 50),
      filterCategory: category,
    }
  }

  return {
    healthOk,
    templates,
    mediaWorkflows,
    ttsWorkflows,
    bgmFiles,
    ttsVoices,
    tasks,
    uploads,
    loadAll,
    loadT,
    handleUpload,
    openHistory,
  }
}