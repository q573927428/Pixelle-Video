import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { request } from '../api'

export function useTaskRunner() {
  const running = ref(false)
  const progress = ref(0)
  const statusText = ref('等待开始')
  const result = ref<any>({})

  let pollTimer: ReturnType<typeof setInterval> | null = null

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }

  function parseJson(text: string) {
    if (!text || !text.trim()) return {}
    try { return JSON.parse(text) }
    catch (e: any) { throw new Error(`JSON 参数格式错误：${e.message}`) }
  }

  function cleanedPayload(payload: any) {
    return Object.fromEntries(
      Object.entries(payload).filter(([_, v]) => v !== '' && v !== null && v !== undefined && !(Array.isArray(v) && v.length === 0))
    )
  }

  async function submitTask(url: string, payload: any) {
    running.value = true
    progress.value = 2
    statusText.value = '任务提交中...'
    result.value = {}
    try {
      const data: any = await request(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      statusText.value = `任务已创建：${data.task_id}`
      progress.value = 8
      pollTask(data.task_id)
    } catch (e: any) {
      running.value = false
      statusText.value = `提交失败：${e.message}`
      ElMessage.error(statusText.value)
    }
  }

  function pollTask(taskId: string) {
    stopPolling()
    const tick = async () => {
      try {
        const task: any = await request(`/api/tasks/${taskId}`)
        progress.value = Math.max(8, Math.min(99, task.percentage || 0))
        statusText.value = task.message || `状态：${task.status}`
        if (task.status === 'completed') {
          running.value = false
          progress.value = 100
          result.value = task.result || {}
          statusText.value = '生成完成'
          stopPolling()
          ElMessage.success('视频生成完成')
        }
        if (['failed', 'cancelled'].includes(task.status)) {
          running.value = false
          statusText.value = `任务失败：${task.error || task.message || task.status}`
          stopPolling()
          ElMessage.error(statusText.value)
        }
      } catch (e: any) {
        running.value = false
        statusText.value = `任务查询失败：${e.message}`
        stopPolling()
      }
    }
    tick()
    pollTimer = setInterval(tick, 3000)
  }

  return {
    running,
    progress,
    statusText,
    result,
    submitTask,
    parseJson,
    cleanedPayload,
    stopPolling,
  }
}