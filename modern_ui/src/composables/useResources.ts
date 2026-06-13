import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { TtsVoiceInfo } from '../types'
import { loadResources, loadTasks as apiLoadTasks, checkHealth, uploadFile as apiUpload, getUserStorageUsage } from '../api'

// 模块顶层单例状态 - 所有调用 useResources() 的地方共享同一组引用
const healthOk = ref(false)
const templates = ref<any[]>([])
const mediaWorkflows = ref<any[]>([])
const ttsWorkflows = ref<any[]>([])
const bgmFiles = ref<any[]>([])
const ttsVoices = ref<TtsVoiceInfo[]>([])
const tasks = ref<any[]>([])

let loaded = false

export function useResources() {
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
    if (loaded) return // 防止重复加载
    loaded = true
    await Promise.allSettled([checkH(), loadRes(), loadT()])
  }

  async function handleUpload(rawFile: File, category: string, target?: string) {
    if (!rawFile) return null
    try {
      // 先检查存储空间是否足够
      try {
        const usage = await getUserStorageUsage()
        if (!usage.is_unlimited && usage.usage_percent >= 100) {
          ElMessage.warning(`存储空间已满（${usage.used_display} / ${usage.limit_display}），请清理空间后继续上传`)
          return null
        }
      } catch (_) {
        // 忽略用量查询失败，后端也会做最终校验
      }

      const data = await apiUpload(rawFile, category)
      ElMessage.success(`${data.filename} 上传成功`)
      return { path: data.path, category, file_id: data.file_id }
    } catch (e: any) {
      ElMessage.error(`上传失败：${e.message}`)
      return null
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
    loadAll,
    loadT,
    handleUpload,
  }
}